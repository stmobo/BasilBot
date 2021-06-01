from __future__ import annotations

import aioredis
from typing import Union

from .commands import CommandContext


def ensure_redis(redis_or_ctx: Union[CommandContext, aioredis.Redis]) -> aioredis.Redis:
    try:
        return redis_or_ctx.redis
    except AttributeError:
        return redis_or_ctx
