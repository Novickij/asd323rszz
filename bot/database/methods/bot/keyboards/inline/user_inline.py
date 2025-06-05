import logging
from datetime import datetime, timezone, timedelta

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.database.methods.get import get_type_vpn, get_key_user, get_person
from bot.misc.VPN.ServerManager import ServerManager
from bot.misc.callbackData import (
    ChoosingMonths,
    ChoosingPrise,
    ChooseLocation,
    MessageAdminUser,
    ChoosingLang,
    ChooseTypeVpn,
    ConnectMenu,
    ChooseTypeVpnHelp,
    DonatePrice,
    BackTypeVpn,
    ExtendKey,
    PromoCodeChoosing,
    DetailKey,
    TrialPeriod,
    CopyTelegramID
)
from bot.misc.language import Localization
from bot.misc.util import CONFIG

log = logging.getLogger(__name__)

_ = Localization.text

async def user_menu(lang: str, id_user: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    adjust = [1]  # Каждая кнопка в отдельной строке
    keys = await get_key_user(id_user, None)
    has_keys = len(keys) > 0
    
    kb.button(
        text="💳 Купить доступ / Продлить",
        callback_data='buy_subscription_btn',
    )
    
    if has_keys:
        kb.button(
            text="🔑 Моя подписка",
            callback_data='my_subscription_btn',
        )
        adjust.append(1)
    
    if not has_keys:
        kb.button(
            text="🔄 Восстановить доступ",
            callback_data='restore_access_btn',
        )
        adjust.append(1)
    
    person = await get_person(id_user)
    log.debug(f"User {id_user} trial_period: {person.trial_period}")
    if not person.trial_period:
        kb.button(
            text="🎁 Пробный период",
            callback_data='trial_period_btn',
        )
        adjust.append(1)
    
    kb.button(
        text="🛟 Помощь",
        callback_data='support_btn',
    )
    adjust.append(1)
    
    if CONFIG.is_admin(id_user):
        kb.button(
            text=_('admin_panel_btn', lang),
            callback_data='admin_panel_btn',
        )
        adjust.append(1)
    
    kb.adjust(*adjust)
    return kb.as_markup(resize_keyboard=True)

async def support_copy_button(lang: str, telegram_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="🆔 Скопировать Telegram ID",
        callback_data=CopyTelegramID(telegram_id=telegram_id)
    )
    kb.adjust(1)
    return kb.as_markup()

async def back_menu_button(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    await back_menu(kb, lang)
    return kb.as_markup(resize_keyboard=True)

async def back_menu(kb: InlineKeyboardBuilder, lang: str) -> InlineKeyboardBuilder:
    return kb.button(
        text=_('back_general_menu_btn', lang),
        callback_data='back_general_menu_btn',
    )

async def replenishment(
    config, price: str,
    lang: str, type_pay: str,
    key_id: int = 0,
    month_count: int = 0
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    adjust = [1]  # Каждая кнопка в отдельной строке
    if config.tg_wallet_token != "":
        kb.button(
            text=_('payments_wallet_pay_btn', lang),
            callback_data=ChoosingPrise(
                price=price,
                payment='WalletPay',
                type_pay=type_pay,
                key_id=key_id,
                month_count=month_count,
                id_prot=1,
                id_loc=0
            )
        )
        adjust.append(1)
    if config.yookassa_shop_id != "" and config.yookassa_secret_key != "":
        kb.button(
            text=_('payments_yookassa_btn', lang),
            callback_data=ChoosingPrise(
                price=price,
                payment='KassaSmart',
                type_pay=type_pay,
                key_id=key_id,
                month_count=month_count,
                id_prot=1,
                id_loc=0
            )
        )
        adjust.append(1)
    if config.yoomoney_token != "" and config.yoomoney_wallet_token != "":
        kb.button(
            text=_('payments_yoomoney_btn', lang),
            callback_data=ChoosingPrise(
                price=price,
                payment='YooMoney',
                type_pay=type_pay,
                key_id=key_id,
                month_count=month_count,
                id_prot=1,
                id_loc=0
            )
        )
        adjust.append(1)
    if config.cryptomus_key != "" and config.cryptomus_uuid != "":
        kb.button(
            text=_('payments_cryptomus_btn', lang),
            callback_data=ChoosingPrise(
                price=price,
                payment='Cryptomus',
                type_pay=type_pay,
                key_id=key_id,
                month_count=month_count,
                id_prot=1,
                id_loc=0
            )
        )
        adjust.append(1)
    if config.crypto_bot_api != '':
        kb.button(
            text='Crypto',
            callback_data=ChoosingPrise(
                price=price,
                payment='CryptoBot',
                type_pay=type_pay,
                key_id=key_id,
                month_count=month_count,
                id_prot=1,
                id_loc=0
            )
        )
        adjust.append(1)
    if config.lava_token_secret != "" and config.lava_id_project != "":
        kb.button(
            text=_('payments_lava_btn', lang),
            callback_data=ChoosingPrise(
                price=price,
                payment='Lava',
                type_pay=type_pay,
                key_id=key_id,
                month_count=month_count,
                id_prot=1,
                id_loc=0
            )
        )
        adjust.append(1)
    if config.token_stars != 'off':
        kb.button(
            text='Stars',
            callback_data=ChoosingPrise(
                price=price,
                payment='Stars',
                type_pay=type_pay,
                key_id=key_id,
                month_count=month_count,
                id_prot=1,
                id_loc=0
            )
        )
        adjust.append(1)
    if (
            config.yookassa_shop_id == ""
            and config.tg_wallet_token == ""
            and config.yoomoney_token == ""
            and config.lava_token_secret == ""
            and config.cryptomus_key == ""
            and config.crypto_bot_api == ""
            and config.token_stars == 'off'
    ):
        kb.button(text=_('payments_not_btn_1', lang), callback_data='none')
        kb.button(text=_('payments_not_btn_2', lang), callback_data='none')
        adjust.extend([1, 1])
    kb.button(
        text=_('back_general_menu_btn', lang),
        callback_data='answer_back_general_menu_btn',
    )
    adjust.append(1)
    kb.adjust(*adjust)
    return kb.as_markup()

async def choosing_promo_code(
    lang: str, promo_codes: list,
    price: str, type_pay: str,
    key_id: int = 0,
    month_count: int = 0,
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for promo_code in promo_codes:
        kb.button(
            text=_('promo_code_menu_btn', lang).format(
                name_promo=promo_code.text, percent=promo_code.percent
            ),
            callback_data=PromoCodeChoosing(
                id_promo=promo_code.id,
                percent=promo_code.percent,
                price=price,
                type_pay=type_pay,
                key_id=key_id,
                month_count=month_count
            )
        )
    kb.button(
        text=_('not_promo_code_menu_btn', lang),
        callback_data=PromoCodeChoosing(
            id_promo=0,
            percent=0,
            price=price,
            type_pay=type_pay,
            key_id=key_id,
            month_count=month_count
        )
    )
    kb.adjust(1)
    return kb.as_markup()

async def connect_menu(lang: str, trial_flag: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=_('vpn_connect_btn', lang),
        callback_data=ConnectMenu(action='connect_vpn')
    )
    if not trial_flag:
        kb.button(
            text=_('trial_period_btn', lang),
            callback_data=ConnectMenu(action='prob_period')
    )
    kb.adjust(1)
    return kb.as_markup()

async def choose_type_vpn(
    lang: str, key_id: int = 0, back_data: str = None, payment: bool = False
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    all_type_vpn = await get_type_vpn()
    adjust = [2, 1]
    for key, item in ServerManager.VPN_TYPES.items():
        if key in all_type_vpn:
            kb.button(
                text=item.NAME_VPN,
                callback_data=ChooseTypeVpn(
                    type_vpn=key,
                    key_id=key_id,
                    payment=payment
                )
            )
    if len(all_type_vpn) == 0:
        kb.button(
            text=_('type_vpn_none', lang),
            callback_data='none protocol'
        )
        adjust = [1]
    if back_data is not None:
        kb.button(
            text=_('admin_back_admin_menu_btn', lang),
            callback_data=back_data,
        )
    kb.adjust(*adjust)
    return kb.as_markup()

async def renew(
    config, lang: str,
    type_pay: str, back_data: str,
    key_id: int = 0, trial_flag: bool = True
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    adjust = []
    
    if not trial_flag:
        kb.button(
            text=_('trial_period_btn', lang),
            callback_data=TrialPeriod(
                id_prot=1,
                id_loc=0
            )
        )
        adjust.append(1)
    
    kb.button(
        text=_('to_extend_month_1_btn', lang).format(price=config.month_cost[0]),
        callback_data=ChoosingMonths(
            price=str(config.month_cost[0]),
            month_count=1,
            type_pay=type_pay,
            key_id=key_id
        )
    )
    adjust.append(1)
    
    kb.button(
        text=_('to_extend_month_2_btn', lang).format(price=config.month_cost[1]),
        callback_data=ChoosingMonths(
            price=str(config.month_cost[1]),
            month_count=3,
            type_pay=type_pay,
            key_id=key_id
        )
    )
    adjust.append(1)
    
    kb.button(
        text=_('to_extend_month_3_btn', lang).format(
            price=config.month_cost[2], bonus=_('bonus_1_month', lang)
        ),
        callback_data=ChoosingMonths(
            price=str(config.month_cost[2]),
            month_count=6,
            type_pay=type_pay,
            key_id=key_id
        )
    )
    adjust.append(1)
    
    kb.button(
        text=_('to_extend_month_4_btn', lang).format(
            price=config.month_cost[3], bonus=_('bonus_3_months', lang)
        ),
        callback_data=ChoosingMonths(
            price=str(config.month_cost[3]),
            month_count=12,
            type_pay=type_pay,
            key_id=key_id
        )
    )
    adjust.append(1)
    
    kb.button(
        text=_('admin_back_admin_menu_btn', lang),
        callback_data=back_data,
    )
    adjust.append(1)
    
    kb.adjust(*adjust)
    return kb.as_markup()

async def buy_subscription_menu(
    config, lang: str,
    type_pay: str, back_data: str,
    key_id: int = 0, trial_flag: bool = True
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    adjust = []
    
    if not trial_flag:
        kb.button(
            text=_('trial_period_btn', lang),
            callback_data=TrialPeriod(
                id_prot=1,
                id_loc=0
            )
        )
        adjust.append(1)
    
    kb.button(
        text=_('to_extend_month_1_btn', lang).format(price=config.month_cost[0]),
        callback_data=ChoosingMonths(
            price=str(config.month_cost[0]),
            month_count=1,
            type_pay=type_pay,
            key_id=key_id
        )
    )
    adjust.append(1)
    
    kb.button(
        text=_('to_extend_month_2_btn', lang).format(price=config.month_cost[1]),
        callback_data=ChoosingMonths(
            price=str(config.month_cost[1]),
            month_count=3,
            type_pay=type_pay,
            key_id=key_id
        )
    )
    adjust.append(1)
    
    kb.button(
        text=_('to_extend_month_3_btn', lang).format(
            price=config.month_cost[2], bonus=_('bonus_1_month', lang)
        ),
        callback_data=ChoosingMonths(
            price=str(config.month_cost[2]),
            month_count=6,
            type_pay=type_pay,
            key_id=key_id
        )
    )
    adjust.append(1)
    
    kb.button(
        text=_('to_extend_month_4_btn', lang).format(
            price=config.month_cost[3], bonus=_('bonus_3_months', lang)
        ),
        callback_data=ChoosingMonths(
            price=str(config.month_cost[3]),
            month_count=12,
            type_pay=type_pay,
            key_id=key_id
        )
    )
    adjust.append(1)
    
    kb.button(
        text=_('extend_existing_subscription_btn', lang),
        callback_data='my_subscription_btn'
    )
    adjust.append(1)
    
    kb.button(
        text=_('admin_back_admin_menu_btn', lang),
        callback_data=back_data,
    )
    adjust.append(1)
    
    kb.adjust(*adjust)
    return kb.as_markup()

async def price_menu(config, payment: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for price in config.deposit:
        kb.button(
            text=f'{price} ₽',
            callback_data=ChoosingPrise(
                price=int(price),
                payment=payment
            )
        )
    kb.adjust(1)
    return kb.as_markup()

async def choosing_lang() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for lang, cls in Localization.ALL_LANGUAGES.items():
        kb.button(text=cls, callback_data=ChoosingLang(lang=lang))
    kb.adjust(1)
    return kb.as_markup()

async def pay_and_check(
    link_invoice: str,
    lang: str,
    webapp: bool = False
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if not webapp:
        kb.button(text=_('user_pay_sub_btn', lang), url=link_invoice)
    else:
        kb.button(
            text=_('user_pay_sub_btn', lang),
            web_app=WebAppInfo(url=link_invoice)
        )
    kb.button(
        text=_('back_general_menu_btn', lang),
        callback_data='answer_back_general_menu_btn',
    )
    kb.adjust(1)
    return kb.as_markup()

async def pay_stars(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=_('user_pay_sub_btn', lang), pay=True)
    kb.button(
        text=_('back_general_menu_btn', lang),
        callback_data='answer_back_general_menu_btn'
    )
    kb.adjust(1)
    return kb.as_markup()

async def instruction_manual(lang: str, type_vPn: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if type_vpn == 0:
        kb.button(
            text=_('instruction_use_iphone_btn', lang),
            url=_('instruction_iphone_outline', lang, False)
        )
        kb.button(
            text=_('instruction_use_android_btn', lang),
            url=_('instruction_android_outline', lang, False)
        )
        kb.button(
            text=_('instruction_use_pc_btn', lang),
            url=_('instruction_windows_outline', lang, False)
        )
    elif type_vpn == 1 or type_vpn == 2:
        kb.button(
            text=_('instruction_use_iphone_btn', lang),
            url=_('instruction_iphone_vless', lang, False)
        )
        kb.button(
            text=_('instruction_use_android_btn', lang),
            url=_('instruction_android_vless', lang, False)
        )
        kb.button(
            text=_('instruction_use_pc_btn', lang),
            url=_('instruction_windows_vless', lang, False)
        )
    kb.button(
        text=_('back_general_menu_btn', lang),
        callback_data='answer_back_general_menu_btn',
    )
    kb.adjust(1)
    return kb.as_markup()

async def back_instructions(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=_('back_type_vpn', lang),
        callback_data='back_instructions'
    )
    kb.adjust(1)
    return kb.as_markup()

async def share_link(ref_link: str, lang: str, ref_balance: float = None) -> InlineKeyboardMarkup:
    link = f'https://t.me/share/url?url={ref_link}'
    kb = InlineKeyboardBuilder()
    kb.button(text=_('user_share_btn', lang), url=link)
    if ref_balance is not None:
        if ref_balance >= CONFIG.minimum_withdrawal_amount:
            kb.button(
                text=_('withdraw_funds_btn', lang).format(
                    min_withdrawal_amount=CONFIG.minimum_withdrawal_amount
                ),
                callback_data='withdrawal_of_funds'
            )
        else:
            kb.button(
                text=_('enough_funds_withdraw_btn', lang).format(
                    min_withdrawal_amount=CONFIG.minimum_withdrawal_amount
                ),
                callback_data='none'
            )
    await back_menu(kb, lang)
    kb.adjust(1)
    return kb.as_markup()

async def promo_code_button(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=_('write_the_promo_btn', lang), callback_data='promo_code')
    await back_menu(kb, lang)
    kb.adjust(1)
    return kb.as_markup()

async def choose_server(
    all_active_location: list,
    type_vpn: int,
    lang: str,
    key_id: int = 0,
    payment: bool = False
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for location in all_active_location:
        text_button = location.name
        kb.button(
            text=text_button,
            callback_data=ChooseLocation(
                id_location=location.id,
                key_id=key_id,
                type_vpn=type_vpn,
                payment=payment
            )
        )
    if payment:
        kb.button(
            text=_('back_type_vpn', lang),
            callback_data='generate_new_key'
        )
    else:
        kb.button(
            text=_('back_type_vpn', lang),
            callback_data=BackTypeVpn(key_id=key_id)
        )
    kb.adjust(1)
    return kb.as_markup()

async def message_admin_user(tgid_user: int, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=_('admin_user_send_reply_btn', lang),
        callback_data=MessageAdminUser(id_user=tgid_user)
    )
    kb.adjust(1)
    return kb.as_markup()

async def back_help_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=_('back_type_vpn', lang),
        callback_data='back_help_menu'
    )
    kb.adjust(1)
    return kb.as_markup()

async def choose_type_vpn_help(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text='Vless', callback_data=ChooseTypeVpnHelp(type_vpn=1))
    kb.button(
        text='Shadowsocks', callback_data=ChooseTypeVpnHelp(type_vpn=2)
    )
    kb.button(
        text=_('back_type_vpn', lang),
        callback_data='back_help_menu'
    )
    kb.adjust(1)
    return kb.as_markup()

async def donate_menu(lang: str) -> InlineKeyboardMarkup:
    donate_price = [99, 499, 999]
    kb = InlineKeyboardBuilder()
    kb.button(
        text=f'{donate_price[0]} ₽',
        callback_data=DonatePrice(price=donate_price[0])
    )
    kb.button(
        text=f'{donate_price[1]} ₽',
        callback_data=DonatePrice(price=donate_price[1])
    )
    kb.button(
        text=f'{donate_price[2]} ₽',
        callback_data=DonatePrice(price=donate_price[2])
    )
    kb.button(
        text=_('donate_input_price', lang),
        callback_data=DonatePrice(price=0)
    )
    kb.button(
        text=_('donate_list', lang),
        callback_data='donate_list'
    )
    await back_menu(kb, lang)
    kb.adjust(3, 1, 1)
    return kb.as_markup()

async def back_donate_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=_('back_type_vpn', lang),
        callback_data='back_donate_menu'
    )
    kb.adjust(1)
    return kb.as_markup()

async def connect_vpn_menu(lang: str, keys: list, id_detail: int = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    count_key = 1
    adjust = []
    utc_plus_3 = timezone(timedelta(hours=CONFIG.UTC_time))
    current_time = datetime.now(utc_plus_3)
    
    if id_detail is not None:
        # Показываем кнопки только для выбранного ключа
        for key in keys:
            if key.id == id_detail:
                time_from_db = datetime.fromtimestamp(key.subscription, tz=utc_plus_3)
                key_label = "Пробный " if key.trial_period else "Бесплатный " if key.free_key else ""
                if time_from_db > current_time:
                    kb.button(
                        text=_('install_btn', lang),
                        callback_data=f'install_key_{key.id}'
                    )
                    kb.button(
                        text=_('extend_key_btn', lang),
                        callback_data=ExtendKey(key_id=key.id)
                    )
                    adjust.extend([1, 1])
                else:
                    kb.button(
                        text=_('extend_key_btn', lang),
                        callback_data=ExtendKey(key_id=key.id)
                    )
                    adjust.append(1)
                break
    else:
        # Показываем список всех ключей
        for key in keys:
            time_from_db = datetime.fromtimestamp(key.subscription, tz=utc_plus_3)
            key_label = "Пробный " if key.trial_period else "Бесплатный " if key.free_key else ""
            if time_from_db > current_time:
                status = "🟢"
                button_text = f"{key_label}{status} Ключ {count_key}"
            else:
                status = "🔴"
                button_text = f"{key_label}{status} Ключ {count_key} (Неактивен, можно продлить)"
            kb.button(
                text=button_text,
                callback_data=DetailKey(key_id=key.id)
            )
            adjust.append(1)
            count_key += 1
    
    # Добавляем кнопку "Главное меню"
    kb.button(
        text=_('back_general_menu_btn', lang),
        callback_data='back_general_menu_btn'
    )
    adjust.append(1)
    
    kb.adjust(*adjust)
    return kb.as_markup()

async def check_follow_chanel(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=CONFIG.name_channel,
        url=CONFIG.link_channel
    )
    kb.button(
        text=_('no_follow_button', lang),
        callback_data='check_follow_chanel'
    )
    kb.adjust(1)
    return kb.as_markup()

async def trial_pay_button(lang: str, price: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=_('payment_button', lang),
        callback_data=ChoosingPrise(
            price=price,
            payment='KassaSmart',
            type_pay=CONFIG.type_payment.get(4),
            key_id=0,
            id_prot=1,
            id_loc=0
        )
    )
    kb.adjust(1)
    return kb.as_markup()

async def mailing_button_message(lang: str, text: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if text == 'not_button_mailing_btn':
        return kb.as_markup()
    kb.button(
        text=_(text, lang),
        callback_data=_(text, lang),
    )
    kb.adjust(1)
    return kb.as_markup()

async def renew_access_button(lang: str, key_id: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=_('renew_access_btn', lang),
        callback_data=ExtendKey(key_id=key_id)
    )
    kb.adjust(1)
    return kb.as_markup()

async def create_key_menu(lang: str, key_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=_('install_btn', lang),
        callback_data=f'install_key_{key_id}'
    )
    kb.button(
        text=_('extend_key_btn', lang),
        callback_data=ExtendKey(key_id=key_id)
    )
    kb.button(
        text=_('back_general_menu_btn', lang),
        callback_data='back_general_menu_btn'
    )
    kb.adjust(1)
    log.debug(f"Generated key menu for key_id {key_id}")
    return kb.as_markup()