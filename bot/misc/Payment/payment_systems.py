import logging
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.formatting import Text

from bot.database.methods.get import get_free_servers, get_person, get_key_id, get_name_location_server
from bot.database.methods.insert import add_payment, add_donate, add_key
from bot.database.methods.update import (
    add_referral_balance_person,
    add_time_key,
    update_switch_key,
    server_space_update,
    update_server_key,
)
from bot.handlers.user.install_menu import install_main_menu
from bot.handlers.user.keys_user import post_key_telegram
from bot.keyboards.inline.user_inline import (
    choose_type_vpn,
    pay_and_check,
    user_menu,
)
from bot.misc.VPN.ServerManager import ServerManager
from bot.misc.language import Localization, get_lang
from bot.misc.util import CONFIG
from bot.service.edit_message import edit_message

log = logging.getLogger(__name__)

_ = Localization.text

class PaymentSystems:
    TOKEN: str
    CHECK_PERIOD = 50 * 60  # 50 minutes
    STEP = 5  # Check every 5 seconds
    TIME_DELETE: int = 5 * 60  # Delete button 5 minutes before period ends
    TYPE_PAYMENT: str
    KEY_ID: int
    MESSAGE_ID_PAYMENT: Message = None

    def __init__(
            self,
            message,
            user_id,
            donate,
            key_id,
            price=None,
            month_count=None
    ):
        self.message: Message = message
        self.user_id = user_id
        self.price = price
        self.month_count = month_count
        self.TYPE_PAYMENT = donate
        self.KEY_ID = key_id
        self.ID_PROT = 1  # Fix VLESS
        self.ID_LOC = 0  # Fix first location
        log.info(f'payment system: {self.TYPE_PAYMENT}')

    async def to_pay(self):
        raise NotImplementedError()

    async def pay_button(self, link_pay, delete=True, webapp=False):
        lang_user = await get_lang(self.user_id)
        if delete:
            try:
                await self.message.delete()
            except Exception:
                log.info('error delete message')
        self.MESSAGE_ID_PAYMENT = await self.message.answer(
            text=_('payment_balance_text', lang_user).format(price=self.price),
            reply_markup=await pay_and_check(link_pay, lang_user, webapp)
        )

    async def delete_pay_button(self, name_payment):
        if self.MESSAGE_ID_PAYMENT is not None:
            try:
                await self.message.bot.delete_message(
                    self.user_id,
                    self.MESSAGE_ID_PAYMENT.message_id
                )
                log.info(
                    f'user ID: {self.user_id} '
                    f'delete payment {self.price} RUB '
                    f'Payment - {name_payment}'
                )
            except Exception as e:
                log.error(
                    f'error delete pay button {e} payment {name_payment}'
                )
            finally:
                self.MESSAGE_ID_PAYMENT = None

    async def successful_payment(
            self,
            total_amount,
            name_payment,
            id_payment=None
    ):
        log.info(
            f'user ID: {self.user_id} '
            f'success payment {total_amount} RUB '
            f'Payment - {name_payment} '
            f'Type payment {self.TYPE_PAYMENT}'
        )
        lang_user = await get_lang(self.user_id)

        # Save payment to database
        await add_payment(
            self.user_id,
            total_amount,
            name_payment,
            id_payment=id_payment,
            month_count=self.month_count
        )

        # Determine effective months with bonuses
        if self.month_count == 6:
            effective_months = 7  # 6 months + 1 bonus
            bonus_message = _("bonus_months", lang_user).format(bonus=1)
        elif self.month_count == 12:
            effective_months = 15  # 12 months + 3 bonus
            bonus_message = _("bonus_months", lang_user).format(bonus=3)
        else:
            effective_months = self.month_count
            bonus_message = ""

        # Calculate subscription duration in seconds
        subscription_seconds = effective_months * CONFIG.COUNT_SECOND_MOTH

        # Process different payment types
        if self.TYPE_PAYMENT == CONFIG.type_payment.get(0):  # New key
            person = await get_person(self.user_id)
            try:
                locations = await get_free_servers(person.group, self.ID_PROT)
                if not locations:
                    raise FileNotFoundError("No available servers")
                server = locations[0].vds[0].servers[0]  # Take first available server
            except FileNotFoundError:
                log.error(f"No free servers for user {self.user_id} group {person.group} type_vpn {self.ID_PROT}")
                await self.message.bot.send_message(
                    self.user_id,
                    _("not_server", lang_user)
                )
                return

            # Create key
            key = await add_key(
                telegram_id=person.tgid,
                subscription=subscription_seconds,
                server_id=server.id,
                id_payment=id_payment
            )

            # Send payment success message
            await self.message.answer(
                _('payment_success', lang_user)
                .format(total_month=effective_months, bonus=bonus_message),
                parse_mode="HTML"
            )
            log.debug(f"Sent payment_success message for user {self.user_id}")

            # Initialize variables
            config = None
            server_manager = None
            name_location = "Unknown"

            # Try to generate key configuration
            try:
                # Get key data
                key = await get_key_id(key.id)
                if not key or not key.server_table:
                    raise ValueError("Key or server_table is None")
                log.debug(f"Retrieved key {key.id} for user {self.user_id}")

                # Initialize server manager
                server_manager = ServerManager(key.server_table)
                await server_manager.login()
                log.debug(f"Server manager logged in for user {self.user_id}")

                # Add client to server
                if await server_manager.add_client(self.user_id, key.id) is None:
                    raise Exception('Failed to add client to server')
                log.debug(f"Client added to server for user {self.user_id}")

                # Get location name and key configuration
                name_location = await get_name_location_server(key.server_table.id)
                config = await server_manager.get_key(
                    self.user_id,
                    name_key=name_location,
                    key_id=key.id
                )
                if config is None:
                    raise Exception("Failed to generate config")
                log.debug(f"Generated config for user {self.user_id}: {config}")

                # Update server space
                server_parameters = await server_manager.get_all_user()
                await server_space_update(server.id, len(server_parameters))
                log.debug(f"Updated server space for server {server.id}")

            except Exception as e:
                log.error(f"Failed to generate key config for user {self.user_id}: {e}")
                await self.message.answer(
                    _("server_not_connected", lang_user),
                    parse_mode="HTML"
                )

            # Send loading indicator
            download = await self.message.answer(
                _('download', lang_user)
            )

            # Delete loading indicator
            await download.delete()

            # Send key with installation menu using post_key_telegram
            if config:  # Send key only if config is successfully generated
                try:
                    await post_key_telegram(
                        self.message,
                        key,
                        config,
                        lang_user
                    )
                    log.debug(f"Sent key with installation menu for user {self.user_id}")
                except Exception as e:
                    log.error(f"Failed to send key with menu for user {self.user_id}: {e}")
                    await self.message.answer(
                        _("key_generated_error", lang_user),
                        parse_mode="HTML"
                    )

            # Notify admins
            text = Text(
                _('admin_message_payment_success', CONFIG.languages).format(
                    username=person.username,
                    user_id=self.user_id,
                    month_count=effective_months,
                    price=self.price
                )
            )
            for admin_id in CONFIG.admin_tg_ids:
                await self.message.bot.send_message(
                    admin_id,
                    **text.as_kwargs()
                )

        elif self.TYPE_PAYMENT == CONFIG.type_payment.get(1):  # Extend key
            person = await get_person(self.user_id)
            await add_time_key(
                int(self.KEY_ID),
                subscription_seconds,
                id_payment=id_payment
            )
            await self.message.answer(
                _('payment_success_extend', lang_user)
                .format(total_month=effective_months, bonus=bonus_message),
                parse_mode="HTML"
            )
            text = Text(
                _('admin_message_payment_success', CONFIG.languages).format(
                    username=person.username,
                    user_id=self.user_id,
                    month_count=effective_months,
                    price=self.price
                )
            )
            for admin_id in CONFIG.admin_tg_ids:
                await self.message.bot.send_message(
                    admin_id,
                    **text.as_kwargs()
                )
            await self.message.answer(
                text=_('main_menu', lang_user),
                reply_markup=await user_menu(lang_user, person.tgid),
                parse_mode="HTML"
            )
            return

        elif self.TYPE_PAYMENT == CONFIG.type_payment.get(2):  # Donate
            person = await get_person(self.user_id)
            await add_donate(person.username, self.price)
            await self.message.answer(
                _('donate_successful', lang_user),
                parse_mode="HTML"
            )
            text = Text(
                _('admin_message_payment_success_donate', CONFIG.languages).format(
                    username=person.username,
                    user_id=self.user_id,
                    price=self.price
                )
            )
            for admin_id in CONFIG.admin_tg_ids:
                await self.message.bot.send_message(
                    admin_id,
                    **text.as_kwargs()
                )
            await self.message.answer(
                text=_('main_menu', lang_user),
                reply_markup=await user_menu(lang_user, person.tgid),
                parse_mode="HTML"
            )
            return

        elif self.TYPE_PAYMENT == CONFIG.type_payment.get(3):  # Change location
            person = await get_person(self.user_id)
            await update_switch_key(self.KEY_ID, True)
            await self.message.answer(
                _('payment_success_switch', lang_user),
                parse_mode="HTML"
            )
            await self.message.answer(
                text=_('choosing_connect_type', lang_user),
                reply_markup=await choose_type_vpn(
                    key_id=self.KEY_ID,
                    lang=lang_user,
                    back_data='back_general_menu_btn'
                ),
                parse_mode="HTML"
            )
            text = Text(
                _('admin_message_payment_success_switch', CONFIG.languages).format(
                    username=person.username,
                    user_id=self.user_id,
                    price=self.price
                )
            )
            for admin_id in CONFIG.admin_tg_ids:
                await self.message.bot.send_message(
                    admin_id,
                    **text.as_kwargs()
                )
            return

        else:
            log.error(f'type payment {self.TYPE_PAYMENT} not found')
            await self.message.bot.send_message(
                self.user_id,
                _('error_send_admin', lang_user),
                parse_mode="HTML"
            )
            return

        # Handle referral balance
        person = await get_person(self.user_id)
        if person.referral_user_tgid is not None:
            referral_user = person.referral_user_tgid
            referral_balance = int(total_amount * (CONFIG.referral_percent * 0.01))
            await add_referral_balance_person(referral_balance, referral_user)
            await self.message.bot.send_message(
                referral_user,
                _('reff_add_balance', await get_lang(referral_user)).format(
                    referral_balance=referral_balance
                ),
                parse_mode="HTML"
            )