from __future__ import annotations

import aioredis
from sanic import Sanic

from .. import config

app = Sanic("basil")


@app.before_server_start
async def setup_redis(app, loop):
    app.ctx.redis = await aioredis.create_redis(config.get().primary_redis_url)


from .api import api
from .view import view

app.blueprint(api)
app.blueprint(view)
