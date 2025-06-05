import logging

from aiogram.filters import Filter, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.payload import decode_payload

from bot.database.methods.get import get_person, get_key_user
from bot.database.methods.insert import add_new_person
from bot.keyboards.inline.user_inline import check_follow_chanel, \
    connect_vpn_menu
from bot.misc.language import Localization
from bot.misc.util import CONFIG

_ = Localization.text

log = logging.getLogger(__name__)


class IsAdmin(Filter):
    def __init__(self):
        config = CONFIG
        self.admin_ids = config.admin_tg_ids

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.admin_ids


class IsBlocked(Filter):

    async def __call__(self, message: Message) -> bool:
        user = await get_person(message.from_user.id)
        if user is not None and user.blocked:
            return False
        if await check_subs(message, message.from_user.id, message.bot):
            return True
        return False


class IsBlockedCall(Filter):

    async def __call__(self, call: CallbackQuery) -> bool:
        user = await get_person(call.from_user.id)
        await call.answer()
        if user is not None and user.blocked:
            return False
        if await check_subs(call.message, call.from_user.id, call.message.bot):
            return True
        return False


async def check_subs(message, user_telegram_id, bot):
    if not CONFIG.check_follow:
        return True
    try:
        user_channel_status = await bot.get_chat_member(
            chat_id=CONFIG.id_channel,
            user_id=user_telegram_id
        )
    except Exception as e:
        await message.answer(
            _('error_check_follow', CONFIG.languages),
        )
        return True
    check = user_channel_status.status != 'left'
    if not check:
        await message.answer(
            _('no_follow', CONFIG.languages),
            reply_markup=await check_follow_chanel(CONFIG.languages)
        )
    return check
