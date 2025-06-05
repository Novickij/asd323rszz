import logging
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    CallbackQuery
)
from aiogram.utils.formatting import Text, Code, Bold
from pyrogram.filters import location
from sqlalchemy.exc import IntegrityError

from bot.database.methods.delete import delete_static_user_bd
from bot.database.methods.get import (
    get_server,
    get_all_static_user, get_location_id, get_vds_location, get_vds_id,
)
from bot.database.methods.insert import add_static_user
from bot.handlers.admin.location_control import show_list_locations
from bot.handlers.admin.user_management import get_config_client
from bot.keyboards.reply.admin_reply import (
    static_user_menu
)
from bot.keyboards.inline.admin_inline import (
    delete_static_user, vds_list_menu, protocol_list_menu
)
from bot.misc.VPN.ServerManager import ServerManager
from bot.misc.callbackData import (
    DeleteStaticUser, ChooseLocations, ChooseVdsList, ChooseProtocolList,
)
from bot.misc.language import Localization, get_lang
from bot.service.edit_message import edit_message

log = logging.getLogger(__name__)

_ = Localization.text
btn_text = Localization.get_reply_button

static_user = Router()

class StaticUser(StatesGroup):
    static_user_server = State()
    static_user_name = State()


@static_user.message(F.text.in_(btn_text('admin_static_add_user_btn')))
async def add_static_user_handler(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    await show_list_locations(
        message,
        state,
        lang,
        'new',
        True
    )

@static_user.callback_query(F.data == 'back_choose_locations')
async def add_static_user_handler(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user.id, state)
    await show_list_locations(
        call.message,
        state,
        lang,
        'edit',
        True
    )


@static_user.callback_query(ChooseLocations.filter())
async def choose_location_callback(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: ChooseLocations
):
    lang = await get_lang(call.from_user.id, state)
    active_location = await get_location_id(callback_data.id)
    vds_list = await get_vds_location(callback_data.id)
    await edit_message(
        call.message,
        text=_('choose_vds', lang),
        reply_markup=await vds_list_menu(
            active_location.id,
            vds_list,
            lang,
            True
        )
    )


@static_user.callback_query(ChooseVdsList.filter())
async def choose_protocol_callback(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: ChooseVdsList
):
    lang = await get_lang(call.from_user.id, state)
    vds = await get_vds_id(callback_data.vds_id)
    await edit_message(
        call.message,
        text=_('choose_protocol', lang)
        .format(vds_ip=vds.ip),
        reply_markup=await protocol_list_menu(
            vds.location, vds.id, vds.servers, lang, True
        )
    )


@static_user.callback_query(ChooseProtocolList.filter())
async def input_username_static(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: ChooseProtocolList
) -> None:
    lang = await get_lang(call.from_user.id, state)
    protocol = await get_server(callback_data.protocol_id)
    await state.update_data(protocol=protocol)
    await edit_message(
        call.message,
        text=_('static_input_name_user', lang)
    )
    await state.set_state(StaticUser.static_user_name)


async def validate_email(email: str, lang) -> (bool, str):
    if len(email.encode()) > 30:
        return False, _('error_name_static_len', lang)
    if " " in email:
        return False, _('error_name_static_space', lang)
    if email != email.lower():
        return False, _('error_name_static_lower', lang)
    email_pattern = r'^[a-z0-9@._-]+$'
    if not re.match(email_pattern, email):
        return False, _('error_name_static_email', lang)
    return True, None


@static_user.message(StaticUser.static_user_name)
async def add_user_in_server(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    val_email = await validate_email(message.text.strip(), lang)
    if not val_email[0]:
        await message.answer(val_email[1])
        return
    user_data = await state.get_data()
    protocol = user_data['protocol']
    name = message.text.strip()
    try:
        await add_static_user(name, protocol.id)
    except IntegrityError:
        log.info('error add static user UNIQUE constraint -- OK')
        await message.answer(_('error_write_bd_key_create', lang))
        return
    try:
        sever_manager = ServerManager(protocol)
        await sever_manager.login()
        await sever_manager.add_client(name, 0)
    except Exception as e:
        log.error(e, 'error connecting to server')
        await message.answer(_('error_connect_serer', lang))
        return
    await message.answer(
        _('static_user_create_success', lang).format(name=name),
        reply_markup=await static_user_menu(lang)
    )
    await state.clear()


@static_user.message(
    F.text.in_(btn_text('admin_static_show_users_btn'))
)
async def show_static_user_handler(
        message: Message,
        state: FSMContext
) -> None:
    lang = await get_lang(message.from_user.id, state)
    try:
        all_static_user = await get_all_static_user()
        if len(all_static_user) == 0:
            await message.answer(_('none_list_static_user', lang))
            return
    except Exception as e:
        log.error(e, 'error get all static user')
        await message.answer(_('error_get_static_user', lang))
        return
    await message.answer(_('list_static_user', lang))
    for user in all_static_user:
        try:
            if user.server is not None:
                config = await get_config_client(
                    user.server_table,
                    user.name
                )
            else:
                await delete_static_user_bd(user.name)
                await message.answer(
                    _('list_static_user_none_server_delete', lang)
                )
                continue
            message_text = Text(
                _('show_user', lang), Bold(user.name), '\n',
                _('show_key', lang), Code(config)
            )
            await message.answer(
                **message_text.as_kwargs(),
                reply_markup=await delete_static_user(
                    user.name,
                    user.server_table.id,
                    lang
                )
            )
        except Exception as e:
            log.error(e, 'error connect server')
            await message.answer(
                _('error_connect_server', lang).format(
                    name_server=user.server_table.name
                )
            )
            continue


@static_user.callback_query(DeleteStaticUser.filter())
async def delete_static_user_callback(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: DeleteStaticUser):
    lang = await get_lang(call.from_user.id, state)
    try:
        protocol = await get_server(callback_data.protocol_id)
        server_manager = ServerManager(protocol)
        await server_manager.login()
        if not await server_manager.delete_client(callback_data.name, 0):
            raise Exception("Couldn't delete it")
    except Exception as e:
        await call.message.answer(
            _('error_delete_static_user_in_server', lang).format(
                name=callback_data.name
            )
        )
        log.error(e, 'error delete static user')
        return
    try:
        await delete_static_user_bd(callback_data.name)
    except Exception as e:
        await call.message.answer(_('error_delete_bd_static_user', lang))
        log.error(e, 'error delete BD static user')
        return
    await edit_message(
        call.message,
        text=_('delete_static_user_success', lang)
        .format(name=callback_data.name)
    )
    await call.answer()