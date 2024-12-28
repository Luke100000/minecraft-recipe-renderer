from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aioredis
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

from minecraft_recipe_renderer.api import setup


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = aioredis.from_url("redis://localhost", decode_responses=False)
    FastAPICache.init(RedisBackend(redis), prefix="minecraft-recipe-renderer")
    yield


app = FastAPI(lifespan=lifespan)

setup(app)
