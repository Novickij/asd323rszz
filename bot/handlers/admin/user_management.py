import io
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile
)
from aiogram.utils.formatting import Text, Bold

from bot.database.methods.get import (
    get_all_user,
    get_all_subscription,
    get_payments,
    get_person,
    get_key_user,
    get_name_location_server,
    get_server_id
)
from bot.database.methods.update import (
    add_time_person,
    person_banned_true,
    block_state_person,
    add_time_key
)
from bot.database.methods.insert import add_key
from bot.keyboards.reply.admin_reply import (
    admin_user_menu,
    back_user_menu,
    show_user_menu,
    static_user_menu
)
from bot.keyboards.inline.admin_inline import (
    edit_client_menu,
    delete_time_client,
    keys_control
)
from bot.misc.VPN.ServerManager import ServerManager
from bot.misc.callbackData import (
    EditUserPanel,
    DeleteTimeClient,
    MessageAdminUser,
    EditKeysUser,
    BlockedUserPanel
)
from bot.misc.language import Localization, get_lang
from bot.misc.loop import disable_key
from bot.misc.util import CONFIG

log = logging.getLogger(__name__)

_ = Localization.text
btn_text = Localization.get_reply_button

ONE_HOUR = 3600

user_management_router = Router()

class EditUser(StatesGroup):
    show_user = State()
    add_time = State()
    delete_time = State()
    input_message_user = State()
    input_balance_user = State()
    add_key = State()
    add_key_duration = State()

