import io
import logging
from datetime import datetime, timezone, timedelta

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
    get_key_user, get_name_location_server
)
from bot.database.methods.update import (
    add_time_person,
    person_banned_true,
    block_state_person
)
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
from bot.misc.loop import delete_key
from bot.misc.util import CONFIG

log = logging.getLogger(__name__)

_ = Localization.text
btn_text = Localization.get_reply_button

ONE_HOUSE = 3600

user_management_router = Router()


class EditUser(StatesGroup):
    show_user = State()
    add_time = State()
    delete_time = State()
    input_message_user = State()
    input_balance_user = State()


# todo: User management
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
        log.error(e, 'error send file all_user.txt')


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
    if str_sub_user == '':
        await message.answer(_('none_list_of_sub_users_file', lang))
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
        log.error(e, 'error send file subscription_user.txt')


@user_management_router.message(
    F.text.in_(btn_text('admin_statistic_show_payments_btn'))
)
async def back_server_menu_bot(message: Message, state: FSMContext) -> None:
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
                user_id=payment.payment_id.tgid,
                payment_system=payment.payment_system,
                amount=payment.amount,
                date=payment.data
            )
        )
        count += 1
    if str_payments == '':
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
        log.error(e, 'error send file payments.txt')


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
        log.info(e, 'client not found')
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
    block_state = state_blocked
    await block_state_person(callback_data.id_user, block_state)
    if state_blocked:
        await call.message.answer(_('edit_client_unblocked_message', lang))
    else:
        await call.message.answer(_('edit_client_blocked_message', lang))
    await call.answer()


@user_management_router.callback_query(EditUserPanel.filter())
async def callback_work_server(
        call: CallbackQuery,
        callback_data: EditUserPanel,
        state: FSMContext):
    lang = await get_lang(call.from_user.id, state)
    if callback_data.action == 'count_use':
        await call.message.answer(_('input_count_day_add_time_m', lang))
        await state.set_state(EditUser.add_time)
    else:
        await call.message.edit_reply_markup(
            call.message.forward_from_message_id,
            reply_markup=await delete_time_client(lang)
        )
    await call.answer()


@user_management_router.callback_query(EditKeysUser.filter())
async def edit_balance_call(
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
        if key.server is not None:
            name = key.server_table.vds_table.location_table.name
            type_vpn_key = ServerManager.VPN_TYPES.get(
                key.server_table.type_vpn
            ).NAME_VPN
        else:
            name = 'no connect'
            type_vpn_key = 'no protocol'
        keys_string += (
            _('user_key_list_admin', lang)
            .format(
                count_key=key.id,
                count_day=days,
                type_vpn_key=type_vpn_key,
                name=name,
                count_switch=key.switch_location
            ) + '\n'
        )
    text = Text(
        _('keys_users_edit_admin', lang)
        .format(full_name=user.fullname, telegram_id=user.tgid),
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
        count_day = int(message.text.strip())
        if count_day > 2000:
            await message.answer(_('limit_count_day_sub_m', lang))
            return
    except Exception as e:
        log.info(e, 'incorrect input count day sub')
        await message.answer(_('incorrect_input_count_day_sub', lang))
        return
    try:
        user_data = await state.get_data()
        client = user_data['client']
        await add_time_person(client.tgid, count_day * (ONE_HOUSE * 24))
        await state.clear()
        await message.answer(
            _('input_count_day_sub_success', lang).format(
                username=client.username
            ),
            reply_markup=await admin_user_menu(lang)
        )
    except Exception as e:
        log.error(e, 'error add time user')
        await message.answer(_('error_not_found', lang))
        await state.clear()
        return
    try:
        client = await get_person(client.tgid)
        await message.bot.send_message(
            client.tgid,
            _('donated_days', client.lang),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        log.info(e, 'user block bot')
        await message.answer(_('error_input_count_day_sub_success', lang))
        return


@user_management_router.callback_query(DeleteTimeClient.filter())
async def delete_time_user_callback(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call.from_user.id, state)
    try:
        user_data = await state.get_data()
        client = user_data['client']
        await person_banned_true(client.tgid)
        await delete_key(client)
        await call.message.answer(
            _('user_delete_time_m', lang).format(username=client.username),
            reply_markup=await admin_user_menu(lang)
        )
        await call.answer()
        await state.clear()
    except Exception as e:
        log.error(e, 'error delete key or person banned')
        await call.message.answer(_('error_not_found', lang))
        await state.clear()
        return
    try:
        client = await get_person(client.tgid)
        await call.message.bot.send_message(
            client.tgid,
            _('ended_sub_message', client.lang)
        )
    except Exception as e:
        await call.message.answer(_('error_user_delete_time_m', lang))
        log.info(e, 'user block bot')


@user_management_router.message(F.text.in_(btn_text('admin_static_user_btn')))
async def static_user_menu_handler(
        message: Message,
        state: FSMContext
) -> None:
    lang = await get_lang(message.from_user.id, state)
    await message.answer(
        _('select_menu_item', lang),
        reply_markup=await static_user_menu(lang)
    )


async def string_user(client, count, lang):
    count_key = 0
    for key in client.keys:
        if key.free_key or key.trial_period:
            continue
        count_key += 1
    return _('show_client_file_str', lang, False).format(
        count=count,
        fullname=client.fullname,
        username=client.username,
        telegram_id=int(client.tgid),
        lang_code=client.lang_tg or '❌',
        referral_balance=client.referral_balance,
        group=client.group if client.group is not None else '',
        count_key=count_key
    )


async def string_user_server(client, count, lang):
    return _('show_client_file_str_server', lang, False).format(
        count=count,
        fullname=client.fullname,
        username=client.username,
        telegram_id=int(client.tgid),
        lang_code=client.lang_tg or '❌',
        referral_balance=client.referral_balance,
        group=client.group if client.group is not None else ''
    )


async def get_config_client(server, name):
    serve_manager = ServerManager(server)
    name_location = await get_name_location_server(server.id)
    await serve_manager.login()
    return await serve_manager.get_key(
        name=name,
        name_key=name_location,
        key_id=0
    )


@user_management_router.callback_query(MessageAdminUser.filter())
async def message_admin_callback_query(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: MessageAdminUser):
    lang = await get_lang(call.from_user.id, state)
    await call.message.delete()
    await call.message.answer(
        _('input_message_admin_user', lang)
    )
    await state.update_data(tgid=callback_data.id_user)
    await state.set_state(EditUser.input_message_user)
    await call.answer()


@user_management_router.message(EditUser.input_message_user)
async def edit_user_callback_query(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id, state)
    text = Text(
        Bold(_('message_from_the_admin', lang)), '\n',
        message.text.strip()
    )
    data = await state.get_data()
    try:
        await message.bot.send_message(int(data['tgid']), **text.as_kwargs())
        await message.answer(
            _('message_from_success', lang),
            reply_markup=await admin_user_menu(lang)
        )
    except Exception as e:
        log.info(e, 'Error send message admin -- user')
        await message.answer(
            _('message_user_block_bot', lang),
            reply_markup=await admin_user_menu(lang)
        )
    await state.clear()
