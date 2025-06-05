import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.main import engine
from bot.database.models.main import Servers, StaticPersons, PromoCode, Groups, \
    Keys, Location, Vds

log = logging.getLogger(__name__)

async def delete_server(id_server):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Servers).filter(Servers.id == id_server)
        result = await db.execute(statement)
        server = result.scalar_one_or_none()

        if server is not None:
            await db.delete(server)
            await db.commit()
        else:
            raise ModuleNotFoundError

async def delete_static_user_bd(name):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(StaticPersons).filter(StaticPersons.name == name)
        result = await db.execute(statement)
        static_user = result.scalar_one_or_none()

        if static_user is not None:
            await db.delete(static_user)
            await db.commit()
        else:
            raise ModuleNotFoundError

async def delete_promo_code(id_promo):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(PromoCode).filter(PromoCode.id == id_promo)
        result = await db.execute(statement)
        promo_code = result.scalar_one_or_none()

        if promo_code is not None:
            await db.delete(promo_code)
            await db.commit()
        else:
            raise ModuleNotFoundError

async def delete_group(group_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Groups).filter(Groups.id == group_id)
        result = await db.execute(statement)
        group = result.scalar_one_or_none()

        if group is not None:
            await db.delete(group)
            await db.commit()
        else:
            raise ModuleNotFoundError

async def delete_key_in_user(key_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Keys).filter(Keys.id == key_id)
        result = await db.execute(statement)
        key = result.scalar_one_or_none()

        if key is not None:
            log.info(f'Deleting key {key_id} for user {key.user_tgid}. Details: subscription={key.subscription}, trial_period={key.trial_period}, free_key={key.free_key}, server={key.server}')
            # await db.delete(key)
            # await db.commit()
            log.info(f'Successfully deleted key {key_id} for user {key.user_tgid} (delete commented out)')
        else:
            raise ModuleNotFoundError

async def delete_location(location_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Location).filter(Location.id == location_id)
        result = await db.execute(statement)
        location = result.scalar_one_or_none()

        if location is not None:
            await db.delete(location)
            await db.commit()
        else:
            raise ModuleNotFoundError

async def delete_vds(vds_id):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Vds).filter(Vds.id == vds_id)
        result = await db.execute(statement)
        vds = result.scalar_one_or_none()

        if vds is not None:
            await db.delete(vds)
            await db.commit()
        else:
            raise ModuleNotFoundError