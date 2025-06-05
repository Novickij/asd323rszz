import logging
import time

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from bot.database.methods.delete import delete_key_in_user
from bot.database.methods.insert import add_payment
from bot.database.methods.get import (
    get_all_subscription,
    get_server_id,
    get_payment
)
from bot.database.methods.update import (
    person_banned_true,
    key_one_day_true,
    server_space_update,
    add_time_key
)
from bot.keyboards.inline.user_inline import mailing_button_message, renew_access_button
from bot.misc.Payment.KassaSmart import KassaSmart
from bot.misc.VPN.ServerManager import ServerManager
from bot.misc.language import Localization
from bot.misc.util import CONFIG

log = logging.getLogger(__name__)

_ = Localization.text

COUNT_SECOND_DAY = 86400

month_count_amount = {
    12: CONFIG.month_cost[3],
    6: CONFIG.month_cost[2],
    3: CONFIG.month_cost[1],
    1: CONFIG.month_cost[0],
}

async def loop(bot: Bot):
    try:
        all_persons = await get_all_subscription()
        for person in all_persons:
            await check_date(person, bot)
    except Exception as e:
        log.error(f"Error in loop: {e}")

async def check_date(person, bot: Bot):
    try:
        for key in person.keys:
            if key.free_key:
                continue
            if key.subscription <= int(time.time()):
                await delete_key(key)
                person.keys.remove(key)
                if len(person.keys) == 0:
                    await person_banned_true(person.tgid)
                try:
                    # Формируем клавиатуру с кнопкой "Мои подписки"
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text=_('my_subscription_btn', person.lang),
                            callback_data='my_subscription_btn'
                        )
                    ]])
                    await bot.send_message(
                        chat_id=person.tgid,
                        text=_('ended_sub_message', person.lang),
                        reply_markup=reply_markup
                    )
                except Exception:
                    log.info(f'User {person.tgid} blocked bot')
                    continue
            elif (key.subscription <= int(time.time()) + COUNT_SECOND_DAY
                  and not key.notion_oneday):
                await key_one_day_true(key_id=key.id)
                try:
                    await bot.send_message(
                        person.tgid,
                        _('alert_to_renew_sub', person.lang),
                        disable_web_page_preview=True,
                        reply_markup=await renew_access_button(
                            person.lang,
                            key_id=key.id
                        )
                    )
                    log.info(f"Sent renew alert to user {person.tgid} for key {key.id}")
                except Exception as e:
                    log.info(f'User {person.tgid} blocked bot or error: {e}')
                    continue
    except Exception as e:
        log.error(f"Error in the user date verification cycle: {e}")
        return

async def delete_key(key):
    await delete_key_in_user(key.id)
    if key.server is not None:
        server = await get_server_id(key.server)
        server_manager = ServerManager(server)
        await server_manager.login()
        try:
            if await server_manager.delete_client(key.user_tgid, key.id):
                all_client = await server_manager.get_all_user()
            else:
                raise Exception("Couldn't delete it")
        except Exception as e:
            log.error(f"Failed to connect to the server: {e}")
            raise e
        space = len(all_client)
        if not await server_space_update(server.id, space):
            raise

async def auto_pay_yookassa(person, key, bot: Bot) -> bool:
    if key.id_payment is None:
        return False
    payment = await get_payment(key.id_payment)
    if payment.month_count is None:
        return False
    price = int(month_count_amount.get(payment.month_count))
    # Определяем фактическое количество месяцев с учетом бонусов
    if payment.month_count == 6:
        effective_months = 7  # 6 месяцев > 7 месяцев
        bonus_message = _("bonus_months", person.lang).format(bonus=1)
    elif payment.month_count == 12:
        effective_months = 15  # 12 месяцев > 15 месяцев
        bonus_message = _("bonus_months", person.lang).format(bonus=3)
    else:
        effective_months = payment.month_count
        bonus_message = ""
    payment_system = await KassaSmart.auto_payment(
        config=CONFIG,
        lang_user=person.lang,
        payment_id=payment.id_payment,
        price=price
    )
    if payment_system is None:
        return False
    log.info(
        f'user ID: {person.tgid}'
        f' success auto payment {price} RUB Payment - YooKassaSmart'
    )
    await add_payment(
        person.tgid,
        price,
        'KassaSmart',
        id_payment=payment.id_payment,
        month_count=payment.month_count
    )
    await add_time_key(
        key.id,
        effective_months * CONFIG.COUNT_SECOND_MOTH,  # Используем effective_months
        id_payment=payment.id_payment
    )
    try:
        await bot.send_message(
            chat_id=person.tgid,
            text=_('loop_autopay_text', person.lang).format(
                month_count=effective_months,
                bonus=bonus_message
            )
        )
    except Exception:
        log.info(f'User {person.tgid} blocked bot')
    return True