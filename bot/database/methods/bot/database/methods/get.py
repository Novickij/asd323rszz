from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import and_, select, func, desc
from datetime import datetime

from bot.database.main import engine
from bot.database.models.main import (
    Persons,
    Servers,
    Payments,
    StaticPersons,
    PromoCode,
    WithdrawalRequests,
    Groups, Donate, Keys, message_button_association, Location, Vds
)
from bot.misc.util import CONFIG


def person_cache_key(telegram_id):
    return f"person:{telegram_id}"


def person_id_cache_key(list_input):
    return f"person:{list_input}"


async def get_person(telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Persons).options(
            joinedload(Persons.keys)
        ).filter(Persons.tgid == telegram_id)
        result = await db.execute(statement)
        person = result.unique().scalar_one_or_none()
        return person


async def get_person_id(list_input):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Persons).options(
            joinedload(Persons.keys)
        ).filter(Persons.tgid.in_(list_input))
        result = await db.execute(statement)
        persons = result.unique().scalars().all()
        return persons


async def get_keys_id(list_input):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).options(
            joinedload(Keys.person)
        ).filter(Keys.id.in_(list_input))
        result = await db.execute(statement)
        keys = result.unique().scalars().all()
        return keys


async def _get_person(db, telegram_id):
    statement = select(Persons).options(
        joinedload(Persons.keys)
    ).filter(Persons.tgid == telegram_id)
    result = await db.execute(statement)
    person = result.unique().scalar_one_or_none()
    return person


async def _get_server(db, id_server):
    statement = select(Servers).filter(Servers.id == id_server)
    result = await db.execute(statement)
    server = result.scalar_one_or_none()
    return server


async def get_all_donate():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Donate)
        result = await db.execute(statement)
        persons = result.scalars().all()
        return persons


async def get_all_user():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Persons).options(
            joinedload(Persons.keys)
        )
        result = await db.execute(statement)
        persons = result.unique().scalars().all()
        return persons


async def get_all_subscription():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Persons).options(
            selectinload(Persons.keys).options(
                selectinload(Keys.server_table).options(
                    selectinload(Servers.vds_table).selectinload(Vds.location_table)
                )
            )
        ).filter(Persons.keys.any())
        result = await db.execute(statement)
        persons = result.unique().scalars().all()
        return persons


async def get_no_subscription():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Persons).options(
            joinedload(Persons.keys)
        ).filter(~Persons.keys.any())
        result = await db.execute(statement)
        persons = result.unique().scalars().all()
        return persons


async def get_payments():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Payments).options(
            joinedload(Payments.payment_id)
        )
        result = await db.execute(statement)
        payments = result.scalars().all()

        for payment in payments:
            payment.user = payment.payment_id.username

        return payments


async def get_payment(id_payment):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Payments).options(
            joinedload(Payments.payment_id)
        ).filter(Payments.id_payment == id_payment).order_by(
            desc(Payments.data)
        )
        result = await db.execute(statement)
        payments = result.scalars().first()
        return payments


async def get_all_server():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Servers)
        result = await db.execute(statement)
        servers = result.scalars().all()
        return servers


async def get_server(id_server):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        return await _get_server(db, id_server)


async def get_server_id(id_server):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Servers).options(
            joinedload(Servers.vds_table)
            .joinedload(Vds.location_table)
        ).filter(Servers.id == id_server)
        result = await db.execute(statement)
        server = result.scalar_one_or_none()
        return server


async def get_type_vpn():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        result = await db.execute(
            select(Servers.type_vpn).join(Servers.vds_table).join(
                Vds.location_table)
            .filter(
                and_(
                    Location.work == True,  # noqa
                    Vds.work == True,  # noqa
                    Servers.work == True,  # noqa
                    Servers.free_server == False  # noqa
                )
            ).distinct()
        )
        unique_type_vpn = result.scalars().all()
        return unique_type_vpn


