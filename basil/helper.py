from __future__ import annotations

import aioredis
import discord
from typing import Union

from . import main
from .commands import CommandContext

ContainsRedis = Union[CommandContext, aioredis.Redis]
ContainsClient = Union[CommandContext, discord.Client]


def ensure_redis(redis_or_ctx: Union[CommandContext, aioredis.Redis]) -> aioredis.Redis:
    try:
        return redis_or_ctx.redis
    except AttributeError:
        return redis_or_ctx


def get_client() -> "main.BasilClient":
    return main.BasilClient.get()
