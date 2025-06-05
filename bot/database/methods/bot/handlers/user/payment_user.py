import logging
import re

from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import Text
from aiogram.exceptions import TelegramBadRequest

from bot.database.methods.update import promo_user_use, update_auto_pay
from bot.misc.Payment.CryptoBot import CryptoBot
from bot.misc.Payment.Cryptomus import Cryptomus
from bot.misc.Payment.KassaSmart import KassaSmart
from bot.misc.Payment.Lava import Lava
from bot.misc.Payment.Stars import Stars, stars_router
from bot.misc.Payment.YooMoney import YooMoney
from bot.misc.language import Localization, get_lang
from bot.misc.util import CONFIG
from bot.misc.callbackData import (
    ChoosingMonths,
    ChoosingPyment,
    ChoosingPrise, DonatePrice, PromoCodeChoosing, AutoPay,
)

from bot.keyboards.inline.user_inline import (
    price_menu,
    replenishment,
    donate_menu,
    back_donate_menu,
    choosing_promo_code, back_menu_button,
)
from bot.database.methods.get import (
    get_person,
    get_all_donate,
    get_promo_codes_user
)
from bot.service.edit_message import edit_message

log = logging.getLogger(__name__)

_ = Localization.text
btn_text = Localization.get_reply_button

callback_user = Router()
callback_user.include_router(stars_router)
CONVERT_PANY_RUBLS = 100

types_of_payments = {
    'KassaSmart': KassaSmart,
    'YooMoney': YooMoney,
    'Lava': Lava,
    'Cryptomus': Cryptomus,
    'CryptoBot': CryptoBot,
    'Stars': Stars
}

class Email(StatesGroup):
    input_email = State()

class Price(StatesGroup):
    input_price = State()

