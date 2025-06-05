import logging
from datetime import datetime, timezone, timedelta
import time
import asyncio
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

from bot.database.methods.delete import delete_key_in_user
from bot.database.methods.get import (
    get_free_vpn_server, get_key_id, get_key_user, get_name_location_server,
)
from bot.database.methods.insert import add_key
from bot.database.methods.update import server_space_update, update_server_key, person_trial_period
from bot.filters.check_free_vpn import IsWorkFreeVPN
from bot.handlers.user.keys_user import show_key, post_key_telegram
from bot.handlers.user.install_menu import install_main_menu
from bot.keyboards.inline.user_inline import back_menu_button
from bot.misc.VPN.ServerManager import ServerManager
from bot.misc.language import Localization, get_lang
from bot.misc.util import CONFIG
from bot.service.edit_message import edit_message

log = logging.getLogger(__name__)

_ = Localization.text

free_vpn_router = Router()
free_vpn_router.callback_query.filter(IsWorkFreeVPN())

# Блокировка для предотвращения дублирования ключей
user_locks = {}

async def connect_to_server_later(key, free_protocol, user_id):
    start_time = time.time()
    server_manager = ServerManager(free_protocol)
    free_protocol.name_location = await get_name_location_server(free_protocol.id)
    name_location = free_protocol.name_location
    log.debug(f"ServerManager.login() started for user {user_id}")
    await server_manager.login()
    log.debug(f"ServerManager.login() took {time.time() - start_time:.2f} seconds")
    
    start_time = time.time()
    if await server_manager.add_client(
            user_id,
            key.id,
            limit_gb=CONFIG.limit_gb_free
    ) is None:
        log.error(f"Failed to add client for user {user_id}, key {key.id}")
        raise Exception('user/free_vpn.py add client error')
    log.debug(f"ServerManager.add_client() took {time.time() - start_time:.2f} seconds")
    
    start_time = time.time()
    config = await server_manager.get_key(
        user_id,
        name_key=name_location,
        key_id=key.id
    )
    log.debug(f"ServerManager.get_key() took {time.time() - start_time:.2f} seconds")
    
    start_time = time.time()
    server_parameters = await server_manager.get_all_user()
    log.debug(f"ServerManager.get_all_user() took {time.time() - start_time:.2f} seconds")

    log.debug(f"Updating server space for server {free_protocol.id}")
    await server_space_update(
        free_protocol.id,
        len(server_parameters)
    )
    return config

@free_vpn_router.callback_query(F.data == 'free_vpn_connect_btn')
async def free_vpn_btn(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    user_id = call.from_user.id
    lang = await get_lang(user_id, state)
    await state.clear()
    
    log.debug(f"Processing free_vpn_btn for user {user_id}")
    
    # Создаем блокировку для пользователя
    if user_id in user_locks:
        log.warning(f"User {user_id} is already processing a key request")
        await call.message.answer(_('already_processing', lang))
        return
    user_locks[user_id] = True
    
    try:
        # Проверяем существующий ключ
        key_user = await get_key_user(user_id, True)
        if key_user is not None:
            if key_user.server_table is None:
                log.debug(f"Deleting invalid key {key_user.id} for user {user_id}")
                await delete_key_in_user(key_user.id)
            else:
                log.debug(f"User {user_id} already has a valid key {key_user.id}, showing it")
                # Отправляем ключ (меню установки уже включено в show_key через post_key_telegram)
                await show_key(call, lang, key_user)
                return

        # Обновляем пробный период
        log.debug(f"Attempting to update trial_period for user {user_id}")
        success = await person_trial_period(user_id)
        if not success:
            log.error(f"Failed to set trial_period for user {user_id}")
            await call.message.answer(_('trial_period_error', lang))
            return
        
        download = await call.message.answer(_('download', lang))
        
        trial_seconds = CONFIG.trial_period
        trial_days = trial_seconds // (24 * 60 * 60)
        subscription_end = int((datetime.now(timezone.utc) + timedelta(seconds=trial_seconds)).timestamp())

        free_protocol = await get_free_vpn_server()
        if free_protocol is None:
            log.debug(f"No free VPN server available for user {user_id}")
            try:
                await download.delete()
            except TelegramBadRequest:
                log.debug(f"Message 'download' already deleted for user {user_id}")
            await edit_message(
                call.message,
                caption=_('not_server_free_vpn', lang),
                reply_markup=await back_menu_button(lang)
            )
            return

        try:
            log.debug(f"Creating new key for user {user_id}")
            key = await add_key(
                telegram_id=user_id,
                subscription=trial_seconds,
                free_key=True,
                trial_period=True
            )
            log.debug(f"Updating server key {key.id} with protocol {free_protocol.id}")
            await update_server_key(key.id, free_protocol.id)
            key = await get_key_id(key.id)

            # Подключаемся к серверу
            config = await connect_to_server_later(key, free_protocol, user_id)

            try:
                await download.delete()
            except TelegramBadRequest:
                log.debug(f"Message 'download' already deleted for user {user_id}")

            # Отправляем сообщение с ключом (меню установки уже включено в post_key_telegram)
            end_date = datetime.fromtimestamp(subscription_end, tz=timezone(timedelta(hours=CONFIG.UTC_time))).strftime("%d.%m.%Y")
            trial_message = _('trial_key_issued', lang).format(days=trial_days, end_date=end_date) + "\n\n" + _("trial_key_in_subscriptions", lang)
            await post_key_telegram(
                call,
                key,
                config,
                lang,
                custom_message=trial_message
            )

        except Exception as e:
            log.error(f'Server not connected for user {user_id}: {e}', exc_info=True)
            try:
                await download.delete()
            except TelegramBadRequest:
                log.debug(f"Message 'download' already deleted for user {user_id}")
            await call.message.answer(_('server_not_connected', lang))
    
    finally:
        # Удаляем блокировку
        user_locks.pop(user_id, None)