from __future__ import annotations

import aiohttp
import aioredis
from sanic import Sanic

from ..config import config

app = Sanic("basil")


@app.before_server_start
async def setup_redis(app, loop):
    app.ctx.http_session = aiohttp.ClientSession()
    app.ctx.redis = aioredis.from_url(
        config.primary_redis_url, encoding="utf-8", decode_responses=True
    )


from .api import api
from .view import view

app.blueprint(api)
app.blueprint(view)