async def get_free_server_id(id_location, type_vpn):
    async with (AsyncSession(autoflush=False, bind=engine()) as db):
        statement = select(Servers).join(Servers.vds_table).join(
            Vds.location_table).filter(
            Location.id == id_location,
            Servers.type_vpn == type_vpn
        ).options(
            selectinload(Servers.vds_table).selectinload(Vds.location_table)
        ).order_by(Servers.actual_space)
        result = await db.execute(statement)
        server = result.unique().scalars().all()
        if len(server) != 0:
            return server[0]
        else:
            return None


async def get_name_location_server(server_id: int):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        result = await db.execute(
            select(Servers)
            .filter(Servers.id == server_id)
            .options(selectinload(Servers.vds_table).selectinload(Vds.location_table))
        )
        server = result.scalars().first()
        return server.vds_table.location_table.name if server and server.vds_table and server.vds_table.location_table else "Unknown"


async def get_free_servers(group_name, type_vpn):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        base_query = select(Location).join(Location.vds).join(
            Vds.servers).filter(
            and_(
                Location.work == True,  # noqa
                Vds.work == True,  # noqa
                Servers.work == True,  # noqa
                Servers.actual_space < Vds.max_space,
                Location.group == group_name,
                Servers.type_vpn == type_vpn,
                Servers.free_server == False
            )
        ).options(
            selectinload(Location.vds).selectinload(Vds.servers)
        ).order_by(Servers.actual_space)
        result = await db.execute(base_query)
        locations = result.unique().scalars().all()
        if not locations:
            raise FileNotFoundError('Server not found')
        return locations


async def get_free_vpn_server():
    async with (AsyncSession(autoflush=False, bind=engine()) as db):
        statement = select(Servers).join(Servers.vds_table).join(
            Vds.location_table).filter(
            Location.work == True,  # noqa
            Vds.work == True,  # noqa
            Servers.work == True,  # noqa
            Servers.free_server == True,  # noqa
            Servers.actual_space < Vds.max_space,
        ).options(
            selectinload(Servers.vds_table).selectinload(Vds.location_table)
        ).order_by(Servers.actual_space)
        result = await db.execute(statement)
        server = result.unique().scalars().first()
        return server


async def get_all_static_user():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(StaticPersons).options(
            joinedload(StaticPersons.server_table)
        )
        result = await db.execute(statement)
        all_static_user = result.scalars().all()
        return all_static_user


async def get_all_promo_code():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(PromoCode).options(
            joinedload(PromoCode.person)
        )
        result = await db.execute(statement)
        promo_code = result.unique().scalars().all()
        return promo_code


