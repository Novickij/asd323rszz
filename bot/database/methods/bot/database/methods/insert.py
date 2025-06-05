import datetime
import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.main import engine
from bot.database.methods.get import _get_person
from bot.database.models.main import (
    Persons,
    Payments,
    StaticPersons,
    PromoCode,
    WithdrawalRequests, Groups, Keys, Donate
)
from bot.misc.util import CONFIG

log = logging.getLogger(__name__)

async def add_new_person(from_user, username, ref_user):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        tom = Persons(
            tgid=from_user.id,
            username=username,
            fullname=from_user.full_name,
            lang_tg=from_user.language_code or None,
            referral_user_tgid=ref_user or None,
            banned=False
        )
        db.add(tom)
        await db.commit()
        log.debug(f"Added new person with tgid={from_user.id}, banned=False")
        return tom


async def add_payment(
        telegram_id, deposit,
        payment_system, id_payment=None,
        month_count=None
):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, telegram_id)
        if person is not None:
            payment = Payments(
                amount=deposit,
                data=datetime.datetime.now(),
                payment_system=payment_system,
                id_payment=id_payment,
                month_count=month_count
            )
            payment.user = person.id
            db.add(payment)
            await db.commit()
        log.info(
            f'Add DB payment '
            f'amount:{deposit} '
            f'payment_system:{payment_system}'
            f'telegram_id:{telegram_id}'
            f'month_count:{month_count}'
            f'id_payment:{id_payment}'
        )


async def add_donate(username, price):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        donate = Donate(
            username=username,
            price=price
        )
        db.add(donate)
        await db.commit()


async def add_key(
        telegram_id,
        subscription,
        id_payment=None,
        free_key=False,
        trial_period=False,
        server_id=None
):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        key = Keys(
            user_tgid=telegram_id,
            subscription=int(time.time()) + subscription,
            switch_location=CONFIG.free_switch_location,
            id_payment=id_payment,
            free_key=free_key,
            trial_period=trial_period,
            server=server_id
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)
        log.info(
            f'Add DB key '
            f'telegram_id:{telegram_id} '
            f'subscription:{subscription} '
            f'id_payment:{id_payment} '
            f'free_key:{free_key} '
            f'trial_period:{trial_period}'
        )
        return key


async def add_server(server):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        db.add(server)
        await db.commit()


async def add_location(location):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        db.add(location)
        await db.commit()


async def add_vds(vds):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        db.add(vds)
        await db.commit()


async def add_static_user(name, server):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        static_user = StaticPersons(
            name=name,
            server=server
        )
        db.add(static_user)
        await db.commit()


async def add_promo(text_promo, percent, count_use):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        promo_code = PromoCode(
            text=text_promo,
            percent=percent,
            count_use=count_use
        )
        db.add(promo_code)
        await db.commit()


async def add_withdrawal(tgid, amount, payment_info, communication):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        withdrawal = WithdrawalRequests(
            amount=amount,
            payment_info=payment_info,
            user_tgid=tgid,
            communication=communication
        )
        db.add(withdrawal)
        await db.commit()


async def add_group(group_name):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        group = Groups(
            name=group_name
        )
        db.add(group)
        await db.commit()