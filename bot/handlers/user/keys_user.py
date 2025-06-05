# handlers/user/keys_user.py
import logging
import time

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.main import engine
from bot.database.methods.get import (
    get_person,
    get_key_user,
    get_key_id, get_name_location_server,
    get_free_server_id,
)
from bot.database.methods.insert import add_key
from bot.database.methods.update import person_trial_period, \
    server_space_update, update_server_key
from bot.handlers.user.install_menu import install_main_menu
from bot.keyboards.inline.user_inline import (
    connect_vpn_menu,
    choose_type_vpn,
    renew,
    user_menu
)
from bot.misc.VPN.ServerManager import ServerManager
from bot.misc.language import Localization, get_lang
from bot.misc.callbackData import (
    ShowKey,
    EditKey,
    ExtendKey,
    DetailKey, TrialPeriod
)
from bot.misc.util import CONFIG
from bot.service.edit_message import edit_message
from bot.database.models.main import Keys

log = logging.getLogger(__name__)

_ = Localization.text
btn_text = Localization.get_reply_button

key_router = Router()

async def post_key_telegram(
        event: CallbackQuery | Message,
        key,
        config,
        lang,
        custom_message=None,
        custom_reply_markup=None
) -> None:
    log.debug(f"Posting key for user {event.from_user.id}, config: {config}")
    try:
        message = event.message if isinstance(event, CallbackQuery) else event
        config_message = f"```\n{config}\n```"
        
        if custom_message:
            connect_message = f"{custom_message}\n\n{config_message}"
            reply_markup = custom_reply_markup or (await install_main_menu(lang))[1]
            await message.answer(
                text=connect_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            connect_message = _('how_to_connect', lang).format(
                name_vpn=ServerManager.VPN_TYPES.get(key.server_table.type_vpn).NAME_VPN,
                config=''
            ) + f"\n\n{config_message}"
            reply_markup = custom_reply_markup or (await install_main_menu(lang))[1]
            await edit_message(
                message,
                caption=connect_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        log.error(f"Failed to send key for user {event.from_user.id}: {e}")
        await message.answer(
            text=_('key_generated_error', lang),
            reply_markup=await user_menu(lang, event.from_user.id),
            parse_mode=ParseMode.HTML
        )

@key_router.callback_query(F.data == 'vpn_connect_btn')
async def choose_server_user(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user.id, state)
    keys = await get_key_user(call.from_user.id, None)
    if len(keys) != 0:
        await edit_message(
            call.message,
            caption=_('user_key_list_message_connect', lang),
            reply_markup=await connect_vpn_menu(lang, keys)
        )
        return
    await edit_message(
        call.message,
        caption=_('choosing_connect_type', lang),
        reply_markup=await choose_type_vpn(
            lang, back_data='back_general_menu_btn',
            payment=True
        )
    )

@key_router.callback_query(F.data.in_(btn_text('vpn_connect_btn')))
async def choose_server_user(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user.id, state)
    keys = await get_key_user(call.from_user.id, None)
    if len(keys) != 0:
        await call.message.answer(
            text=_('user_key_list_message_connect', lang),
            reply_markup=await connect_vpn_menu(lang, keys)
        )
        return
    await call.message.answer(
        text=_('choosing_connect_type', lang),
        reply_markup=await choose_type_vpn(
            lang, back_data='back_general_menu_btn',
            payment=True
        )
    )

@key_router.callback_query(TrialPeriod.filter())
async def choose_server_user(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: TrialPeriod
) -> None:
    lang = await get_lang(call.from_user.id, state)
    person = await get_person(call.from_user.id)
    await call.message.delete()
    await get_trial_period(
        call.message,
        call,
        lang,
        person,
        callback_data.id_prot,
        callback_data.id_loc
    )

async def get_trial_period(
        message: Message,
        call: CallbackQuery,
        lang,
        person,
        id_prot,
        id_loc
):
    if person.trial_period:
        await message.answer(_('not_trial_message', lang))
        return
    await person_trial_period(person.tgid)
    person.trial_period = True
    person.special_offer = True
    await message.answer(_('trial_message', lang))
    server = await get_free_server_id(
        id_loc,
        id_prot
    )
    key = await add_key(
        person.tgid,
        CONFIG.trial_period,
        trial_period=True,
        server_id=server.id
    )
    try:
        download = await message.answer(_('download', lang))
        key = await get_key_id(key.id)
        if not key.is_active or key.subscription <= int(time.time()):
            log.error(f"Trial key {key.id} is not active or expired for user {call.from_user.id}")
            await message.answer(
                text=_('key_expired', lang),
                parse_mode="HTML"
            )
            await download.delete()
            return
        server_manager = ServerManager(key.server_table)
        await server_manager.login()
        if await server_manager.add_client(
                call.from_user.id, key.id
        ) is None:
            raise Exception('user/main.py add client error')
        name_location = await get_name_location_server(key.server_table.id)
        config = await server_manager.get_key(
            call.from_user.id,
            name_key=name_location,
            key_id=key.id
        )
        server_parameters = await server_manager.get_all_user()

        await server_space_update(
            server.id,
            len(server_parameters)
        )
    except Exception as e:
        await update_server_key(key.id)
        await message.answer(_('server_not_connected', lang))
        log.error(f"Failed to issue trial key for user {call.from_user.id}: {e}")
        await download.delete()
        return
    await download.delete()
    await post_key_telegram(call, key, config, lang)

async def show_key(callback, lang, key):
    async with AsyncSession(engine) as session:
        statement = select(Keys).filter(Keys.id == key.id)
        result = await session.execute(statement)
        key_db = result.scalar_one_or_none()
        if not key_db:
            await callback.message.answer(
                text=_('key_not_found', lang),
                parse_mode="HTML"
            )
            log.error(f"Key {key.id} not found for user {callback.from_user.id}")
            await callback.answer()
            return
        if not key_db.is_active or key_db.subscription <= int(time.time()):
            await callback.message.answer(
                text=_('key_expired_please_extend', lang),
                parse_mode="HTML"
            )
            log.info(f"Key {key.id} is not active or expired for user {callback.from_user.id}")
            await callback.answer()
            return
        try:
            server_manager = ServerManager(key_db.server_table)
            name_location = await get_name_location_server(key_db.server_table.id)
            await server_manager.login()
            config = await server_manager.get_key(
                name=callback.from_user.id,
                name_key=name_location,
                key_id=key_db.id
            )
            if config is None:
                raise Exception('Server Not Connected')
        except Exception as e:
            await callback.message.answer(_('server_not_connected', lang))
            log.error(f"Failed to get key {key.id} for user {callback.from_user.id}: {e}")
            await callback.answer()
            return
        await post_key_telegram(callback, key_db, config, lang)

@key_router.callback_query(DetailKey.filter())
async def choose_server_free(
        call: CallbackQuery,
        callback_data: DetailKey,
        state: FSMContext
) -> None:
    lang = await get_lang(call.from_user.id, state)
    keys = await get_key_user(call.from_user.id)
    try:
        await edit_message(
            call.message,
            reply_markup=await connect_vpn_menu(
                lang,
                keys,
                id_detail=callback_data.key_id
            )
        )
    except Exception as e:
        await call.message.answer(
            text=_('user_key_list_message_connect', lang),
            reply_markup=await connect_vpn_menu(
                lang,
                keys,
                id_detail=callback_data.key_id
            )
        )
    await call.answer()

@key_router.callback_query(ShowKey.filter())
async def choose_server_free(
        call: CallbackQuery,
        callback_data: ShowKey,
        state: FSMContext
) -> None:
    lang = await get_lang(call.from_user.id, state)
    key = await get_key_id(callback_data.key_id)
    if key.server is None:
        await edit_message(
            call.message,
            caption=_('choosing_connect_type', lang),
            reply_markup=await choose_type_vpn(
                lang,
                key_id=key.id,
                back_data='vpn_connect_btn'
            )
        )
        await call.answer()
        return
    await show_key(call, lang, key)
    await call.answer()

@key_router.callback_query(EditKey.filter())
async def choose_server_free(
        call: CallbackQuery,
        callback_data: EditKey,
        state: FSMContext
) -> None:
    lang = await get_lang(call.from_user.id, state)
    await edit_message(
        call.message,
        caption=_('choosing_connect_type', lang),
        reply_markup=await choose_type_vpn(
            lang, key_id=callback_data.key_id, back_data='vpn_connect_btn'
        )
    )
    await call.answer()

@key_router.callback_query(ExtendKey.filter())
async def extend_key(
        call: CallbackQuery,
        callback_data: ExtendKey,
        state: FSMContext
) -> None:
    lang = await get_lang(call.from_user.id, state)
    user = await get_person(call.from_user.id)
    async with AsyncSession(engine) as session:
        statement = select(Keys).filter(Keys.id == callback_data.key_id)
        result = await session.execute(statement)
        key = result.scalar_one_or_none()
        if not key:
            log.error(f"Key {callback_data.key_id} not found for user {call.from_user.id}")
            await call.message.answer(
                text=_('key_not_found', lang),
                parse_mode="HTML"
            )
            await call.answer()
            return
    await edit_message(
        call.message,
        caption=_('choosing_month_sub', lang),
        reply_markup=await renew(
            CONFIG,
            lang,
            CONFIG.type_payment.get(1),
            back_data='vpn_connect_btn',
            key_id=callback_data.key_id,
            trial_flag=user.trial_period
        )
    )
    await call.answer()