import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from bot.database.methods.get import get_key_id, get_free_servers, get_name_location_server, get_person
from bot.database.methods.insert import add_key
from bot.database.methods.update import new_time_key, update_switch_key_admin, server_space_update
from bot.misc.callbackData import EditKeysAdmin
from bot.misc.language import Localization, get_lang
from bot.misc.loop import delete_key
from bot.misc.util import CONFIG
from bot.misc.VPN.ServerManager import ServerManager
from bot.handlers.user.keys_user import post_key_telegram

log = logging.getLogger(__name__)

_ = Localization.text
btn_text = Localization.get_reply_button

keys_control_router = Router()


class EditKeys(StatesGroup):
    input_key_id = State()
    input_key_subscribe = State()
    input_new_subscribe = State()
    input_switch_location = State()


@keys_control_router.callback_query(
    EditKeysAdmin.filter(F.action == 'new_key')
)
async def callback_work_server(
        call: CallbackQuery,
        callback_data: EditKeysAdmin,
        state: FSMContext):
    lang = await get_lang(call.from_user.id, state)
    await call.message.answer(_('edit_key_new_key', lang))
    await state.update_data(id_user=callback_data.id_user)
    await state.set_state(EditKeys.input_key_subscribe)
    await call.answer()


@keys_control_router.message(EditKeys.input_key_subscribe)
async def new_key_admin(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    day = message.text.strip()
    if not day.isdigit():
        await message.answer(_('edit_key_input_key_id_error_number', lang))
        return
    day = int(day)
    if day <= 0 or day > 500:
        await message.answer(_('edit_key_new_key_error_limit', lang))
        return
    data = await state.get_data()
    user_id = data.get('id_user')

    # Получаем информацию о пользователе
    person = await get_person(user_id)
    try:
        # Выбираем платный сервер (free_server=FALSE, type_vpn=1)
        locations = await get_free_servers(person.group, type_vpn=1)
        if not locations:
            raise FileNotFoundError("No available servers")
        server = locations[0].vds[0].servers[0]  # Берем первый доступный сервер
    except FileNotFoundError:
        log.info(f"No free servers for user {user_id} group {person.group} type_vpn 1")
        await message.answer(_('not_server', lang))
        await state.clear()
        return

    # Создаём ключ
    key = await add_key(
        telegram_id=user_id,
        subscription=day * CONFIG.COUNT_SECOND_DAY,
        server_id=server.id
    )

    try:
        # Генерируем конфигурацию ключа
        server_manager = ServerManager(server)
        await server_manager.login()
        if await server_manager.add_client(user_id, key.id) is None:
            raise Exception('add client error')
        name_location = await get_name_location_server(server.id)
        config = await server_manager.get_key(
            user_id,
            name_key=name_location,
            key_id=key.id
        )
        server_parameters = await server_manager.get_all_user()
        await server_space_update(server.id, len(server_parameters))

        # Отправляем ключ пользователю
        lang_user = await get_lang(user_id)
        key = await get_key_id(key.id)
        await message.bot.send_message(
            user_id,
            text=_('admin_gift_key', lang_user).format(days=day),
        )
        await post_key_telegram(message, key, config, lang_user)

        # Сообщение админу
        await message.answer(
            _('edit_key_new_key_success', lang).format(days=day)
        )
    except Exception as e:
        await message.answer(_('edit_key_new_key_success_error', lang))
        log.error(f"Failed to create key for user {user_id}: {e}")
        await state.clear()
        return

    await state.clear()


@keys_control_router.callback_query(EditKeysAdmin.filter())
async def callback_work_server(
        call: CallbackQuery,
        callback_data: EditKeysAdmin,
        state: FSMContext):
    lang = await get_lang(call.from_user.id, state)
    await state.update_data(
        action=callback_data.action,
        id_user=callback_data.id_user
    )
    await call.message.answer(_('edit_key_input_key_id', lang))
    await state.set_state(EditKeys.input_key_id)
    await call.answer()


@keys_control_router.message(EditKeys.input_key_id)
async def edit_key_actions(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    key_id = message.text.strip()
    if not key_id.isdigit():
        await message.answer(_('edit_key_input_key_id_error_number', lang))
        return
    key_id = int(key_id)
    key = await get_key_id(key_id)
    if key is None:
        await message.answer(_('edit_key_input_key_id_error_not_found', lang))
        return
    data = await state.get_data()
    action = data['action']
    if action == 'delete_key':
        try:
            await delete_key(key)
        except Exception as e:
            log.error(e)
            await message.answer(
                _('edit_key_delete_admin_message_error_connect', lang)
            )
            return
        await message.answer(_('edit_key_delete_admin_message', lang))
        lang_user = await get_lang(key.user_tgid)
        await message.bot.send_message(
            key.user_tgid,
            _('edit_key_delete_user_message', lang_user)
        )
    elif action == 'edit_time':
        await state.set_state(EditKeys.input_new_subscribe)
        await state.update_data(key_id=key_id)
        await message.answer(_('edit_key_input_new_time', lang))
        return
    elif action == 'swith_update':
        await state.set_state(EditKeys.input_switch_location)
        await state.update_data(key_id=key_id)
        await message.answer(_('edit_key_input_switch', lang))
        return
    else:
        raise NotImplemented(f'not found action {action}')
    await state.clear()


@keys_control_router.message(EditKeys.input_new_subscribe)
async def new_key_admin(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    day = message.text.strip()
    if not day.isdigit():
        await message.answer(_('edit_key_input_key_id_error_number', lang))
        return
    day = int(day)
    if day <= 0 or day > 500:
        await message.answer(_('edit_key_new_key_error_limit', lang))
        return
    data = await state.get_data()
    key_id = data.get('key_id')
    await new_time_key(
        key_id,
        day * CONFIG.COUNT_SECOND_DAY
    )
    await message.answer(_('edit_key_new_time_success_admin', lang))
    try:
        lang_user = await get_lang(data.get('id_user'))
        await message.bot.send_message(
            data.get('id_user'),
            _('edit_key_new_time_success_user', lang_user)
        )
    except Exception as e:
        await message.answer(_('edit_key_new_key_success_error', lang))
        log.info('user blocked bot')
    await state.clear()


@keys_control_router.message(EditKeys.input_switch_location)
async def new_key_admin(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    count = message.text.strip()
    if not count.isdigit():
        await message.answer(_('edit_key_input_key_id_error_number', lang))
        return
    count = int(count)
    if count > 10000:
        await message.answer(_('edit_key_input_switch_error_limit', lang))
        return
    data = await state.get_data()
    key_id = data.get('key_id')
    await update_switch_key_admin(key_id, count)

    await message.answer(_('edit_key_input_switch_success_admin', lang))
    try:
        lang_user = await get_lang(data.get('id_user'))
        await message.bot.send_message(
            data.get('id_user'),
            _('edit_key_input_switch_success_user', lang_user)
        )
    except Exception as e:
        await message.answer(_('edit_key_new_key_success_error', lang))
        log.info('user blocked bot')
    await state.clear()