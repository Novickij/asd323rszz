import time
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from bot.database.main import engine
from bot.database.methods.get import _get_person, _get_server
from bot.database.models.main import Persons, WithdrawalRequests, Keys, \
    PromoCode, message_button_association, Location, Vds
from bot.misc.util import CONFIG

log = logging.getLogger(__name__)

async def add_balance_person(tgid, deposit):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.balance += int(deposit)
            await db.commit()
            return True
        return False

async def reduce_balance_person(deposit, tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.balance -= int(deposit)
            await db.commit()
            return True
        return False

async def reduce_referral_balance_person(amount, tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.referral_balance -= int(amount)
            if person.referral_balance < 0:
                return False
            await db.commit()
            return True
        return False

async def update_balance_person(amount, tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.balance = int(amount)
            if person.balance < 0:
                return False
            await db.commit()
            return True
        return False

async def add_referral_balance_person(amount, tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.referral_balance += int(amount)
            await db.commit()
            return True
        return False

async def add_time_person(tgid, count_time):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            now_time = int(time.time()) + count_time
            if person.banned:
                person.subscription = int(now_time)
                person.banned = False
            else:
                person.subscription += count_time
            await db.commit()
            return True
        return False

async def person_trial_period(telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, telegram_id)
        if person is not None:
            if not person.trial_period:
                person.banned = False
                person.trial_period = True
                log.debug(f"Updated trial_period for user {telegram_id} to True")
                await db.commit()
                log.debug(f"Committed trial_period update for user {telegram_id}")
                return True
            else:
                log.debug(f"User {telegram_id} already has trial_period=True")
                return False
        log.error(f"Failed to update trial_period: user {telegram_id} not found")
        return False

async def person_special_off(telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, telegram_id)
        if person is not None:
            person.special_offer = False
            await db.commit()
            return True
        return False

async def person_banned_true(tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.banned = True
            person.notion_oneday = False
            person.subscription = int(time.time())
            await db.commit()
            return True
        return False

async def key_one_day_true(key_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).filter(Keys.id == key_id)
        result = await db.execute(statement)
        key = result.scalar_one_or_none()
        if key is not None:
            key.notion_oneday = True
            await db.commit()
            return True
        return False

async def person_delete_server(telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, telegram_id)
        if person and person.keys:
            for key in person.keys:
                await db.delete(key)
            await db.commit()
            return True
        else:
            return False

async def update_server_key(key_id, server_id=None):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).filter(Keys.id == key_id)
        result = await db.execute(statement)
        key = result.unique().scalar_one_or_none()
        if key is not None:
            key.server = server_id
            await db.commit()
            return True
        return False

async def server_work_update(id_server, work):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        server = await _get_server(db, id_server)
        if server is not None:
            server.work = work
            await db.commit()
            return True
        return False

async def location_switch_update(id_location, pay_switch):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Location).filter(Location.id == id_location)
        result = await db.execute(statement)
        location = result.unique().scalar_one_or_none()
        if location is not None:
            location.pay_switch = pay_switch
            await db.commit()
            return True
        return False

async def server_space_update(id_server, new_space):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        server = await _get_server(db, id_server)
        if server is not None:
            server.actual_space = new_space
            await db.commit()
            return True
        return False

async def add_pomo_code_person(tgid, promo_code: PromoCode):
    async with (AsyncSession(autoflush=False, bind=engine()) as db):
        async with db.begin():
            statement = select(Persons).options(
                joinedload(Persons.promocode)).filter(Persons.tgid == tgid)
            result = await db.execute(statement)
            person = result.unique().scalar_one_or_none()
            if person is not None:
                person.promocode.append(promo_code)
                await db.commit()
                return True
            return False

async def succes_aplication(id_application):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        application = await db.execute(
            select(WithdrawalRequests)
            .filter(WithdrawalRequests.id == id_application)
        )
        application_instance = application.scalar_one_or_none()
        if application_instance is not None:
            application_instance.check_payment = True
            await db.commit()
            return True
        return False

async def update_delete_users_server(server):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).filter(Keys.server == server.id)
        result = await db.execute(statement)
        keys = result.scalars().all()
        if keys is not None:
            for key in keys:
                key.server = None
            await db.commit()
            return True
        else:
            return False

async def update_key_users_server(telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).filter(Keys.user_tgid == telegram_id)
        result = await db.execute(statement)
        keys = result.scalars().all()
        if keys is not None:
            for key in keys:
                key.server = None
            await db.commit()
            return True
        else:
            return False

async def add_time_key(key_id, time_sub, id_payment=None):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).filter(Keys.id == key_id)
        result = await db.execute(statement)
        key = result.scalar_one_or_none()
        if key is not None:
            key.subscription += time_sub
            key.id_payment = id_payment
            if not key.notion_oneday:
                key.notion_oneday = False
            if key.trial_period:
                key.trial_period = False
            if key.free_key:
                key.free_key = False
            await db.commit()
            return True
        else:
            return False

async def new_time_key(key_id, time_sub):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).filter(Keys.id == key_id)
        result = await db.execute(statement)
        key = result.scalar_one_or_none()
        if key is not None:
            key.subscription = int(time.time()) + time_sub
            if not key.notion_oneday:
                key.notion_oneday = False
            if key.trial_period:
                key.trial_period = False
            if key.free_key:
                key.free_key = False
            await db.commit()
            return True
        else:
            return False

