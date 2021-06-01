from __future__ import annotations

import aioredis
import discord
from sanic import Sanic, Blueprint, Request, response
import urllib.parse

from ...series import Series, SeriesNotFound, SERIES_INDEX_KEY
from .. import helper

series_api = Blueprint("series_api", url_prefix="/series")
app = Sanic.get_app("basil")


@series_api.get("/")
async def get_all_series(_req: Request):
    client: discord.Client = app.ctx.client
    redis: aioredis.Redis = app.ctx.redis

    ret = []
    async for tag_bytes in redis.isscan(SERIES_INDEX_KEY):
        tag: str = tag_bytes.decode("utf-8")
        try:
            series = await Series.load(redis, tag)
        except SeriesNotFound:
            continue

        display_names, username, discriminator = helper.get_member_names(
            client, series.author_id
        )
        ret.append(
            {
                "tag": tag,
                "title": series.title.strip(),
                "n_snippets": len(series.snippets),
                "author": {
                    "id": series.author_id,
                    "display_name": " / ".join(display_names),
                    "username": username,
                    "discriminator": discriminator,
                },
                "url": app.url_for("view.series", name=urllib.parse.quote(tag)),
                "updated": series.update_time,
            }
        )

    return response.json(ret)