@user_management_router.message(
    (F.text.in_(btn_text('admin_users_btn')))
    | (F.text.in_(btn_text('admin_back_users_menu_btn')))
)
async def command(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    await message.answer(
        _('admin_user_manager_m', lang),
        reply_markup=await admin_user_menu(lang)
    )

@user_management_router.message(
    F.text.in_(btn_text('admin_show_statistic_btn'))
)
async def control_user_handler(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    await message.answer(
        _('admin_user_manager_m', lang),
        reply_markup=await show_user_menu(lang)
    )

@user_management_router.message(
    F.text.in_(btn_text('admin_statistic_show_all_users_btn'))
)
async def show_user_handler(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    all_users = await get_all_user()
    str_user = ''
    count = 1
    for user in all_users:
        str_user += await string_user(user, count, lang)
        count += 1
    file_stream = io.BytesIO(str_user.encode()).getvalue()
    input_file = BufferedInputFile(file_stream, 'all_user.txt')
    try:
        await message.answer_document(
            input_file,
            caption=_('list_of_all_users_file', lang)
        )
    except Exception as e:
        await message.answer(_('error_list_of_all_users_file', lang))
        log.error(f"Error sending file all_user.txt: {e}")

@user_management_router.message(
    F.text.in_(btn_text('admin_statistic_show_sub_users_btn'))
)
async def show_user_sub_handler(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    sub_users = await get_all_subscription()
    str_sub_user = ''
    count = 1
    keys_user = []
    for user in sub_users:
        for key in user.keys:
            if not key.free_key and not key.trial_period:
                keys_user.append(key)
        user.keys = keys_user
        keys_user = []
        if len(user.keys) == 0:
            continue
        str_sub_user += await string_user(user, count, lang)
        count += 1
    if not str_sub_user:
        await message.answer(_('none_sub_users_list', lang))
        return
    file_stream = io.BytesIO(str_sub_user.encode()).getvalue()
    input_file = BufferedInputFile(file_stream, 'subscription_user.txt')
    try:
        await message.answer_document(
            input_file,
            caption=_('list_of_sub_users_file', lang)
        )
    except Exception as e:
        await message.answer(_('error_list_of_sub_users_file', lang))
        log.error(f"Error sending file subscription_user.txt: {e}")

@user_management_router.message(
    F.text.in_(btn_text('admin_statistic_show_payments_btn'))
)
async def show_payments_handler(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    payments = await get_payments()
    str_payments = ''
    count = 1
    for payment in payments:
        str_payments += (
            _('write_payments_file_str', lang, False)
            .format(
                count=count,
                user=payment.user,
                user_id=payment.user_id.tg_id,
                payment_system=payment.payment_system,
                amount=payment.amount,
                date=payment.created_at
            )
        )
        count += 1
    if not str_payments:
        await message.answer(_('none_list_of_payments_file', lang))
        return
    file_stream = io.BytesIO(str_payments.encode()).getvalue()
    input_file = BufferedInputFile(file_stream, 'payments.txt')
    try:
        await message.answer_document(
            input_file,
            caption=_('list_of_payments_file', lang)
        )
    except Exception as e:
        await message.answer(_('error_list_of_payments_file', lang))
        log.error(f"Error sending file payments.txt: {e}")

@user_management_router.message(
    F.text.in_(btn_text('admin_edit_user_btn'))
)
async def edit_user_handler(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    await message.answer(
        _('input_telegram_id_user_m', lang),
        reply_markup=await back_user_menu(lang)
    )
    await state.set_state(EditUser.show_user)

@user_management_router.message(
    (F.text.in_(btn_text('admin_users_cancellation')))
    | (F.text.in_(btn_text('admin_exit_btn')))
)
async def back_user_control(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    await state.clear()
    await message.answer(
        _('admin_user_manager_m', lang),
        reply_markup=await admin_user_menu(lang)
    )

@user_management_router.message(EditUser.show_user)
async def show_user_state(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    try:
        client = await get_person(int(message.text.strip()))
        content = Text(
            _('card_client_admin_m', lang).format(
                fullname=client.fullname,
                username=client.username,
                telegram_id=client.tgid,
                lang_code=client.lang_tg or '❌',
                referral_balance=client.referral_balance,
                keys=len(client.keys),
                group=client.group if client.group is not None else '❌',
            ),
        )
        await message.answer(
            **content.as_kwargs(),
            reply_markup=await edit_client_menu(
                client.tgid, lang, client.blocked)
        )
        await state.update_data(client=client)
    except Exception as e:
        log.info(f"Client not found: {e}")
        await message.answer(
            _('card_client_admin_m_client_none', lang),
            reply_markup=await admin_user_menu(lang)
        )
        await state.clear()

@user_management_router.callback_query(BlockedUserPanel.filter())
async def callback_work_server(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: BlockedUserPanel):
    lang = await get_lang(call.from_user.id, state)
    state_blocked = not callback_data.action == 'unblocked'
    await block_state_person(callback_data.id_user, state_blocked)
    await call.message.answer(
        _('edit_client_unblocked_' if state_blocked else 'edit_client_blocked_', lang=True))
    await call.answer()

@user_management_router.callback_query(EditUserPanel.filter())
async def callback_user(
        call: CallbackQuery,
        callback_data: EditUserPanel,
        state: FSMContext):
    lang = await get_lang(call.from_user.id, state)
    user_data = await state.get_data()
    log.info(f"callback_user: user_data={user_data}")
    if callback_data.action == 'count_use':
        if 'client' not in user_data:
            log.error("Client data not found in state for count_use action")
            await call.message.answer("Ошибка: данные клиента не найдены. Пожалуйста, выберите пользователя заново.")
            await state.set_state(EditUser.show_user)
            await call.answer()
            return
        await call.message.answer(_('input_count_day_add_time_m', lang))
        await state.set_state(EditUser.add_time)
    elif callback_data.action == 'add_key':
        if 'client' not in user_data:
            log.error("Client data not found in state for add_key action")
            await call.message.answer("Ошибка: данные клиента не найдены. Пожалуйста, выберите пользователя заново.")
            await state.set_state(EditUser.show_user)
            await call.answer()
            return
        await call.message.answer(_('input_server_id_m', lang))
        await state.set_state(EditUser.add_key)
    else:
        await call.message.edit_reply_markup(
            reply_markup=await delete_time_client(lang)
        )
    await call.answer()

@user_management_router.callback_query(EditKeysUser.filter())
async def edit_keys_user(
        call: CallbackQuery,
        callback_data: EditKeysUser,
        state: FSMContext):
    lang = await get_lang(call.from_user.id, state)
    user = await get_person(callback_data.id_user)
    keys = await get_key_user(callback_data.id_user)
    keys_string = ''
    utc_plus_3 = timezone(timedelta(hours=CONFIG.UTC_time))
    for key in keys:
        time_from_db = datetime.fromtimestamp(key.subscription, tz=utc_plus_3)
        current_time = datetime.now(utc_plus_3)
        time_difference = time_from_db - current_time
        days = time_difference.days
        name = (key.server_table.vds_table.location_table.name if key.server_table
                else '')
        type_vpn_key = ServerManager.VPN_TYPES.get(
            key.server_table.type_vpn, ServerManager.VPN('Unknown')).NAME_VPN
        keys_string += (
            _('user_key_list_admin', lang).format(
                count_key=key.id,
                count_day=days,
                type_vpn_key=type_vpn_key,
                name=name,
                count_switch=key.switch_location
            ) + '\n'
        )
    text = Text(
        _('keys_users_edit_admin', lang).format(
            full_name=user.fullname, telegram_id=user.tgid),
        '\n\n', keys_string
    )
    await call.message.answer(
        **text.as_kwargs(),
        reply_markup=await keys_control(lang, user.tgid)
    )
    await call.answer()

@user_management_router.message(EditUser.add_time)
async def add_time_user_state(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    try:
        if message.text.strip() in btn_text('admin_users_cancellation'):
            await state.clear()
            await message.answer(
                _('back_you_back', lang),
                reply_markup=await admin_user_menu(lang)
            )
            return
        input_text = message.text.strip()
        if input_text.endswith('m'):
            count = int(input_text[:-1])
            seconds = count * 60
            unit = 'минут'
        elif input_text.endswith('d'):
            count = int(input_text[:-1])
            seconds = count * (ONE_HOUR * 24)
            unit = 'дней'
        else:
            await message.answer(_('incorrect_input_time_format', lang))
            return

        max_days = 2000
        max_minutes = max_days * 24 * 60
        if (input_text.endswith('d') and count > max_days) or (input_text.endswith('m') and count > max_minutes):
            await message.answer(_('limit_count_day_sub_m', lang))
            return
    except ValueError as e:
        log.error(f"Incorrect input count time: {e}")
        await message.answer(_('incorrect_input_time_format', lang))
        return
    try:
        user_data = await state.get_data()
        client = user_data['client']
        await add_time_person(client.tgid, seconds)
        await state.clear()
        await message.answer(
            f(_('input_count_day_sub_success', lang).format(
                username=client.username, count=count, unit=unit)),
            reply_markup=await admin_user_menu(lang)
        )
        try:
            client = await get_person(client.tgid)
            await message.bot.send_message(
                client.tgid,
                f(_('donated_days', lang=client.lang_tg).format(count=count, unit=unit)),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            log.info(f"User blocked bot: {e}")
            await message.answer(_('error_input_count_day_sub_success', lang))
    except Exception as e:
        log.error(f"Error adding time to user: {e}")
        await message.answer(_('error_not_found', lang))
        await state.clear()
        return

@user_management_router.message(EditUser.add_key)
async def add_key_user_state(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    from sqlalchemy.ext.asyncio import AsyncSession
    from bot.database.db import async_session
    try:
        if message.text.strip() in btn_text('admin_users_cancellation'):
            await state.clear()
            await message.answer(
                _('back_you_back', lang),
                reply_markup=await admin_user_menu(lang)
            )
            return
        server_id = int(message.text.strip())
        log.info(f"Processing add_key for server_id={server_id}")
        server = await get_server_id(server_id)
        if not server:
            log.warning(f"Server {server_id} not found")
            await message.answer(_('server_not_found', lang))
            return
        if not server.work:
            log.warning(f"Server {server_id} is not working")
            await message.answer(_('server_not_working', lang))
            return
        if not server.vds_table:
            log.error(f"No VDS associated with server {server_id}")
            await message.answer(_('error_no_vds_for_server', lang))
            return
        if not server.vds_table.ip:
            log.error(f"Server {server_id} missing VDS IP")
            await message.answer(_('error_missing_vds_ip', lang))
            return
        user_data = await state.get_data()
        log.info(f"user_data: {user_data}")
        if 'client' not in user_data:
            log.error("Client data not found in state")
            await message.answer("Ошибка: данные клиента не найдены. Пожалуйста, выберите пользователя заново.")
            await state.set_state(EditUser.show_user)
            await message.answer(
                _('input_telegram_id_user_m', lang),
                reply_markup=await back_user_menu(lang)
            )
            return
        client = user_data['client']
        log.info(f"Creating key for user {client.tgid} on server {server_id}")
        server_manager = ServerManager(server)
        if not await server_manager.login():
            log.error(f"Failed to login to server {server_id}: check IP/port or credentials")
            await message.answer(
                _('error_connection_failed', lang).format(ip=server.vds_table.ip, ports='80, 8080, 8081'),
                reply_markup=await admin_user_menu(lang)
            )
            return
        current_time = int(datetime.now(timezone(timedelta(hours=CONFIG.UTC_time))).timestamp())
        log.info(f"Current time for key creation: {datetime.fromtimestamp(current_time)} (UTC+{CONFIG.UTC_time})")
        async with async_session() as session:
            key_id = await add_key(
                session=session,
                telegram_id=client.tgid,
                subscription=current_time + 3600,  # 1 час для временного ключа
                server_id=server_id
            )
            await session.commit()
        if not key_id:
            log.error(f"Failed to create key {key_id} for user {client.tgid} on server {server_id}")
            await message.answer(_('error_create_key', lang))
            return
        log.info(f"Created key {key_id} for user {client.tgid} on server {server_id} with subscription={datetime.fromtimestamp(current_time + 3600)}")
        await state.update_data(key_id=key_id, server_id=server_id)
        await message.answer(_('input_time_for_key_m', lang))
        await state.set_state(EditUser.add_key_duration)
    except ValueError as e:
        log.error(f"Incorrect input server_id: {e}")
        await message.answer(_('incorrect_input_server_id', lang))
        return
    except Exception as e:
        log.error(f"Error during key creation: {e}")
        await message.answer(_('error_message', lang))
        await state.clear()

@user_management_router.message(EditUser.add_key_duration)
async def set_time_key_user_state(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    from sqlalchemy.ext.asyncio import AsyncSession
    from bot.database.db import async_session
    try:
        if message.text.strip() in btn_text('admin_users_cancellation'):
            await state.clear()
            await message.answer(
                _('back_you_back', lang),
                reply_markup=await admin_user_menu(lang)
            )
            return
        input_text = message.text.strip()
        if input_text.endswith('m'):
            count = int(input_text[:-1])
            seconds = count * 60
            unit = 'минут'
        elif input_text.endswith('d'):
            count = int(input_text[:-1])
            seconds = count * (ONE_HOUR * 24)
            unit = 'дней'
        else:
            await message.answer(_('incorrect_input_time_format', lang))
            return

        max_days = 2000
        max_minutes = max_days * 24 * 60
        if (input_text.endswith('d') and count > max_days) or (input_text.endswith('m') and count > max_minutes):
            await message.answer(_('limit_count_day_sub_m', lang))
            return

        user_data = await state.get_data()
        key_id = user_data['key_id']
        server_id = user_data['server_id']
        client = user_data['client']
        log.info(f"Setting subscription time for key {key_id} on server {server_id}: {count} {unit}")
        server = await get_server_id(server_id)
        if not server:
            log.error(f"Server {server_id} not found during key activation")
            await message.answer(_('server_not_found', lang))
            await state.clear()
            return
        if not server.vds_table:
            log.error(f"No VDS associated with server {server_id}")
            await message.answer(_('error_no_vds_for_server', lang))
            await state.clear()
            return
        if not server.vds_table.ip:
            log.error(f"Server {server_id} VDS missing IP")
            await message.answer(_('error_missing_vds_ip', lang))
            await state.clear()
            return
        current_time = int(datetime.now(timezone(timedelta(hours=CONFIG.UTC_time))).timestamp())
        log.info(f"Current time for key activation: {datetime.fromtimestamp(current_time)} (UTC+{CONFIG.UTC_time}), adding {seconds} seconds")
        async with async_session() as session:
            success = await add_time_key(key_id, seconds, session=session)
            await session.commit()
        if not success:
            log.error(f"Failed to set subscription time for key {key_id}")
            await message.answer(_('error_setting_key_time', lang))
            await state.clear()
            return
        log.info(f"Subscription time set for key {key_id}: {count} {unit}, new subscription={datetime.fromtimestamp(current_time + seconds)}")
        server_manager = ServerManager(server)
        if not await server_manager.login():
            log.error(f"Failed to login to server {server_id}: check IP/port or credentials")
            await message.answer(
                _('error_connection_failed', lang).format(ip=server.vds_table.ip, ports='80, 8080, 8081'),
                reply_markup=await admin_user_menu(lang)
            )
            await state.clear()
            return
        success = await server_manager.add_client(client.tgid, key_id)
        if not success:
            log.warning(f"Failed to add client for key {key_id} on server {server_id}")
            await message.answer(_('error_adding_key_to_server', lang))
            await state.clear()
            return
        log.info(f"Added client for key {key_id} to server {server_id}")
        name_key = await get_name_location_server(server_id)
        config = await server_manager.get_key(
            user_tgid=client.tgid,
            name_key=name_key,
            key_id=key_id
        )
        if not config:
            log.warning(f"Failed to get key config for key {key_id} on server {server_id}")
            await message.answer(_('error_getting_key_config', lang))
            await state.clear()
            return
        log.info(f"Successfully retrieved key config for {key_id} on server {server_id}")
        lang_user = await get_lang(client.tgid)
        await message.bot.send_message(
            client.tgid,
            text=_('admin_gift_key', lang_user).format(
                key_id=key_id,
                days=count if unit == 'дней' else count // (24 * 60)),
            parse_mode=ParseMode.HTML
        )
        await message.bot.send_message(
            client.tgid,
            config,
            parse_mode=ParseMode.HTML
        )
        await message.answer(
            _('key_added_success', lang).format(
                key_id=key_id,
                count=count,
                unit=unit
            ),
            reply_markup=await admin_user_menu(lang)
        )
        log.info(f"Successfully sent key {key_id} to user {client.tgid}")
        await state.clear()
    except ValueError as e:
        log.error(f"Incorrect input time format: {e}")
        await message.answer(_('incorrect_input_time_format', lang))
        return
    except Exception as e:
        log.error(f"Error during adding time to key: {e}")
        await message.answer(_('error', lang))
        await state.clear()

async def delete_time_user_callback(call: CallbackQuery, callback_data: DeleteTimeClient, state: FSMContext):
    lang = await get_lang(call.from_user.id, state)
    try:
        user_data = await state.get_data()
        client = user_data['client']
        await person_banned_true(client.tgid)
        for key in client.keys:
            await disable_key(key.id)
        try:
            client = await get_person(client.tgid)
            await call.message.bot.send_message(
                client.tgid,
                _('ended_sub_message', lang=client.lang_tg),
                parse_mode=ParseMode.HTML
            )
            await call.message.answer(_('success_user_delete_time', lang))
            await state.clear()
            return
        except Exception as e:
            log.error(f"Error notifying user {client.tgid}: {e}")
            await call.message.answer(_('error_user_delete_time_m', lang))
            await state.clear()
    except Exception as e:
        log.error(f"Error in delete_time_user_callback: {e}")
        await call.message.answer(_('error_not_found', lang))
        await state.clear()

@user_management_router.message(F.text.in_(btn_text('admin_static_user_btn')))
async def static_user_management_handler(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id, state)
    await message.answer(
        _('select_menu_item', lang),
        reply_markup=await static_user_menu(lang)
    )

async def string_user(client, count, lang):
    count_key = 0
    for key in client.keys:
        if not key.free_key and not key.trial_period:
            count_key += 1
    return _('show_client_file_str', lang, False).format(
        count=count,
        fullname=client.fullname,
        username=client.username,
        telegram_id=str(client.tgid),
        lang_code=client.lang_tg or '',
        referral_balance=client.referral_balance,
        group=client.group or '',
        count_key=count_key
    )

async def string_user_server(client, count, lang):
    return _('show_client_file_str_server', lang).format(
        count=count,
        fullname=client.fullname,
        username=client.username,
        telegram_id=str(client.tgid),
        lang_code=client.lang_tg or '',
        referral_balance=client.referral_balance,
        group=client.group or ''
    )

async def get_config_client(client, server_id: int) -> Optional[str]:
    server = await get_server_id(server_id)
    server_manager = ServerManager(server)
    name_key = await get_name_location_server(server_id)
    await server_manager.login()
    return await server_manager.get_key(
        user_tgid=client.tgid,
        name_key=name_key,
        key_id=server_id
    )

@user_management_router.callback_query(MessageAdminUser.filter())
async def message_admin_callback_query(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: MessageAdminUser):
    lang = await get_lang(call.from_user.id, state)
    await call.message.delete()
    await call.message.answer(
        _('input_admin_message', lang),
    )
    await state.update_data(tgid=callback_data.id_user)
    await state.set_state(EditUser.input_message_user)
    await call.answer()

@user_management_router.message(EditUser.input_message_user)
async def message_user_input(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id, state)
    text = Text(_('message_from_admin', lang), '\n\n', message.text.strip())
    data = await state.get_data()
    try:
        await message.bot.send_message(int(data.get('tgid')), **text.as_kwargs())
        await message.answer(
            _('message_success', lang),
            reply_markup=await admin_user_menu(lang)
        )
    except Exception as e:
        log.error(f"Error sending message to user: {e}")
        await message.answer(
            _('message_user_blocked', lang),
            reply_markup=await admin_user_menu(lang)
        )
    await state.clear()