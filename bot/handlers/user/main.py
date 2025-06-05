import logging
import random
import urllib.parse
import base64
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.utils.formatting import Text, Code
from aiogram.utils.payload import decode_payload
from sqlalchemy.ext.asyncio import AsyncSession
from bot.handlers.user.free_vpn import free_vpn_btn
from bot.database.main import engine
from bot.database.methods.get import (
    get_person,
    get_key_id,
    get_key_user,
    get_name_location_server,
    get_active_keys_count,
    get_promo_codes_user
)
from bot.database.methods.update import (
    server_space_update,
    update_lang,
    update_server_key,
    update_switch_key
)
from bot.database.methods.delete import delete_key_in_user
from bot.database.models.main import Keys, Servers, Persons
from bot.keyboards.inline.user_inline import (
    renew,
    buy_subscription_menu,
    choosing_lang,
    connect_vpn_menu,
    user_menu,
    back_menu_button,
    instruction_manual,
    replenishment
)
from bot.keyboards.inline.support_menu import support_menu, documents_menu
from bot.misc.VPN.ServerManager import ServerManager
from bot.misc.language import Localization, get_lang
from bot.misc.util import CONFIG
from bot.handlers.user.install_menu import (
    install_main_menu,
    ios_install_menu,
    android_install_menu,
    huawei_install_menu,
    windows_install_menu,
    macos_install_menu,
    tv_install_menu,
    second_device_install_menu,
    manual_install_menu,
    v2box_instruction
)
from bot.misc.callbackData import (
    DetailKey,
    EditKey,
    ExtendKey,
    ChoosingMonths,
    ChoosingPrise,
    PromoCodeChoosing,
    InstallMenuCallback
)
from bot.filters.main import IsBlocked, IsBlockedCall, check_subs
from bot.database.methods.insert import add_new_person
from bot.service.edit_message import edit_message
from bot.misc.Payment.KassaSmart import KassaSmart
import aiohttp
import asyncio
from aiogram.exceptions import TelegramBadRequest

log = logging.getLogger(__name__)

_ = Localization.text
btn_text = Localization.get_reply_button

# Создаём роутеры
user_router = Router()
registered_router = Router()

def generate_random_load():
    return round(random.uniform(2.1, 8.2), 1)

async def check_follow(user_id, bot):
    try:
        user_channel_status = await bot.get_chat_member(
            chat_id=CONFIG.id_channel,
            user_id=user_id
        )
        return user_channel_status.status != 'left'
    except Exception as e:
        log.error(f"Failed to check follow status for user {user_id}: {e}")
        return False

@registered_router.callback_query(F.data == 'check_follow_chanel')
async def connect_vpn(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing check_follow_chanel for user {callback.from_user.id}")
    if await check_follow(callback.from_user.id, callback.message.bot):
        person = await get_person(callback.from_user.id)
        await show_start_message(callback.message, person, lang)
        await callback.answer()
        return
    await callback.answer(
        _('no_follow_bad_check', lang),
        show_alert=True
    )

@registered_router.message(Command("start"))
async def command(message: Message, state: FSMContext, command: Command = None):
    if message.from_user.is_bot:
        return
    lang = await get_lang(message.from_user.id, state)
    log.debug(f"Processing /start for user {message.from_user.id}")
    await state.clear()
    if not await get_person(message.from_user.id):
        try:
            user_name = f'@{str(message.from_user.username)}'
        except Exception as e:
            log.error(e)
            user_name = str(message.from_user.username)
        reference = decode_payload(command.args) if command.args else None
        if reference is not None:
            if reference.isdigit():
                reference = int(reference)
            else:
                reference = None
            if reference != str(message.from_user.id):
                await give_bonus_invitee(message, reference, lang)
            else:
                await message.answer(_('referral_error', lang))
                reference = None
        await add_new_person(
            message.from_user,
            user_name,
            reference
        )
        text_user = Text(
            _('message_new_user', lang), '\n',
            '👤: ' f'@{message.from_user.username}',
            ' ', message.from_user.full_name, '\n',
            'ID:', Code(message.from_user.id)
        )
        try:
            for admin_id in CONFIG.admin_tg_ids:
                await message.bot.send_message(
                    admin_id,
                    **text_user.as_kwargs()
                )
        except Exception as e:
            log.error(f"Failed to send message to admin: {e}")
    person = await get_person(message.from_user.id)
    if person.blocked:
        return
    if not await check_subs(message, message.from_user.id, message.bot):
        return
    await show_start_message(message, person, lang)

# Обработчик команды /subscriptions
@user_router.message(Command("subscriptions"))
async def command_subscriptions(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id, state)
    log.debug(f"Processing /subscriptions for user {message.from_user.id}")
    await state.clear()
    
    if not await check_subs(message, message.from_user.id, message.bot):
        return
    
    try:
        keys = await get_key_user(message.from_user.id, None)
        log.debug(f"Subscriptions for user {message.from_user.id}: {len(keys)} keys found, keys: {[k.id for k in keys]}")
        if keys:
            reply_markup = await connect_vpn_menu(lang, keys)
            await message.answer(
                text=await format_keys_message(keys, lang, is_detail=False),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            log.debug(f"No keys found for user {message.from_user.id}, showing subscription prompt")
            person = await get_person(message.from_user.id)
            trial_flag = person.trial_period
            if trial_flag:
                caption = _('no_active_subscriptions', lang)
            else:
                caption = _('no_active_subscriptions_trial_available', lang)
            await message.answer(
                text=caption,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=_('buy_subscription_btn', lang),
                            callback_data='buy_subscription_btn'
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=_('trial_period_btn', lang) if not trial_flag else _('no_trial_message', lang),
                            callback_data='trial_period_btn' if not trial_flag else 'none'
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=_('back_general_menu_btn', lang),
                            callback_data='back_general_menu_btn'
                        )
                    ]
                ]),
                parse_mode="HTML"
            )
        log.info(f"Successfully processed /subscriptions for user {message.from_user.id}")
    except Exception as e:
        log.error(f"Failed to process /subscriptions for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer(
            text=_('server_not_connected', lang),
            reply_markup=await user_menu(lang, message.from_user.id),
            parse_mode="HTML"
        )