async def update_switch_key(key_id, action):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).filter(Keys.id == key_id)
        result = await db.execute(statement)
        key = result.scalar_one_or_none()
        if key is not None:
            if action:
                key.switch_location += 1
            else:
                if key.switch_location == 0:
                    return
                key.switch_location -= 1
            await db.commit()
            return True
        else:
            return False

async def update_switch_key_admin(key_id, count_switch):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).filter(Keys.id == key_id)
        result = await db.execute(statement)
        key = result.scalar_one_or_none()
        if key is not None:
            key.switch_location = count_switch
            await db.commit()
            return True
        else:
            return False

async def update_lang(lang, tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.lang = lang
            await db.commit()
            return True
        return False

async def update_auto_pay(new_auto_pay, telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, telegram_id)
        if person is not None:
            person.auto_pay = new_auto_pay
            await db.commit()
            return True
        return False

async def persons_add_group(list_input, name_group=None):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Persons).filter(Persons.tgid.in_(list_input))
        result = await db.execute(statement)
        persons = result.scalars().all()
        if persons is not None:
            for person in persons:
                person.group = name_group
            await db.commit()
            return len(persons)
        return 0

async def promo_user_use(promo_id, telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        promo_statement = select(PromoCode).filter(PromoCode.id == promo_id)
        promo_result = await db.execute(promo_statement)
        promo = promo_result.scalar_one_or_none()

        if promo is not None:
            user_statement = select(Persons).options(
                joinedload(Persons.promocode)
            ).filter(
                Persons.tgid == telegram_id
            )
            user_result = await db.execute(user_statement)
            user = user_result.unique().scalar_one_or_none()

            if user is not None:
                update_statement = update(message_button_association).where(
                    message_button_association.c.promocode_id == promo_id,
                    message_button_association.c.users_id == user.id
                ).values(use=True)
                await db.execute(update_statement)
                await db.commit()
                return True
        return False

async def block_state_person(telegram_id, block_state):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, telegram_id)
        if person is not None:
            person.blocked = block_state
            await db.commit()
            return True
        return False

async def new_name_location(location_id, new_name):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Location).filter(Location.id == location_id)
        result = await db.execute(statement)
        location = result.unique().scalar_one_or_none()
        location.name = new_name
        await db.commit()

async def edit_work_location(location_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Location).filter(Location.id == location_id)
        result = await db.execute(statement)
        location = result.unique().scalar_one_or_none()
        location.work = not location.work
        work = location.work
        await db.commit()
        return work

async def edit_work_vds(vds_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Vds).filter(Vds.id == vds_id)
        result = await db.execute(statement)
        vds = result.unique().scalar_one_or_none()
        vds.work = not vds.work
        work = vds.work
        await db.commit()
        return work

async def new_name_vds(vds_id, new_name):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Vds).filter(Vds.id == vds_id)
        result = await db.execute(statement)
        vds = result.unique().scalar_one_or_none()
        vds.name = new_name
        await db.commit()

async def new_ip_vds(vds_id, new_ip):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Vds).filter(Vds.id == vds_id)
        result = await db.execute(statement)
        vds = result.unique().scalar_one_or_none()
        vds.ip = new_ip
        await db.commit()

async def new_password_vds(vds_id, new_password):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Vds).filter(Vds.id == vds_id)
        result = await db.execute(statement)
        vds = result.unique().scalar_one_or_none()
        vds.vds_password = new_password
        await db.commit()

async def new_limit_vds(vds_id, new_limit):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Vds).filter(Vds.id == vds_id)
        result = await db.execute(statement)
        vds = result.unique().scalar_one_or_none()
        vds.max_space = new_limit
        await db.commit()