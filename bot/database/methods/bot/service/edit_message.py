from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, InlineKeyboardMarkup


async def edit_message(
        message: Message,
        caption: str = None,
        reply_markup: InlineKeyboardMarkup = None,
        parse_mode: str = None
) -> None:
    try:
        if caption:
            await message.edit_caption(
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await message.edit_reply_markup(
                reply_markup=reply_markup
            )
    except TelegramAPIError:
        if caption:
            await message.answer(
                text=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await message.answer(
                text="",
                reply_markup=reply_markup
            )