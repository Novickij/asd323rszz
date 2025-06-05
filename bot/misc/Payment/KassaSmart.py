import logging
import uuid
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from bot.misc.Payment.payment_systems import PaymentSystems
from yookassa import Configuration, Payment
from yookassa.domain.exceptions.bad_request_error import BadRequestError
from bot.misc.language import Localization

log = logging.getLogger(__name__)

_ = Localization.text

class KassaSmart(PaymentSystems):
    CHECK_PERIOD = 50 * 60  # 50 минут
    STEP = 5  # Проверка каждые 5 секунд
    TIME_DELETE = 5 * 60  # Удаление кнопки за 5 минут до конца периода

    def __init__(
            self,
            config,
            message: Message,
            telegram_id: int,
            price: int,
            month_count: int,
            type_pay: str,
            key_id: int,
            id_prot: int,
            id_loc: int,
            data=None
    ):
        super().__init__(
            message=message,
            user_id=telegram_id,
            donate=type_pay,
            key_id=key_id,
            price=price,
            month_count=month_count
        )
        self.config = config
        self.ID_PROT = id_prot
        self.ID_LOC = id_loc
        self.data = data
        self.telegram_id = telegram_id
        self.price = price
        self.month_count = month_count
        self.type_pay = type_pay
        self.key_id = key_id
        self.payment_id = None

    async def to_pay(self):
        log.info(f"YooKassa config: shop_id={self.config.yookassa_shop_id}, secret_key={self.config.yookassa_secret_key[:4]}****")
        Configuration.account_id = self.config.yookassa_shop_id
        Configuration.secret_key = self.config.yookassa_secret_key

        payment_params = {
            "amount": {
                "value": f"{self.price}.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": self.config.yookassa_return_url
            },
            "capture": True,
            "description": f"Оплата подписки на {self.month_count} мес. для пользователя {self.telegram_id}",
            "metadata": {
                "telegram_id": self.telegram_id,
                "month_count": self.month_count,
                "type_pay": self.type_pay,
                "key_id": self.key_id,
                "id_prot": self.ID_PROT,
                "id_loc": self.ID_LOC
            },
            "receipt": {
                "customer": {
                    "email": f"user_{self.telegram_id}@example.com"
                },
                "items": [
                    {
                        "description": f"Подписка на {self.month_count} мес.",
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{self.price}.00",
                            "currency": "RUB"
                        },
                        "vat_code": 1,  # Без НДС
                        "payment_mode": "full_payment",
                        "payment_subject": "service"
                    }
                ]
            }
        }
        log.debug(f"Payment.create params: {payment_params}")

        try:
            payment = await Payment.create(payment_params, uuid.uuid4())
            self.payment_id = payment.id
            log.info(
                f"Created payment link YooKassaSmart for user (ID: {self.telegram_id}), "
                f"payment_id={self.payment_id}"
            )

            confirmation_url = payment.confirmation.confirmation_url
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_('user_pay_sub_btn', 'ru'), url=confirmation_url)],
                [InlineKeyboardButton(text=_('back_general_menu_btn', 'ru'), callback_data='back_general_menu_btn')]
            ])
            log.debug(f"Sending payment message for user {self.telegram_id}, keyboard={keyboard.inline_keyboard}")
            await self.message.bot.send_message(
                chat_id=self.telegram_id,
                text=f"Перейдите по ссылке для оплаты:\n{confirmation_url}",
                reply_markup=keyboard
            )
            log.debug(f"Sent payment link with keyboard for user {self.telegram_id}")

            try:
                await self.check_payment()
            except Exception as e:
                log.error(f"Error checking payment for user {self.telegram_id}: {e}")
            finally:
                await self.delete_pay_button('YooKassaSmart')
                log.info(f"Exit check payment YooKassaSmart for user {self.telegram_id}")

        except BadRequestError as e:
            log.error(f"YooKassa error for user {self.telegram_id}: {e}")
            await self.message.bot.send_message(
                chat_id=self.telegram_id,
                text="Ошибка при создании платежа. Пожалуйста, попробуйте позже или обратитесь в поддержку.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=_('back_general_menu_btn', 'ru'), callback_data='back_general_menu_btn')]
                ])
            )
        except Exception as e:
            log.error(f"Unexpected error in YooKassa payment for user {self.telegram_id}: {e}")
            await self.message.bot.send_message(
                chat_id=self.telegram_id,
                text="Произошла ошибка. Пожалуйста, попробуйте позже или обратитесь в поддержку.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=_('back_general_menu_btn', 'ru'), callback_data='back_general_menu_btn')]
                ])
            )

    async def check_payment(self):
        Configuration.account_id = self.config.yookassa_shop_id
        Configuration.secret_key = self.config.yookassa_secret_key
        tic = 0
        while tic < self.CHECK_PERIOD:
            res = await Payment.find_one(self.payment_id)
            if res.status == 'succeeded':
                payment_data = {
                    "id": res.id,
                    "status": res.status,
                    "amount": {"value": str(res.amount.value), "currency": res.amount.currency},
                    "metadata": {
                        "telegram_id": self.telegram_id,
                        "month_count": self.month_count,
                        "type_pay": self.type_pay,
                        "key_id": self.key_id,
                        "id_prot": self.ID_PROT,
                        "id_loc": self.ID_LOC
                    }
                }
                log.info(f"Payment succeeded for user {self.telegram_id}, payment_id={self.payment_id}")
                await super().successful_payment(
                    total_amount=float(res.amount.value),
                    name_payment='YooKassaSmart',
                    id_payment=res.id
                )
                return
            tic += self.STEP
            await asyncio.sleep(self.STEP)
            if self.CHECK_PERIOD - tic <= self.TIME_DELETE:
                await self.delete_pay_button('YooKassaSmart')
        log.warning(f"Payment check timeout for user {self.telegram_id}, payment_id={self.payment_id}")