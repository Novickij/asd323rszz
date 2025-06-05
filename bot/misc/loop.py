import logging
import time

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.main import engine  # Импорт функции engine
from bot.database.models.main import Keys

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
        async with AsyncSession(engine()) as db:  # Вызываем engine() для получения AsyncEngine
            current_time = int(time.time())
            for key in person.keys:
                # Проверяем, истёк ли ключ
                if key.subscription <= current_time and not key.notification_sent:
                    # Отключаем ключ на сервере (не удаляем!)
                    if key.server is not None:
                        try:
                            server = await get_server_id(key.server)
                            if server:
                                server_manager = ServerManager(server)
                                await server_manager.login()
                                email = f"{person.tgid}.{key.id}"
                                success = await server_manager.disable_client(person.tgid, key.id)
                                if success:
                                    log.info(f"Disabled key {key.id} (user {person.tgid}, email {email}) on server {key.server}")
                                else:
                                    log.warning(f"Failed to disable key {key.id} (email {email}) on server {key.server}")
                            else:
                                log.warning(f"Server {key.server} not found for key {key.id}")
                        except Exception as e:
                            log.error(f"Failed to disable key {key.id} (user {person.tgid}): {e}")
                    
                    # Помечаем, что уведомление отправлено
                    key_statement = select(Keys).filter(Keys.id == key.id)
                    key_db = (await db.execute(key_statement)).scalars().first()
                    if key_db:
                        key_db.notification_sent = True
                        await db.commit()
                        log.info(f"Marked key {key.id} as notification sent for user {person.tgid}")
                    
                    # Отправляем уведомление об истечении подписки
                    try:
                        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(
                                text=_('my_subscription_btn', person.lang),
                                callback_data='my_subscription_btn'
                            )
                        ]])
                        await bot.send_message(
                            chat_id=person.tgid,
                            text=_('ended_sub_message', person.lang),
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                        log.info(f"Sent expiration notification to user {person.tgid} for key {key.id}")
                    except Exception as e:
                        log.info(f'User {person.tgid} blocked bot or error: {e}')
                
                # Проверяем, истекает ли ключ через 1 день
                elif (key.subscription <= current_time + COUNT_SECOND_DAY
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
                            ),
                            parse_mode="HTML"
                        )
                        log.info(f"Sent renew alert to user {person.tgid} for key {key.id}")
                    except Exception as e:
                        log.info(f'User {person.tgid} blocked bot or error: {e}')
    except Exception as e:
        log.error(f"Error in the user date verification cycle: {e}")

async def auto_pay_yookassa(person, key, bot: Bot) -> bool:
    if key.id_payment is None:
        return False
    payment = await get_payment(key.id_payment)
    if payment.month_count is None:
        return False
    price = int(month_count_amount.get(payment.month_count))
    # Определяем фактическое количество месяцев с учётом бонусов
    if payment.month_count == 6:
        effective_months = 7
        bonus_message = _("bonus_months", person.lang).format(bonus=1)
    elif payment.month_count == 12:
        effective_months = 15
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
        f' success auto payment {price} RUB Payment - KassaSmart'
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
        effective_months * CONFIG.COUNT_SECOND_MONTH,
        id_payment=payment.id_payment
    )
    try:
        await bot.send_message(
            chat_id=person.tgid,
            text=_('loop_autopay_text', person.lang).format(
                month_count=effective_months,
                bonus=bonus_message
            ),
            parse_mode="HTML"
        )
    except Exception:
        log.info(f'User {person.tgid} blocked bot')
    return True

async def disable_key(key_id: int) -> bool:
    # Отключает ключ на сервере, но не удаляет его из базы
    async with AsyncSession(engine()) as db:  # Вызываем engine() для получения AsyncEngine
        key_statement = select(Keys).filter(Keys.id == key_id)
        key_result = await db.execute(key_statement)
        key = key_result.scalar_one_or_none()
        
        if key is None:
            log.error(f"Key {key_id} not found")
            return False
        
        # Отключаем ключ на сервере
        if key.server is not None:
            try:
                server = await get_server_id(key.server)
                if server:
                    server_manager = ServerManager(server)
                    await server_manager.login()
                    email = f"{key.user_tgid}.{key.id}"
                    success = await server_manager.disable_client(key.user_tgid, key.id)
                    if success:
                        log.info(f"Disabled key {key.id} (user {key.user_tgid}, email {email}) on server {key.server}")
                    else:
                        log.warning(f"Failed to disable key {key.id} (email {email}) on server {key.server}")
            except Exception as e:
                log.error(f"Failed to disable key {key.id} on server: {e}")
        
        return True

async def delete_key(key_id: int) -> bool:
    # Удаляет ключ из базы данных и отключает его на сервере (для админских действий)
    async with AsyncSession(engine()) as db:  # Вызываем engine() для получения AsyncEngine
        key_statement = select(Keys).filter(Keys.id == key_id)
        key_result = await db.execute(key_statement)
        key = key_result.scalar_one_or_none()
        
        if key is None:
            log.error(f"Key {key_id} not found")
            return False
        
        # Отключаем ключ на сервере
        if key.server is not None:
            try:
                server = await get_server_id(key.server)
                if server:
                    server_manager = ServerManager(server)
                    await server_manager.login()
                    email = f"{key.user_tgid}.{key.id}"
                    success = await server_manager.delete_client(key.user_tgid, key.id)
                    if success:
                        log.info(f"Deleted key {key.id} (user {key.user_tgid}, email {email}) on server {key.server}")
                    else:
                        log.warning(f"Failed to delete key {key.id} (email {email}) on server {key.server}")
            except Exception as e:
                log.error(f"Failed to delete key {key.id} on server: {e}")
        
        # Удаляем ключ из базы данных
        await db.delete(key)
        await db.commit()
        log.info(f"Deleted key {key_id} from database")
        return True