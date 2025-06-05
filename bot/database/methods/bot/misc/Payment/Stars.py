import logging

from aiogram import F, Router
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery

from bot.keyboards.inline.user_inline import pay_stars
from bot.misc.Payment.payment_systems import PaymentSystems
from bot.misc.language import get_lang, Localization
from bot.misc.util import CONFIG

stars_router = Router()
log = logging.getLogger(__name__)

_ = Localization.text


class Stars(PaymentSystems):

    def __init__(
            self, config,
            message, user_id,
            price, month_count,
            type_pay, key_id,
            id_prot, id_loc,
            data=None
    ):
        super().__init__(
            message, user_id,
            type_pay, key_id,
            id_prot, id_loc,
            price, month_count
        )
        self.TOKEN = config.token_stars

    async def to_pay(self):
        await self.message.delete()
        lang_user = await get_lang(self.user_id)
        amount = self.price // 2
        title = _('description_payment', lang_user)
        description = (
            _('payment_balance_text2', lang_user).format(price=self.price)
        )
        prices = [LabeledPrice(label="XTR", amount=amount)]
        await self.message.answer_invoice(
            title=title,
            description=description,
            prices=prices,
            provider_token=self.TOKEN,
            payload=
            f'{self.price}'
            f':{self.month_count}'
            f':{self.TYPE_PAYMENT}'
            f':{self.KEY_ID}'
            f':{self.ID_PROT}'
            f':{self.ID_LOC}',
            currency="XTR",
            reply_markup=await pay_stars(lang_user)
        )
        log.info(
            f'Create payment Stars '
            f'User: ID: {self.user_id}'
        )
        return self.price

    def __str__(self):
        return 'Платежная система Telegram Stars'


@stars_router.pre_checkout_query()
async def on_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@stars_router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    data = message.successful_payment.invoice_payload.split(':')
    price = int(data[0])
    donate = CONFIG.type_payment.get(2) == data[2]
    if not donate:
        month_count = int(data[1])
    else:
        month_count = 1
    id_prot = int(data[4])
    id_loc = int(data[5])
    payment_system = PaymentSystem(
        message,
        message.from_user.id,
        data[2],
        data[3],
        price=price,
        month_count=month_count,
        id_prot=id_prot,
        id_loc=id_loc,
    )
    try:
        await payment_system.successful_payment(price, 'Telegram Stars')
    except BaseException as e:
        log.error(e, 'The payment period has expired')
    finally:
        log.info('exit check payment Stars')

