from functools import wraps

from dogpile.cache import make_region
from dogpile.cache.api import NO_VALUE
from sqlalchemy.ext.asyncio import create_async_engine

from bot.misc.util import CONFIG

if CONFIG.debug:
    ENGINE = "sqlite+aiosqlite:///bot/database/DatabaseVPN.db"
else:
    ENGINE = (
        f'postgresql+asyncpg://'
        f'{CONFIG.postgres_user}:'
        f'{CONFIG.postgres_password}'
        f'@postgres_db_container/{CONFIG.postgres_db}'
    )

cache_region = make_region().configure(
    'dogpile.cache.memory',  # Можно выбрать другой backend
    expiration_time=30     # Время жизни кэша в секундах
)


def async_cache_decorator(cache_key_func):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = cache_key_func(*args, **kwargs)
            cached_value = cache_region.get(cache_key)
            if cached_value is not NO_VALUE:
                print('input has')
                return cached_value
            result = await func(*args, **kwargs)
            cache_region.set(cache_key, result)
            return result
        return wrapper
    return decorator


def clear_cache_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        cache_region.invalidate()
        return await func(*args, **kwargs)

    return wrapper


def engine():
    return create_async_engine(ENGINE)