@callback_user.callback_query(AutoPay.filter())
async def callback_price(
        call: CallbackQuery,
        callback_data: AutoPay,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    await update_auto_pay(callback_data.work, call.from_user.id)
    if callback_data.work:
        text = _('work_auto_pay_message', lang)
    else:
        text = _('not_work_auto_pay_message', lang)
    await call.message.answer(text=text)
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")

@callback_user.callback_query(ChoosingMonths.filter())
async def my_callback_foo(
        call: CallbackQuery,
        callback_data: ChoosingMonths,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    promo_code = await get_promo_codes_user(call.from_user.id)
    if (
            len(promo_code) != 0
            and callback_data.type_pay == CONFIG.type_payment.get(0)
    ):
        await edit_message(
            call.message,
            caption=_('want_use_promocode', lang),
            reply_markup=await choosing_promo_code(
                lang,
                promo_code,
                callback_data.price,
                callback_data.type_pay,
                key_id=callback_data.key_id,
                month_count=callback_data.month_count
            )
        )
    else:
        await edit_message(
            call.message,
            caption=_('method_replenishment', lang),
            reply_markup=await replenishment(
                config=CONFIG,
                price=callback_data.price,
                lang=lang,
                type_pay=callback_data.type_pay,
                key_id=callback_data.key_id,
                month_count=callback_data.month_count
            )
        )
        text = Text(
            _('admin_message_choosing_month', CONFIG.languages)
            .format(
                username=call.from_user.username,
                user_id=call.from_user.id,
                month_count=callback_data.month_count
            )
        )
        for admin_id in CONFIG.admin_tg_ids:
            await call.message.bot.send_message(
                admin_id,
                **text.as_kwargs()
            )
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")

@callback_user.callback_query(PromoCodeChoosing.filter())
async def callback_price(
        call: CallbackQuery,
        callback_data: PromoCodeChoosing,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    if callback_data.percent != 0:
        price = callback_data.price
        percent = callback_data.percent
        price = price - int(price * (percent * 0.01))
        await promo_user_use(callback_data.id_promo, call.from_user.id)
        text = _('method_replenishment_promo', lang).format(
            percent=percent
        )
    else:
        price = callback_data.price
        text = _('method_replenishment', lang)
    await edit_message(
        call.message,
        caption=text,
        reply_markup=await replenishment(
            config=CONFIG,
            price=price,
            lang=lang,
            type_pay=callback_data.type_pay,
            key_id=callback_data.key_id,
            month_count=callback_data.month_count
        )
    )
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")

async def check_balance(price, telegram_id):
    person = await get_person(telegram_id)
    if person.balance >= price:
        return True
    return False

@callback_user.callback_query(ChoosingPyment.filter())
async def callback_price(
        call: CallbackQuery,
        callback_data: ChoosingPyment,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    await call.message.edit_text(
        _('choosing_amount_menu', lang),
        call.inline_message_id,
        reply_markup=await price_menu(CONFIG, callback_data.payment))
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")

@callback_user.callback_query(ChoosingPrise.filter(F.payment == 'KassaSmart'))
async def callback_payment(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: ChoosingPrise
):
    lang = await get_lang(call.from_user.id, state)
    try:
        await call.message.delete()
    except Exception as e:
        log.info(f'Error delete message: {e}')
    await state.clear()
    await pay_payment(
        'KassaSmart',
        call.message,
        call.from_user,
        callback_data.price,
        callback_data.month_count,
        None,  # data
        callback_data.type_pay,
        callback_data.key_id
    )
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")

@callback_user.message(Email.input_email)
async def input_email(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id, state)
    await message.answer(_('error_email_input', lang))  # Оставляем как заглушку, не должно вызываться

@callback_user.callback_query(ChoosingPrise.filter())
async def callback_payment(
        call: CallbackQuery,
        callback_data: ChoosingPrise,
        state: FSMContext
):
    await state.clear()
    type_pay = callback_data.type_pay
    key_id = callback_data.key_id
    if types_of_payments.get(callback_data.payment):
        await pay_payment(
            callback_data.payment,
            call.message,
            call.from_user,
            callback_data.price,
            callback_data.month_count,
            call.data,
            type_pay,
            key_id
        )
    else:
        raise NameError(callback_data.payment)
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")

async def pay_payment(
        payment, message,
        from_user, price,
        month_count, data,
        type_pay, key_id
):
    if (
            month_count is None
            and (
            type_pay == CONFIG.type_payment.get(0)
            or type_pay == CONFIG.type_payment.get(1)
    )
    ):
        lang = await get_lang(message.from_user.id)
        await message.answer(_('error_month_count', lang))
        return
    payment = types_of_payments[payment](
        config=CONFIG,
        message=message,
        telegram_id=from_user.id,
        price=price,
        month_count=month_count,
        type_pay=type_pay,
        key_id=key_id,
        data=data
    )
    await payment.to_pay()

@callback_user.callback_query(F.data.in_('donate_btn'))
async def renew_subscription(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user.id, state)
    await edit_message(
        call.message,
        caption=_('donate_message', lang).format(fullname=call.from_user.full_name),
        reply_markup=await donate_menu(lang)
    )
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")

@callback_user.callback_query(F.data.in_(btn_text('donate_btn')))
async def renew_subscription(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user.id, state)
    await call.message.answer(
        text=_('donate_message', lang).format(fullname=call.from_user.full_name),
        reply_markup=await donate_menu(lang)
    )
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")

@callback_user.callback_query(F.data == 'back_donate_menu')
async def callback_payment(
        call: CallbackQuery,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    await edit_message(
        call.message,
        caption=_('donate_message', lang).format(fullname=call.from_user.full_name),
        reply_markup=await donate_menu(lang)
    )
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")

@callback_user.callback_query(DonatePrice.filter())
async def callback_payment(
        call: CallbackQuery,
        callback_data: DonatePrice,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    if callback_data.price == 0:
        await edit_message(
            call.message,
            caption=_('donate_input_price_text', lang),
            reply_markup=await back_menu_button(lang)
        )
        await state.set_state(Price.input_price)
        return
    await edit_message(
        call.message,
        caption=_('method_replenishment', lang),
        reply_markup=await replenishment(
            config=CONFIG,
            price=callback_data.price,
            lang=lang,
            type_pay=CONFIG.type_payment.get(2)
        )
    )
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")

@callback_user.message(Price.input_price)
async def input_price(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id, state)
    price = message.text.strip()
    if not price.isdigit():
        await message.answer(_('donate_input_price_text_not_num', lang))
        return
    price = int(price)
    if price < 50 or price > 20000:
        await message.answer(_('donate_input_price_text_limit', lang))
        return
    await state.clear()
    await message.answer(
        text=_('method_replenishment', lang),
        reply_markup=await replenishment(
            config=CONFIG,
            price=price,
            lang=lang,
            type_pay=CONFIG.type_payment.get(2)
        )
    )

@callback_user.callback_query(F.data == 'donate_list')
async def callback_payment(
        call: CallbackQuery,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    all_donate = await get_all_donate()
    list_donate = ''
    for donate in all_donate:
        list_donate += f'{donate.username} - <b>{donate.price} ₽</b>\n'
    await edit_message(
        call.message,
        caption=_('donate_list_users', lang).format(users=list_donate),
        reply_markup=await back_donate_menu(lang)
    )
    try:
        await call.answer()
    except TelegramBadRequest as e:
        log.warning(f"Ignored TelegramBadRequest: {e}")