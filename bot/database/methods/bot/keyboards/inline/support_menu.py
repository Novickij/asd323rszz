from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.misc.language import Localization

_ = Localization.text

async def support_menu(lang: str) -> InlineKeyboardMarkup:
    """
    Формирует клавиатуру для меню поддержки.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=_("write_to_support_btn", lang),
                url="https://t.me/WolfPNsupport_bot"
            )
        ],
        [
            InlineKeyboardButton(
                text=_("documents_btn", lang),
                callback_data="documents_btn"
            )
        ],
        [
            InlineKeyboardButton(
                text=_("general_menu_btn", lang),
                callback_data="back_general_menu_btn"
            )
        ]
    ])
    return keyboard

async def documents_menu(lang: str) -> InlineKeyboardMarkup:
    """
    Формирует клавиатуру для меню документов.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=_("privacy_policy_btn", lang),
                url="https://telegra.ph/Privacy-Policy-Example-10-01"
            )
        ],
        [
            InlineKeyboardButton(
                text=_("public_offer_btn", lang),
                url="https://telegra.ph/Public-Offer-Example-10-01"
            )
        ],
        [
            InlineKeyboardButton(
                text=_("refund_policy_btn", lang),
                url="https://telegra.ph/Refund-Policy-Example-10-01"
            )
        ],
        [
            InlineKeyboardButton(
                text=_("general_menu_btn", lang),
                callback_data="back_general_menu_btn"
            )
        ]
    ])
    return keyboard