# Обработчик команды /support
@user_router.message(Command("support"))
async def command_support(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id, state)
    log.debug(f"Processing /support for user {message.from_user.id}")
    await state.clear()
    
    if not await check_subs(message, message.from_user.id, message.bot):
        return
    
    telegram_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        active_keys_count = await get_active_keys_count(telegram_id, db)
    caption = _("support_message", lang).format(
        telegram_id=f"<code>{telegram_id}</code>",
        username=username,
        active_keys_count=active_keys_count
    )
    await message.answer(
        text=caption,
        reply_markup=await support_menu(lang),
        parse_mode="HTML"
    )

# Обработчик команды /ust
@user_router.message(Command("ust"))
async def command_ust(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id, state)
    log.debug(f"Processing /ust for user {message.from_user.id}")
    await state.clear()
    
    if not await check_subs(message, message.from_user.id, message.bot):
        return
    
    text, reply_markup = await install_main_menu(lang)
    await message.answer(
        text=text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# Обработчик меню установки
@user_router.callback_query(InstallMenuCallback.filter())
async def handle_install_menu(callback: CallbackQuery, callback_data: InstallMenuCallback, state: FSMContext):
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Handling install_menu action: {callback_data.action} for user {callback.from_user.id}")
    
    # Получаем selected_key_id из состояния
    data = await state.get_data()
    selected_key_id = data.get('selected_key_id')
    log.debug(f"Retrieved selected_key_id: {selected_key_id} for user {callback.from_user.id}")
    
    action = callback_data.action
    try:
        if action == "main_menu":
            text, reply_markup = await install_main_menu(lang)
        elif action == "ios":
            text, reply_markup = await ios_install_menu(lang, user_id=callback.from_user.id, key_id=selected_key_id)
        elif action == "android":
            text, reply_markup = await android_install_menu(lang, user_id=callback.from_user.id, key_id=selected_key_id)
        elif action == "huawei":
            text, reply_markup = await huawei_install_menu(lang, user_id=callback.from_user.id, key_id=selected_key_id)
        elif action == "windows":
            text, reply_markup = await windows_install_menu(lang)
        elif action == "macos":
            text, reply_markup = await macos_install_menu(lang)
        elif action == "tv":
            text, reply_markup = await tv_install_menu(lang)
        elif action == "second_device":
            text, reply_markup = await second_device_install_menu(lang)
        elif action in ["manual_install_ios", "manual_install_android", "manual_install_huawei"]:
            device = action.split("_")[-1]
            text, reply_markup = await manual_install_menu(lang, device, user_id=callback.from_user.id, key_id=selected_key_id)
        elif action in ["v2box_ios", "v2box_android"]:
            device = action.split("_")[-1]
            text, reply_markup = await v2box_instruction(lang, device)
        elif action in ["no_key_ios", "no_key_android", "no_key_huawei"]:
            text = _("no_active_keys_config", lang)
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=_("buy_subscription_btn", lang),
                        callback_data="buy_subscription_btn"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=_("back_general_menu_btn", lang),
                        callback_data="back_general_menu_btn"
                    )
                ]
            ])
        else:
            log.warning(f"Unknown action {action} for user {callback.from_user.id}")
            text = _("unknown_action", lang)
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=_("back_general_menu_btn", lang),
                        callback_data="back_general_menu_btn"
                    )
                ]
            ])
        
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    
    except Exception as e:
        log.error(f"Error in handle_install_menu for user {callback.from_user.id}, action {action}: {e}", exc_info=True)
        text = _("server_not_connected", lang)
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_("back_general_menu_btn", lang),
                    callback_data="back_general_menu_btn"
                )
            ]
        ])
        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            log.warning(f"Failed to edit message in error handler for user {callback.from_user.id}: {e}")
            await callback.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
    await callback.answer()

