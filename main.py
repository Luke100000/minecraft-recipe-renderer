from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio.client import Redis

from minecraft_recipe_renderer.api import setup


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    FastAPICache.init(RedisBackend(Redis()), prefix="minecraft-recipe-renderer")
    yield


app = FastAPI(lifespan=lifespan)

setup(app)
