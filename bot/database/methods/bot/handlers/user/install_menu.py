import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.misc.language import Localization
from bot.misc.callbackData import InstallMenuCallback
from bot.misc.util import CONFIG
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.main import engine
from bot.database.models.main import Keys
from sqlalchemy.orm import selectinload
from bot.misc.VPN.ServerManager import ServerManager
from bot.database.methods.get import get_name_location_server
import urllib.parse
import base64

log = logging.getLogger(__name__)

_ = Localization.text

async def install_main_menu(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """
    Главное меню выбора устройства для установки.
    """
    text = _("install_main_menu", lang)
    kb = InlineKeyboardBuilder()
    
    kb.button(
        text="📱 iPhone | iPad (iOS)",
        callback_data=InstallMenuCallback(action="ios")
    )
    kb.button(
        text="🤖 Android",
        callback_data=InstallMenuCallback(action="android")
    )
    kb.button(
        text="Huawei",
        callback_data=InstallMenuCallback(action="huawei")
    )
    kb.button(
        text="💻 Windows",
        callback_data=InstallMenuCallback(action="windows")
    )
    kb.button(
        text="🍎 MacOS",
        callback_data=InstallMenuCallback(action="macos")
    )
    kb.button(
        text="📺 TV",
        callback_data=InstallMenuCallback(action="tv")
    )
    kb.button(
        text="➕ Установить на второе устройство",
        callback_data=InstallMenuCallback(action="second_device")
    )
    kb.button(
        text=_("back_general_menu_btn", lang),
        callback_data="back_general_menu_btn"
    )
    
    kb.adjust(1)
    return text, kb.as_markup()

async def generate_deeplink(user_id: int, platform: str, lang: str, key_id: int = None) -> str:
    """
    Генерирует deeplink для указанной платформы, пользователя и конкретного ключа.
    """
    log.info(f"Generating deeplink for user {user_id}, platform: {platform}, key_id: {key_id}")
    try:
        async with AsyncSession(autoflush=False, bind=engine()) as db:
            query = select(Keys).filter(Keys.user_tgid == user_id)
            if key_id:
                query = query.filter(Keys.id == key_id)
                log.debug(f"Filtering by key_id: {key_id}")
            else:
                query = query.order_by(Keys.subscription.desc())
                log.debug("No key_id provided, selecting latest key by subscription")
            query = query.options(selectinload(Keys.server_table))
            key = await db.execute(query)
            key = key.scalars().first()
            
            if key is None or key.server_table is None:
                log.warning(f"No active keys or server table for user {user_id}, key_id {key_id}")
                return None
            
            log.debug(f"Selected key: {key.id}, server_id: {key.server_table.id}")
            server_manager = ServerManager(key.server_table)
            await server_manager.login()
            name_location = await get_name_location_server(key.server_table.id)
            name_location = name_location.replace("Германия", "Germany")
            config = await server_manager.get_key(
                user_id,
                name_key=name_location,
                key_id=key.id
            )
            
            if config is None:
                log.error(f"Failed to generate config for user {user_id}, key {key.id}")
                return None
            
            log.debug(f"Generated config: {config}")
            if "&flow=" not in config:
                config = config + "&flow=xtls-rprx-vision"
                log.debug(f"Added flow parameter: {config}")
            
            # Формируем deeplink
            encoded_vless = urllib.parse.quote(config, safe='~()*!.\'')
            if platform == "ios":
                deeplink = f"v2raytun://import/{encoded_vless}"
            elif platform in ["android", "huawei"]:
                deeplink = f"v2raytun://import/{encoded_vless}"
            else:
                log.error(f"Unsupported platform: {platform}")
                return None
            
            log.debug(f"Generated deeplink: {deeplink}")
            
            # Формируем редирект-ссылку
            redirect_file = f"redirect_{platform}.html"
            redirect_base_url = "http://85.192.63.159:8080"
            redirect_url = f"{redirect_base_url}/{redirect_file}?deeplink={urllib.parse.quote(deeplink)}&vless={urllib.parse.quote(config)}&platform={platform}"
            
            log.info(f"Generated redirect URL for user {user_id}, platform: {platform}, key_id: {key_id}, url: {redirect_url}")
            return redirect_url
    except Exception as e:
        log.error(f"Error generating deeplink for user {user_id}, platform {platform}, key_id {key_id}: {e}", exc_info=True)
        return None

async def ios_install_menu(lang: str, user_id: int = None, key_id: int = None) -> tuple[str, InlineKeyboardMarkup]:
    """
    Инструкция для автоматической настройки на iOS.
    """
    text = (
        "📱 " + _("auto_setup", lang) + "\n\n"
        "➊ " + _("install_v2raytun", lang) + "\n"
        "🔁 " + _("return_to_chat", lang) + "\n"
        "➋ " + _("press_configure", lang) + "\n"
        "✅ " + _("allow_app_open", lang) + "\n"
        "➌ " + _("press_enable_button", lang) + "\n"
        "✅ " + _("allow_config_add", lang) + "\n\n"
        "❗️ " + _("if_v2raytun_unsupported", lang)
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(
        text="1️⃣ " + _("install_app_btn", lang),
        url="https://apps.apple.com/ru/app/v2raytun/id6476628951"
    )
    if user_id and key_id:
        redirect_url = await generate_deeplink(user_id, "ios", lang, key_id=key_id)
        if redirect_url:
            kb.button(
                text="2️⃣ " + _("configure_connection_btn", lang),
                url=redirect_url
            )
        else:
            kb.button(
                text="2️⃣ " + _("configure_connection_btn", lang),
                callback_data=InstallMenuCallback(action="no_key_ios")
            )
    else:
        kb.button(
            text="2️⃣ " + _("configure_connection_btn", lang),
            callback_data=InstallMenuCallback(action="no_key_ios")
        )
    kb.button(
        text="📞 V2Box (" + _("if_v2raytun_not_working", lang) + ")",
        callback_data=InstallMenuCallback(action="v2box_ios")
    )
    kb.button(
        text="🆘 " + _("problems_occurred_btn", lang),
        callback_data=InstallMenuCallback(action="manual_install_ios")
    )
    kb.button(
        text="📱 " + _("choose_another_device_btn", lang),
        callback_data=InstallMenuCallback(action="main_menu")
    )
    kb.button(
        text=_("back_general_menu_btn", lang),
        callback_data="back_general_menu_btn"
    )
    
    kb.adjust(1)
    return text, kb.as_markup()

async def android_install_menu(lang: str, user_id: int = None, key_id: int = None) -> tuple[str, InlineKeyboardMarkup]:
    """
    Инструкция для автоматической настройки на Android.
    """
    text = (
        "📱 " + _("auto_setup", lang) + "\n\n"
        "➊ " + _("install_v2raytun", lang) + "\n"
        "🔁 " + _("return_to_chat", lang) + "\n"
        "➋ " + _("press_configure", lang) + "\n"
        "✅ " + _("allow_app_open", lang) + "\n"
        "➌ " + _("press_enable_button", lang) + "\n"
        "✅ " + _("allow_config_add", lang) + "\n\n"
        "❗️ " + _("if_v2raytun_unsupported", lang)
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(
        text="1️⃣ " + _("install_app_btn", lang),
        url="https://play.google.com/store/apps/details?id=com.v2raytun.android"
    )
    if user_id and key_id:
        redirect_url = await generate_deeplink(user_id, "android", lang, key_id=key_id)
        if redirect_url:
            kb.button(
                text="2️⃣ " + _("configure_connection_btn", lang),
                url=redirect_url
            )
        else:
            kb.button(
                text="2️⃣ " + _("configure_connection_btn", lang),
                callback_data=InstallMenuCallback(action="no_key_android")
            )
    else:
        kb.button(
            text="2️⃣ " + _("configure_connection_btn", lang),
            callback_data=InstallMenuCallback(action="no_key_android")
        )
    kb.button(
        text="📞 V2Box (" + _("if_v2raytun_not_working", lang) + ")",
        callback_data=InstallMenuCallback(action="v2box_android")
    )
    kb.button(
        text="🆘 " + _("problems_occurred_btn", lang),
        callback_data=InstallMenuCallback(action="manual_install_android")
    )
    kb.button(
        text="📱 " + _("choose_another_device_btn", lang),
        callback_data=InstallMenuCallback(action="main_menu")
    )
    kb.button(
        text=_("back_general_menu_btn", lang),
        callback_data="back_general_menu_btn"
    )
    
    kb.adjust(1)
    return text, kb.as_markup()

async def huawei_install_menu(lang: str, user_id: int = None, key_id: int = None) -> tuple[str, InlineKeyboardMarkup]:
    """
    Инструкция для автоматической настройки на Huawei.
    """
    text = (
        "📱 " + _("auto_setup", lang) + "\n\n"
        "➊ " + _("install_v2raytun", lang) + "\n"
        "🔁 " + _("return_to_chat", lang) + "\n"
        "➋ " + _("press_configure", lang) + "\n"
        "✅ " + _("allow_app_open", lang) + "\n"
        "➌ " + _("press_enable_button", lang) + "\n"
        "✅ " + _("allow_config_add", lang)
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(
        text="1️⃣ " + _("install_app_btn", lang),
        url="https://appgallery.huawei.com/app/v2raytun"
    )
    if user_id and key_id:
        redirect_url = await generate_deeplink(user_id, "huawei", lang, key_id=key_id)
        if redirect_url:
            kb.button(
                text="2️⃣ " + _("configure_connection_btn", lang),
                url=redirect_url
            )
        else:
            kb.button(
                text="2️⃣ " + _("configure_connection_btn", lang),
                callback_data=InstallMenuCallback(action="no_key_huawei")
            )
    else:
        kb.button(
            text="2️⃣ " + _("configure_connection_btn", lang),
            callback_data=InstallMenuCallback(action="no_key_huawei")
        )
    kb.button(
        text="🆘 " + _("problems_occurred_btn", lang),
        callback_data=InstallMenuCallback(action="manual_install_huawei")
    )
    kb.button(
        text="📱 " + _("choose_another_device_btn", lang),
        callback_data=InstallMenuCallback(action="main_menu")
    )
    kb.button(
        text=_("back_general_menu_btn", lang),
        callback_data="back_general_menu_btn"
    )
    
    kb.adjust(1)
    return text, kb.as_markup()

async def windows_install_menu(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """
    Инструкция для настройки на Windows.
    """
    text = (
        "🖥️ " + _("windows_setup_prompt", lang) + "\n\n"
        "⮕ " + _("vpn_for_selected_apps", lang) + "\n"
        "⮕ " + _("vpn_for_entire_pc", lang) + "\n"
        "⮕ " + _("internet_not_working", lang)
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(
        text=_("vpn_for_selected_apps_btn", lang),
        url="https://telegra.ph/vpn-selected-apps"
    )
    kb.button(
        text=_("vpn_for_entire_pc_btn", lang),
        url="https://telegra.ph/vpn-entire-pc"
    )
    kb.button(
        text=_("internet_not_working_btn", lang),
        url="https://telegra.ph/internet-not-working"
    )
    kb.button(
        text="📱 " + _("choose_another_device_btn", lang),
        callback_data=InstallMenuCallback(action="main_menu")
    )
    kb.button(
        text=_("back_general_menu_btn", lang),
        callback_data="back_general_menu_btn"
    )
    
    kb.adjust(1)
    return text, kb.as_markup()

async def macos_install_menu(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """
    Инструкция для настройки на MacOS.
    """
    text = (
        "🍎 Инструкция для MacOS:\n\n"
        "1️⃣ Нажмите кнопку «🔑 Моя подписка» в главном меню этого бота.\n"
        "• Чтобы открыть Главное меню, нажмите «Меню» в левом нижнем углу экрана → Главное меню\n"
        "2️⃣ Выберете ключ подписки, который хотите установить\n"
        "3️⃣ Перед Вами будет Ваш ключ подписки (vless://…..), нажмите на него один раз, чтобы скопировать\n"
        "4️⃣ Скачайте приложение V2RayTun <a href=\"https://apps.apple.com/ru/app/v2raytun/id6476628951?tgme_nopreview=1\">тут</a> или Streisand <a href=\"https://apps.apple.com/ru/app/streisand/id6450534064?tgme_nopreview=1\">тут</a> или V2Box <a href=\"https://apps.apple.com/ru/app/v2box-v2ray-client/id6446814690?tgme_nopreview=1\">тут</a> (в зависимости от вашей версии ОС и удобства для вас)\n"
        "5️⃣ Откройте приложение и нажмите '+' для добавления новой конфигурации\n"
        "6️⃣ Нажмите «Добавить из буфера» или добавьте ключ вручную\n"
        "7️⃣ Разрешите добавление конфигурации\n"
        "✅ Нажмите кнопку подключения и наслаждайтесь безопасным интернетом!"
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(
        text="📱 " + _("choose_another_device_btn", lang),
        callback_data=InstallMenuCallback(action="main_menu")
    )
    kb.button(
        text=_("back_general_menu_btn", lang),
        callback_data="back_general_menu_btn"
    )
    
    kb.adjust(1)
    return text, kb.as_markup()

async def tv_install_menu(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """
    Меню выбора типа TV устройства.
    """
    text = (
        "📺 " + _("tv_device_type", lang) + "\n\n"
        "• " + _("android_tv", lang) + "\n"
        "• " + _("apple_tv", lang) + "\n"
        "• " + _("yandex_tv", lang) + "\n\n"
        "❗️ " + _("tv_requirements", lang)
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(
        text=_("android_tv_btn", lang),
        url="https://telegra.ph/android-tv"
    )
    kb.button(
        text=_("apple_tv_btn", lang),
        url="https://telegra.ph/apple-tv"
    )
    kb.button(
        text=_("yandex_tv_btn", lang),
        url="https://telegra.ph/yandex-tv"
    )
    kb.button(
        text="📱 " + _("choose_another_device_btn", lang),
        callback_data=InstallMenuCallback(action="main_menu")
    )
    kb.button(
        text=_("back_general_menu_btn", lang),
        callback_data="back_general_menu_btn"
    )
    
    kb.adjust(1)
    return text, kb.as_markup()

async def second_device_install_menu(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """
    Инструкция для установки на второе устройство.
    """
    text = (
        "📱 Как подключить второе устройство:\n\n"
        "1️⃣ Нажмите кнопку «🔑 Моя подписка» в главном меню этого бота.\n"
        "• Чтобы открыть Главное меню, нажмите «Меню» в левом нижнем углу экрана → Главное меню\n"
        "2️⃣ Выберете ключ подписки, который хотите установить\n"
        "3️⃣ Перед Вами будет Ваш ключ подписки (vless://…..), нажмите на него один раз, чтобы скопировать\n"
        "4️⃣ Перенесите ключ подписку на второе устройство любым удобным способом (например, отправьте через месседжер)\n"
        "5️⃣ На втором устройстве (если это телефон или планшет): скачайте приложение V2RayTun\n"
        "   • Если V2RayTun не поддерживается, используйте V2Box\n"
        "6️⃣ Скопируйте на втором устройстве полученный ключ подписки\n"
        "7️⃣ В приложении V2RayTun нажмите «+» в правом верхнем углу\n"
        "   • Выберите «Вставить из буфера»\n"
        "   • Подтвердите разрешения на установку\n"
        "✅ Готово! Приятного использования!"
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(
        text="📱 " + _("choose_another_device_btn", lang),
        callback_data=InstallMenuCallback(action="main_menu")
    )
    kb.button(
        text=_("back_general_menu_btn", lang),
        callback_data="back_general_menu_btn"
    )
    
    kb.adjust(1)
    return text, kb.as_markup()

async def manual_install_menu(lang: str, device: str, user_id: int = None, key_id: int = None) -> tuple[str, InlineKeyboardMarkup]:
    """
    Инструкция для ручной установки (iOS, Android, Huawei) с возможностью автоматической настройки.
    """
    text = (
        "📝 " + _("manual_install", lang) + "\n\n"
        "1️⃣ " + _("download_v2raytun", lang) + "\n"
        "2️⃣ " + _("remove_old_configs", lang) + "\n"
        "3️⃣ " + _("return_to_bot", lang) + "\n"
        "4️⃣ " + _("open_main_menu", lang) + "\n"
        "5️⃣ " + _("go_to_subscription", lang) + "\n"
        "6️⃣ " + _("select_active_key", lang) + "\n"
        "7️⃣ " + _("copy_key", lang) + "\n"
        "🔁 " + _("return_to_v2raytun", lang) + "\n"
        "8️⃣ " + _("add_config_plus", lang) + "\n"
        "9️⃣ " + _("add_from_clipboard", lang) + "\n"
        "🔟 " + _("allow_paste", lang) + "\n"
        "✅ " + _("enable_v2raytun", lang) + "\n\n"
        "❗️ " + _("if_problems_persist", lang) + "\n"
        "👨🏼‍💻 " + _("contact_support", lang)
    )
    
    kb = InlineKeyboardBuilder()
    if user_id and key_id:
        redirect_url = await generate_deeplink(user_id, device, lang, key_id=key_id)
        if redirect_url:
            kb.button(
                text="2️⃣ " + _("configure_connection_btn", lang),
                url=redirect_url
            )
        else:
            kb.button(
                text="2️⃣ " + _("configure_connection_btn", lang),
                callback_data=InstallMenuCallback(action=f"no_key_{device}")
            )
    else:
        kb.button(
            text="2️⃣ " + _("configure_connection_btn", lang),
            callback_data=InstallMenuCallback(action=f"no_key_{device}")
        )
    kb.button(
        text=" " + _("write_to_support_btn", lang),
        url="https://t.me/suppotyspn_bot"
    )
    kb.button(
        text="📱 " + _("choose_another_device_btn", lang),
        callback_data=InstallMenuCallback(action="main_menu")
    )
    kb.button(
        text=_("back_general_menu_btn", lang),
        callback_data="back_general_menu_btn"
    )
    
    kb.adjust(1)
    return text, kb.as_markup()

async def v2box_instruction(lang: str, device: str) -> tuple[str, InlineKeyboardMarkup]:
    """
    Текстовая инструкция для V2Box (iOS и Android).
    """
    text = (
        "📱 Инструкция по настройке V2Box:\n\n"
        "1️⃣ Скачайте V2Box\n1.1 iPhone | iPad <a href=\"https://apps.apple.com/ru/app/v2box-v2ray-client/id6446814690?tgme_nopreview=1\">V2BOX</a>\n"
        "1.2 Android <a href=\"https://play.google.com/store/apps/details?id=dev.hexasoftware.v2box&hl=ru&pli=1?tgme_nopreview=1\">V2BOX</a>\n"
        "2️⃣ Нажмите кнопку «🔑 Моя подписка» в главном меню этого бота\n"
        "3️⃣ Выберете нужный ключ подписки\n"
        "4️⃣ Перед Вами будет Ваш ключ подписки (vless://…..), нажмите на него один раз, чтобы скопировать\n"
        "5️⃣ Откройте приложение V2BOX, нажмите снизу «Configs» → нажмите «+» в правом верхнем углу → нажмите на надпись «Import v2ray uri from clipboard» или «Добавить из буфера»\n"
        "6️⃣ Разрешите добавление конфигурации\n"
        "✅ Нажмите кнопку подключения и наслаждайтесь безопасным интернетом!"
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(
        text="📱 " + _("choose_another_device_btn", lang),
        callback_data=InstallMenuCallback(action="main_menu")
    )
    kb.button(
        text=_("back_general_menu_btn", lang),
        callback_data="back_general_menu_btn"
    )
    
    kb.adjust(1)
    return text, kb.as_markup()