# Обработчики возврата в главное меню
@user_router.callback_query(F.data.in_(btn_text('general_menu_btn')))
async def back_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing back_main_menu for user {callback.from_user.id}")
    await state.clear()
    person = await get_person(callback.from_user.id)
    await show_start_message(callback.message, person, lang)

@user_router.message(F.text.in_(btn_text('back_general_menu_btn')))
async def back_main_menu(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    log.debug(f"Processing back_main_menu (text) for user {message.from_user.id}")
    await state.clear()
    person = await get_person(message.from_user.id)
    await show_start_message(message, person, lang)

@user_router.callback_query(F.data == 'back_general_menu_btn')
async def back_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing back_general_menu_btn for user {callback.from_user.id}")
    await state.clear()
    person = await get_person(callback.from_user.id)
    try:
        await callback.message.delete()
    except TelegramBadRequest as e:
        log.warning(f"Failed to delete message for user {callback.from_user.id}: {e}")
    await show_start_message(callback.message, person, lang)

@user_router.callback_query(F.data == 'answer_back_general_menu_btn')
async def back_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing answer_back_general_menu_btn for user {callback.from_user.id}")
    await state.clear()
    person = await get_person(callback.from_user.id)
    await show_start_message(callback.message, person, lang)

# Отображение главного меню
async def show_start_message(message: Message, person, lang):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        active_keys_count = await get_active_keys_count(person.tgid, db)
    
    keys = await get_key_user(person.tgid)
    valid_keys = []
    for key in keys:
        if key.server_table:
            utc_plus_3 = timezone(timedelta(hours=CONFIG.UTC_time))
            current_time = datetime.now(utc_plus_3)
            end_date = datetime.fromtimestamp(key.subscription, tz=utc_plus_3)
            if end_date < current_time and key.is_active:
                # Отключаем ключ, если срок действия истёк
                server_manager = ServerManager(key.server_table)
                await server_manager.disable_client(person.tgid, key.id)
                log.info(f"Key {key.id} disabled due to expiration during show_start_message")
            valid_keys.append(key)  # Все ключи показываем, даже неактивные
        else:
            log.debug(f"Deleting invalid key {key.id} for user {person.tgid} due to missing server_table")
            await delete_key_in_user(key.id)

    # Формируем текст главного меню
    text = _('main_menu', lang).format(nagruzka=generate_random_load())
    text += '\n\n' + _('subscription_status', lang)
    text += '\n' + _('active_keys_count', lang).format(active_keys_count=active_keys_count)
    
    if valid_keys:
        utc_plus_3 = timezone(timedelta(hours=CONFIG.UTC_time))
        current_time = datetime.now(utc_plus_3)
        count_key = 1
        for key in valid_keys:
            text += f'\n'
            time_from_db = datetime.fromtimestamp(key.subscription, tz=utc_plus_3)
            if time_from_db > current_time and key.is_active:
                days = (time_from_db - current_time).days
                text += f'\n🔑 Ключ №{count_key} ({days} дн.)'
            else:
                text += f'\n🔑 Ключ №{count_key} (Неактивен)'
            count_key += 1
        text = text.replace('рџ”‘', '🔑')  # Заменяем битые эмодзи, если есть
    else:
        text += '\n' + _('no_active_subscriptions', lang)
    
    await message.answer(
        text=text,
        reply_markup=await user_menu(lang, person.tgid),
        parse_mode="HTML"
    )

# Бонус за рефералов
async def give_bonus_invitee(m, reference, lang):
    if reference is None:
        return
    if CONFIG.referral_day == 0:
        await m.bot.send_message(
            reference,
            _('referral_new_user_zero', lang),
            parse_mode="HTML"
        )
        return
    keys = await get_key_user(reference)
    await m.bot.send_message(
        reference,
        _('referral_new_user', lang).format(
            day=CONFIG.referral_day,
        ),
        reply_markup=await connect_vpn_menu(
            lang,
            keys,
            'referral_bonus',
        ),
        parse_mode="HTML"
    )

# Отправка сообщения с повторными попытками
async def send_with_retry(callback: CallbackQuery, text: str, reply_markup, parse_mode: str = None, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            await callback.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return True
        except aiohttp.ClientConnectionError as e:
            log.warning(f"Retry {attempt + 1}/{max_retries} for sending message to {callback.from_user.id}: {e}")
            await asyncio.sleep(2 ** attempt)
    log.error(f"Failed to send message to {callback.from_user.id} after {max_retries} retries")
    return False

# Отправка ключа в Telegram
async def post_key_telegram(callback: CallbackQuery, key, config, lang):
    log.debug(f"Posting key for user {callback.from_user.id}, config: {config}")
    try:
        def escape_markdown_v2(text):
            chars = r'_[]()~`>#+-=|{}.!'
            for char in chars:
                text = text.replace(char, f'\\{char}')
            return text

        escaped_config = escape_markdown_v2(config)
        text = f"```\n{escaped_config}\n```"
        reply_markup = await user_menu(lang, callback.from_user.id)
        
        success = await send_with_retry(
            callback,
            text=text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2',
            max_retries=3
        )
        
        if not success:
            await callback.message.answer(
                text=_('key_generated_error', lang),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return

        import io
        file = io.StringIO(config)
        await callback.message.answer_document(
            document=FSInputFile(file, filename=f"vpn_key_{key.id}.txt"),
            caption=_('key_file_caption', lang),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"Failed to send key for user {callback.from_user.id}: {e}")
        await callback.message.answer(
            text=_('key_generated_error', lang),
            reply_markup=await user_menu(lang, callback.from_user.id),
            parse_mode="HTML"
        )

# Форматирование сообщения о ключах
async def format_keys_message(keys, lang, is_detail=False, selected_key_id=None):
    utc_plus_3 = timezone(timedelta(hours=CONFIG.UTC_time))
    current_time = datetime.now(utc_plus_3)
    header = 'manage_key_header' if is_detail else 'user_keys_header'
    keys_text = _(header, lang) + ":\n\n"
    
    if is_detail and selected_key_id is not None:
        # Находим номер ключа в списке
        key_number = None
        selected_key = None
        for i, key in enumerate(keys, start=1):
            if key.id == selected_key_id:
                key_number = i
                selected_key = key
                break
        
        if key_number is None or selected_key is None:
            return _("key_not_found", lang) + "\n"
        
        end_date = datetime.fromtimestamp(selected_key.subscription, tz=utc_plus_3)
        status = "🟢" if end_date > current_time and selected_key.is_active else "🔴"
        end_date_str = end_date.strftime("%d-%m-%Y")
        key_label = "Пробный " if selected_key.trial_period else ""
        if end_date > current_time and selected_key.is_active:
            keys_text += f"{key_label}{status} Ключ {key_number} до {end_date_str} (выбранный ключ)\n"
        else:
            keys_text += f"{key_label}{status} Ключ {key_number} (Неактивен) (выбранный ключ)\n"
    else:
        count_key = 1
        for key in keys:
            end_date = datetime.fromtimestamp(key.subscription, tz=utc_plus_3)
            status = "🟢" if end_date > current_time and key.is_active else "🔴"
            end_date_str = end_date.strftime("%d-%m-%Y")
            key_label = "Пробный " if key.trial_period else ""
            if end_date > current_time and key.is_active:
                keys_text += f"{key_label}{status} Ключ {count_key} до {end_date_str}\n"
            else:
                keys_text += f"{key_label}{status} Ключ {count_key} (Неактивен)\n"
            count_key += 1
    
    if not is_detail:
        keys_text += "\n" + _('select_key_prompt', lang)
    return keys_text

# Отображение деталей ключа
async def show_key_details(
        callback: CallbackQuery,
        callback_data: DetailKey,
        state: FSMContext
) -> None:
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Showing key details for user {callback.from_user.id}, key_id={callback_data.key_id}")
    try:
        async with AsyncSession(autoflush=False, bind=engine()) as db:
            key = await db.execute(
                select(Keys)
                .filter(Keys.id == callback_data.key_id, Keys.user_tgid == callback.from_user.id)
                .options(selectinload(Keys.server_table))
            )
            key = key.scalars().first()
            if key is None:
                log.error(f"Key {callback_data.key_id} not found or does not belong to user {callback.from_user.id}")
                await callback.message.answer(
                    text=_('error_add_server_client', lang),
                    parse_mode="HTML"
                )
                await callback.answer()
                return

            server_table = key.server_table
            config = None
            if server_table:
                try:
                    server_manager = ServerManager(server_table)
                    # Отключаем клиента, если ключ истёк
                    utc_plus_3 = timezone(timedelta(hours=CONFIG.UTC_time))
                    current_time = datetime.now(utc_plus_3)
                    end_date = datetime.fromtimestamp(key.subscription, tz=utc_plus_3)
                    if end_date < current_time and key.is_active:
                        await server_manager.disable_client(callback.from_user.id, key.id)
                        log.info(f"Key {key.id} disabled due to expiration during show_key_details")

                    # Пытаемся получить конфигурацию
                    await server_manager.login()
                    name_location = await get_name_location_server(server_table.id)
                    config = await server_manager.get_key(
                        callback.from_user.id,
                        name_key=name_location,
                        key_id=key.id
                    )
                    if config is None:
                        log.warning(f"Failed to generate config for key {callback_data.key_id}, possibly inactive or server issue")
                except Exception as e:
                    log.error(f"Error while fetching config for key {callback_data.key_id}: {e}")
                    config = None

            # Сохраняем key_id в состояние FSM
            await state.update_data(selected_key_id=callback_data.key_id)

            def escape_markdown_v2(text):
                chars = r'_[]()~`>#+-=|{}.!'
                for char in chars:
                    text = text.replace(char, f'\\{char}')
                return text
            
            keys = await get_key_user(callback.from_user.id, None)
            message_text = await format_keys_message(keys, lang, is_detail=True, selected_key_id=callback_data.key_id)
            message_text = escape_markdown_v2(message_text)

            # Добавляем информацию о статусе ключа
            utc_plus_3 = timezone(timedelta(hours=CONFIG.UTC_time))
            current_time = datetime.now(utc_plus_3)
            end_date = datetime.fromtimestamp(key.subscription, tz=utc_plus_3)
            status = "🟢" if end_date > current_time and key.is_active else "🔴"
            key_label = "Пробный " if key.trial_period else ""
            status_text = f"\n{key_label}{status} Ключ (действует до {end_date.strftime('%d-%m-%Y')})"
            status_text = escape_markdown_v2(status_text)

            # Добавляем конфигурацию, если она доступна
            if config:
                escaped_config = escape_markdown_v2(config)
                log.debug(f"Escaped config for key {callback_data.key_id}: {escaped_config}")
                message_text += f"\n🔑 Ваш ключ для подключения:\n```\n{escaped_config}\n```"
            else:
                warning_text = f"\n⚠️ Конфигурация недоступна (ключ неактивен или сервер не отвечает). Пожалуйста, продлите подписку для активации."
                message_text += escape_markdown_v2(warning_text)

            reply_markup = await connect_vpn_menu(lang, keys, id_detail=callback_data.key_id)
            
            await callback.message.delete()
            await callback.message.answer(
                text=message_text + status_text,
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )
            log.info(f"Successfully showed key details for user {callback.from_user.id}, key_id={callback_data.key_id}")
    
    except Exception as e:
        log.error(f"Failed to show key details for user {callback.from_user.id}, key_id={callback_data.key_id}: {e}", exc_info=True)
        await callback.message.answer(
            text=_('server_not_connected', lang),
            parse_mode="HTML"
        )
    
    await callback.answer()

# Генерация нового ключа
async def generate_new_key(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback.from_user.id, state)
    user = await get_person(callback.from_user.id)
    log.debug(f"Generating new key for user {callback.from_user.id}, trial_flag={user.trial_period}")
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Servers).filter(
            Servers.type_vpn == 1,
            Servers.work == True,
            Servers.free_server == False
        ).order_by(Servers.actual_space)
        result = await db.execute(statement)
        server = result.scalars().first()
        if not server:
            log.error(f"No available servers for user {callback.from_user.id}")
            await callback.message.answer(_('not_server', lang), parse_mode="HTML")
            await callback.answer()
            return
        log.debug(f"Selected server {server.id} for user {callback.from_user.id}")
    caption = _('choosing_month_sub', lang)
    log.debug(f"Raw caption: {caption}")
    await callback.message.delete()
    await callback.message.answer(
        text=caption,
        reply_markup=await buy_subscription_menu(
            CONFIG,
            lang,
            CONFIG.type_payment.get(0),
            back_data='back_general_menu_btn',
            trial_flag=user.trial_period
        ),
        parse_mode="HTML"
    )
    await callback.answer()

# Установка ключа
async def install_key(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback.from_user.id, state)
    key_id = int(callback.data.split('_')[-1])
    log.debug(f"Processing install_key for user {callback.from_user.id}: key_id={key_id}")
    
    # Сохраняем key_id в состояние
    await state.update_data(selected_key_id=key_id)
    
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        key = await db.execute(
            select(Keys)
            .filter(Keys.id == key_id)
            .options(selectinload(Keys.server_table))
        )
        key = key.scalars().first()
        if key is None:
            log.error(f"Key {key_id} not found for user {callback.from_user.id}")
            await callback.message.answer(
                text=_('error_add_server_client', lang),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        log.debug(f"Showing install_main_menu for key {key_id}")
        text, reply_markup = await install_main_menu(lang)
        await callback.message.delete()
        await callback.message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    await callback.answer()

# Продление ключа
async def extend_key(
        callback: CallbackQuery,
        callback_data: ExtendKey,
        state: FSMContext
) -> None:
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Starting extend_key for user {callback.from_user.id}: key_id={callback_data.key_id}")
    try:
        async with AsyncSession(autoflush=False, bind=engine()) as db:
            key = await db.execute(
                select(Keys)
                .filter(Keys.id == callback_data.key_id)
                .options(selectinload(Keys.server_table))
            )
            key = key.scalars().first()
            if key is None:
                log.error(f"Key {callback_data.key_id} not found for user {callback.from_user.id}")
                await callback.message.answer(_('error_add_server_client', lang), parse_mode="HTML")
                await callback.answer()
                return
            log.debug(f"Key {callback_data.key_id} found for user {callback.from_user.id}")
            
            user = await get_person(callback.from_user.id)
            if user is None:
                log.error(f"User {callback.from_user.id} not found")
                await callback.message.answer(_('error_add_server_client', lang), parse_mode="HTML")
                await callback.answer()
                return
            log.debug(f"User {callback.from_user.id} found, trial_flag={user.trial_period}")
            
            type_payment = CONFIG.type_payment.get(1)
            if type_payment is None:
                log.error(f"CONFIG.type_payment.get(1) returned None for user {callback.from_user.id}")
                await callback.message.answer(_('no_payment_methods', lang), parse_mode="HTML")
                await callback.answer()
                return
            
            server_table = key.server_table
            if server_table is None:
                log.error(f"Server table not found for key {callback_data.key_id}")
                await callback.message.answer(_('server_not_connected', lang), parse_mode="HTML")
                await callback.answer()
                return
            
            log.debug(f"Calling renew with: type_payment={type_payment}, key_id={key.id}, trial_flag={user.trial_period}")
            reply_markup = await renew(
                CONFIG,
                lang,
                type_payment,
                back_data='back_general_menu_btn',
                key_id=key.id,
                trial_flag=user.trial_period
            )
            caption = _('extending_month_sub', lang)
            log.debug(f"Raw caption: {caption}")

            await callback.message.delete()
            await callback.message.answer(
                text=caption,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            log.info(f"Successfully generated renew markup for user {callback.from_user.id}, key_id={callback_data.key_id}")
    except Exception as e:
        log.error(f"Failed to extend key for user {callback.from_user.id}, key_id={callback_data.key_id}: {e}", exc_info=True)
        await callback.message.answer(_('server_not_connected', lang), parse_mode="HTML")
    await callback.answer()

# Обработка оплаты подписки
async def process_subscription_payment(
        callback: CallbackQuery,
        callback_data: ChoosingMonths,
        state: FSMContext
) -> None:
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing subscription payment for user {callback.from_user.id}: price={callback_data.price}, month_count={callback_data.month_count}, type_pay={callback_data.type_pay}, key_id={callback_data.key_id}")
    try:
        promo_code = await get_promo_codes_user(callback.from_user.id)
        if (
                len(promo_code) != 0
                and callback_data.type_pay == CONFIG.type_payment.get(0)
        ):
            await callback.message.delete()
            await callback.message.answer(
                text=_('want_use_promocode', lang),
                reply_markup=await choosing_promo_code(
                    lang,
                    promo_code,
                    callback_data.price,
                    callback_data.type_pay,
                    key_id=callback_data.key_id,
                    month_count=callback_data.month_count
                ),
                parse_mode="HTML"
            )
            
        else:
            await callback.message.delete()
            await callback.message.answer(
                text=_('method_replenishment', lang),
                reply_markup=await replenishment(
                    config=CONFIG,
                    price=callback_data.price,
                    lang=lang,
                    type_pay=callback_data.type_pay,
                    key_id=callback_data.key_id,
                    month_count=callback_data.month_count
                ),
                parse_mode="HTML"
            )
            text = Text(
                _('admin_message_choosing_month', CONFIG.languages)
                .format(
                    username=callback.from_user.username,
                    user_id=callback.from_user.id,
                    month_count=callback_data.month_count
                )
            )
            for admin_id in CONFIG.admin_tg_ids:
                try:
                    await callback.message.bot.send_message(
                        admin_id,
                        **text.as_kwargs()
                    )
                except TelegramBadRequest as e:
                    log.warning(f"Failed to send message to {admin_id} for user {callback.from_user.id}: {e}")
                except Exception as e:
                    log.error(f"Unexpected error sending message to admin {admin_id} for user {callback.from_user.id}: {e}")
        log.info(f"Successfully processed ChoosingMonths for user {callback.from_user.id}")
        await state.update_data(
            price=callback_data.price,
            month_count=callback_data.month_count,
            type_pay=callback_data.type_pay,
            key_id=callback_data.key_id
        )
    except Exception as e:
        log.error(f"Failed to process subscription payment for user {callback.from_user.id}: {e}", exc_info=True)
        await callback.message.answer(_('server_not_connected', lang), parse_mode="HTML")
    await callback.answer()

# Обработка метода оплаты
async def process_payment_method(
        callback: CallbackQuery,
        callback_data: ChoosingPrise,
        state: FSMContext
) -> None:
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing payment method for user {callback.from_user.id}: payment={callback_data.payment}, price={callback_data.price}, month_count={callback_data.month_count}, type_pay={callback_data.type_pay}, key_id={callback_data.key_id}, id_prot={callback_data.id_prot}, id_loc={callback_data.id_loc}")
    try:
        payment_system = KassaSmart(
            config=CONFIG,
            message=callback.message,
            telegram_id=callback.from_user.id,
            price=int(callback_data.price),
            month_count=callback_data.month_count,
            type_pay=callback_data.type_pay,
            key_id=callback_data.key_id,
            id_prot=callback_data.id_prot,
            id_loc=callback_data.id_loc
        )
        await payment_system.to_pay()
        # После успешной оплаты активируем ключ
        if callback_data.key_id:
            async with AsyncSession(autoflush=False, bind=engine()) as db:
                key = await db.execute(
                    select(Keys)
                    .filter(Keys.id == callback_data.key_id)
                    .options(selectinload(Keys.server_table))
                )
                key = key.scalars().first()
                if key and key.server_table:
                    server_manager = ServerManager(key.server_table)
                    await server_manager.enable_client(callback.from_user.id, callback_data.key_id)
                    log.info(f"Key {callback_data.key_id} enabled after payment for user {callback.from_user.id}")
        log.info(f"Successfully initiated payment for user {callback.from_user.id} with {callback_data.payment}")
    except Exception as e:
        log.error(f"Failed to process payment method for user {callback.from_user.id}: {e}")
        await callback.message.answer(_('error_payment', lang), parse_mode="HTML")
    await callback.answer()

# Восстановление доступа
async def restore_access(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing restore_access for user {callback.from_user.id}")
    keys = await get_key_user(callback.from_user.id, None)
    log.debug(f"Restore access for user {callback.from_user.id}: {len(keys)} keys found")

    if keys:
        key = keys[0]
        subscription_seconds = key.subscription
        log.info(f"User {callback.from_user.id} subscription: {subscription_seconds}")
        
        if subscription_seconds < 9466848000:  # Проверка на валидность времени подписки
            log.warning(f"Invalid subscription for user {callback.from_user.id}: {subscription_seconds}")
            subscription_seconds = 2592000  # 30 дней по умолчанию
        
        end_date = (datetime.now(timezone(timedelta(hours=CONFIG.UTC_time))) + 
                   timedelta(seconds=subscription_seconds)).strftime("%d.%m.%Y")

        try:
            async with AsyncSession(autoflush=False, bind=engine()) as db:
                # Выбираем сервер для ключа
                if key.server_table:
                    selected_server = key.server_table
                else:
                    statement = (
                        select(Servers)
                        .filter(
                            Servers.type_vpn == 1,
                            Servers.work == True,
                            Servers.free_server == False
                        )
                        .order_by(Servers.actual_space)
                    )
                    selected_server = (await db.execute(statement)).scalars().first()

                if not selected_server:
                    log.error(f"No available servers for user {callback.from_user.id}")
                    await callback.message.delete()
                    await callback.message.answer(
                        text=_('not_server', lang),
                        reply_markup=await user_menu(lang, callback.from_user.id),
                        parse_mode="HTML",
                    )
                    await callback.answer()
                    return

                await update_server_key(key.id, selected_server.id)
                key = await get_key_id(key.id)

                server_manager = ServerManager(selected_server)
                await server_manager.login()
                name_location = await get_name_location_server(selected_server.id)
                
                if await server_manager.add_client(callback.from_user.id, key.id) is None:
                    raise Exception('user/server_manager add_client error')

                config = await server_manager.get_key(
                    callback.from_user.id,
                    name_key=name_location,
                    key_id=key.id
                )

                server_parameters = await server_manager.get_all_user()
                await server_space_update(selected_server.id, len(server_parameters))

                log.info(f"Successfully generated key {config} for user {callback.from_user.id}")
                await callback.message.delete()
                text, reply_markup = await install_main_menu(lang)
                await callback.message.answer(
                    text=_('restore_success', lang).format(end_date=end_date) + "\n\n" + text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
                await post_key_telegram(callback, key, config, lang)

        except Exception as e:
            log.error(f"Failed to restore access for user {callback.from_user.id}: {e}")
            await callback.message.delete()
            await callback.message.answer(
                text=_('server_not_connected', lang),
                reply_markup=await user_menu(lang, callback.from_user.id),
                parse_mode="HTML",
            )
            await callback.answer()
            return

    else:
        support_button = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=_('contact_support_btn', lang),
                        url=CONFIG.support_url
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=_('back_general_menu_btn', lang),
                        callback_data='back_general_menu_btn'
                    )
                ]
            ]
        )
        await callback.message.delete()
        await callback.message.answer(
            text=_('restore_not_found', lang),
            reply_markup=support_button,
            parse_mode="HTML",
        )

    await callback.answer()

# Пробный период
async def trial_period(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Trial period request for user {callback.from_user.id}")
    user = await get_person(callback.from_user.id)
    if user.trial_period:
        await callback.message.delete()
        await callback.message.answer(
            text=_('no_trial_message', lang),
            reply_markup=await user_menu(lang, callback.from_user.id),
            parse_mode="HTML",
        )
    else:
        await free_vpn_btn(callback)
    await callback.answer()

# Поддержка
async def support_subscription(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing support request for user {callback.from_user.id}")
    telegram_id = callback.from_user.id
    username = callback.from_user.username or "No username"
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        active_keys_count = await get_active_keys_count(telegram_id, db)
    
    caption = _(
        'support_message', lang
    ).format(
        telegram_id=f"<code>{telegram_id}</code>",
        username=username,
        active_keys_count=active_keys_count
    )

    await callback.message.delete()
    await callback.message.answer(
        text=caption,
        reply_markup=await support_menu(lang),
        parse_mode="HTML",
    )
    await callback.answer()

# Документы
async def documents_subscription(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing documents request for user {callback.from_user.id}")
    await callback.message.delete()
    await callback.message.answer(
        text=_('documents_menu_message', lang),
        reply_markup=await documents_menu(lang),
        parse_mode="HTML",
    )
    await callback.answer()

# Покупка подписки
async def buy_subscription(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing buy_subscription request for user {callback.from_user.id}")
    try:
        user = await get_person(callback.from_user.id)
        log.debug(f"User {callback.from_user.id} found, trial_flag={user.trial_period}")
        type_payment = CONFIG.type_payment.get(0)
        if type_payment is None:
            log.error(f"No payment type available for user {callback.from_user.id}")
            await callback.message.delete()
            await callback.message.answer(
                text=_('no_payment_methods', lang),
                reply_markup=await user_menu(lang, callback.from_user.id),
                parse_mode="HTML",
            )
            await callback.answer()
            return
        reply_markup = await buy_subscription_menu(
            CONFIG,
            lang,
            type_payment,
            back_data='back_general_menu_btn',
            trial_flag=user.trial_period
        )
        log.debug(f"Subscription menu markup generated for user {callback.from_user.id}")
        caption = _('choosing_month_sub', lang)
        log.debug(f"Raw caption: {caption}")
        await callback.message.delete()
        await callback.message.answer(
            text=caption,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        await state.update_data(
            price="249",
            month_count=1,
            type_pay=type_payment,
            key_id=0
        )
        log.info(f"Successfully processed buy_subscription request for user {callback.from_user.id}")
    except Exception as e:
        log.error(f"Failed to process buy_subscription for user {callback.from_user.id}: {e}")
        await callback.message.delete()
        await callback.message.answer(
            text=_('server_not_connected', lang),
            reply_markup=await user_menu(lang, callback.from_user.id),
            parse_mode="HTML",
        )
    await callback.answer()

# Мои подписки
async def my_subscription(callback: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback.from_user.id, state)
    log.debug(f"Processing my_subscription request for user {callback.from_user.id}")
    try:
        keys = await get_key_user(callback.from_user.id, None)
        log.debug(f"Subscription details for user {callback.from_user.id}: {len(keys)} keys found")
        if keys:
            reply_markup = await connect_vpn_menu(lang, keys)
            log.debug(f"Connect VPN menu markup generated for user {callback.from_user.id}")
            await callback.message.delete()
            await callback.message.answer(
                text=await format_keys_message(keys, lang, is_detail=False),
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        else:
            log.debug(f"No keys found for user {callback.from_user.id}, showing subscription prompt")
            await callback.message.delete()
            await callback.message.answer(
                text=_('no_active_subscriptions', lang),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=_('buy_subscription_btn', lang),
                                callback_data='buy_subscription_btn'
                            ),
                            InlineKeyboardButton(
                                text=_('back_general_menu_btn', lang),
                                callback_data='back_general_menu_btn'
                            )
                        ]
                    ]
                ),
                parse_mode="HTML",
            )
        log.info(f"Successfully processed my_subscription request for user {callback.from_user.id}")
    except Exception as e:
        log.error(f"Failed to process my_subscription for user {callback.from_user.id}: {e}")
        await callback.message.delete()
        await callback.message.answer(
            text=_('server_not_connected', lang),
            reply_markup=await user_menu(lang, callback.from_user.id),
            parse_mode="HTML",
        )
    await callback.answer()

# Регистрация обработчиков
user_router.callback_query.register(show_key_details, DetailKey.filter())
user_router.callback_query.register(generate_new_key, F.data == 'generate_new_key')
user_router.callback_query.register(install_key, F.data.startswith('install_key_'))
user_router.callback_query.register(extend_key, ExtendKey.filter())
user_router.callback_query.register(process_subscription_payment, ChoosingMonths.filter())
user_router.callback_query.register(process_payment_method, ChoosingPrise.filter(F.payment == 'KassaSmart'))
user_router.callback_query.register(restore_access, F.data == "restore_access_btn")
user_router.callback_query.register(trial_period, F.data == "trial_period_btn")
user_router.callback_query.register(support_subscription, F.data == "support_btn")
user_router.callback_query.register(documents_subscription, F.data == "documents_btn")
user_router.callback_query.register(buy_subscription, F.data == "buy_subscription_btn")
user_router.callback_query.register(my_subscription, F.data == "my_subscription_btn")