async def get_promo_codes_user(telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(PromoCode).join(
            message_button_association,
            PromoCode.id == message_button_association.c.promocode_id
        ).join(
            Persons, Persons.id == message_button_association.c.users_id
        ).filter(
            Persons.tgid == telegram_id,
            message_button_association.c.use == False  # noqa
        )
        result = await db.execute(statement)
        promo_codes = result.scalars().all()
        return promo_codes


async def get_promo_code(text_promo):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        promo_code_query = select(PromoCode).where(
            PromoCode.text == text_promo)
        promo_code_result = await db.execute(promo_code_query)
        promo_code = promo_code_result.scalar_one_or_none()

        if not promo_code:
            return None

        usage_count_query = (
            select(func.count(message_button_association.c.users_id))
            .where(message_button_association.c.promocode_id == promo_code.id)
        )
        usage_count_result = await db.execute(usage_count_query)
        usage_count = usage_count_result.scalar()

        if usage_count < promo_code.count_use:
            return promo_code
        else:
            return None


async def get_count_referral_user(telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(func.count(Persons.id)).filter(
            Persons.referral_user_tgid == telegram_id
        )
        result = await db.execute(statement)
        return result.scalar()


async def get_referral_balance(telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Persons).filter(Persons.tgid == telegram_id)
        result = await db.execute(statement)
        person = result.scalar_one_or_none()
        return person.referral_balance


async def get_all_application_referral():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(WithdrawalRequests)
        result = await db.execute(statement)
        return result.scalars().all()


async def get_application_referral_check_false():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(WithdrawalRequests).filter(
            WithdrawalRequests.check_payment == False  # noqa
        )
        result = await db.execute(statement)
        return result.scalars().all()


async def get_person_lang(telegram_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Persons).filter(Persons.tgid == telegram_id)
        result = await db.execute(statement)
        person = result.scalar_one_or_none()
        if person is None:
            return CONFIG.languages
        return person.lang


async def get_all_groups():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(
            Groups, func.count(Groups.users), func.count(Groups.locations)). \
            outerjoin(Groups.users). \
            outerjoin(Groups.locations). \
            group_by(Groups.id). \
            order_by(Groups.id)
        result = await db.execute(statement)
        rows = result.all()
        groups_with_counts = []
        for row in rows:
            group = row[0]
            count_user = row[1]
            count_server = row[2]
            groups_with_counts.append(
                {"group": group, "count_user": count_user,
                 "count_server": count_server})
        return groups_with_counts


async def get_group(group_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Groups).filter(Groups.id == group_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()


async def get_group_name(group_name):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Groups).filter(Groups.name == group_name)
        result = await db.execute(statement)
        return result.scalar_one_or_none()


async def get_users_group(group_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Groups).filter(Groups.id == group_id)
        result = await db.execute(statement)
        group = result.scalar_one_or_none()
        statement = select(Persons).options(
            joinedload(Persons.keys)
        ).filter(Persons.group == group.name)  # noqa
        result = await db.execute(statement)
        return result.unique().scalars().all()


async def get_count_groups():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(func.count(Groups.id))
        result = await db.execute(statement)
        count = result.scalar_one()
        return count


async def get_key_user(telegram_id, free_key=None):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).options(
            joinedload(Keys.server_table)
            .joinedload(Servers.vds_table)
            .joinedload(Vds.location_table)
        ).filter(
            Keys.user_tgid == telegram_id
        )
        if free_key is not None:
            statement = statement.filter(Keys.free_key == free_key)
        result = await db.execute(statement)
        if free_key:
            return result.unique().scalar_one_or_none()
        return result.unique().scalars().all()


async def get_key_id(key_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).options(
            joinedload(Keys.server_table)
        ).filter(
            Keys.id == key_id
        )
        result = await db.execute(statement)
        key = result.unique().scalar_one_or_none()
        return key


async def get_key_id_server(telegram_id, server_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).options(
            joinedload(Keys.server_table)
        ).filter(
            Keys.server == server_id,
            Keys.user_tgid == telegram_id
        )
        result = await db.execute(statement)
        key = result.unique().scalar_one_or_none()
        return key


async def get_all_locations():
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Location).options(
            joinedload(Location.vds)
        )
        result = await db.execute(statement)
        locations = result.unique().scalars().all()
        return locations


async def get_location_id(id_location):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Location).filter(Location.id == id_location)
        result = await db.execute(statement)
        location = result.scalar_one_or_none()
        return location


async def get_vds_id(id_vds):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Vds).options(
            joinedload(Vds.servers)
        ).filter(Vds.id == id_vds)
        result = await db.execute(statement)
        location = result.unique().scalar_one_or_none()
        return location


async def get_vds_location(id_location):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Vds).options(
            joinedload(Vds.servers)
        ).filter(Vds.location == id_location)
        result = await db.execute(statement)
        locations = result.unique().scalars().all()
        return locations


async def get_active_keys_count(telegram_id: int, session: AsyncSession) -> int:
    current_time = int(datetime.utcnow().timestamp())
    query = select(Keys).where(
        Keys.user_tgid == telegram_id,
        Keys.subscription > current_time
    )
    result = await session.execute(query)
    keys = result.scalars().all()
    return len(keys)