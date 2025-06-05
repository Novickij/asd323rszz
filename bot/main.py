import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.strategy import FSMStrategy
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers.user.main import user_router, registered_router
from bot.handlers.admin.main import admin_router
from bot.database.models.main import create_all_table
from bot.database.importBD.import_BD import import_all
from bot.misc.commands import set_commands
from bot.misc.loop import loop
from bot.misc.util import CONFIG

async def start_bot():
    dp = Dispatcher(
        storage=MemoryStorage(),
        fsm_strategy=FSMStrategy.USER_IN_CHAT
    )
    # todo Register all the routers from handlers package
    dp.include_routers(
        registered_router,
        user_router,
        admin_router
    )

    await create_all_table()
    if CONFIG.import_bd:
        await import_all()
        logging.info('Import BD successfully -- OK')
        return
    scheduler = AsyncIOScheduler()
    bot = Bot(token=CONFIG.tg_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await set_commands(bot)
    scheduler.add_job(loop, "interval", seconds=15, args=(bot,))
    logging.getLogger('apscheduler.executors.default').setLevel(
        logging.WARNING)
    scheduler.start()
    await dp.start_polling(bot)