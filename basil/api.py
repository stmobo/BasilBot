from __future__ import annotations

import aioredis
from sanic import Sanic, Request, response

from . import config
from .snippet import Snippet

api_app = Sanic("")


@api_app.before_server_start
async def setup_redis(app, loop):
    app.ctx.redis = await aioredis.create_redis(config.primary_redis_url)


@api_app.get("/snippet/<msg_id:int>")
async def render_snippet(_req: Request, msg_id: int):
    snippet = await Snippet.load(api_app.ctx.redis, msg_id)
    return response.html(snippet.render())
