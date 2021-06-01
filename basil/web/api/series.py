from __future__ import annotations

import aioredis
import discord
from sanic import Sanic, Blueprint, Request, response, exceptions
from sanic.views import HTTPMethodView
from schema import Schema, And, Optional, SchemaError
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

    tag: str
    async for tag in redis.sscan_iter(SERIES_INDEX_KEY):
        try:
            series = await Series.load(redis, tag)
        except SeriesNotFound:
            continue

        authors = [helper.author_id_to_object(client, id) for id in series.author_ids]
        ret.append(
            {
                "tag": tag,
                "title": series.title.strip(),
                "n_snippets": len(series.snippets),
                "wordcount": series.wordcount(),
                "authors": authors,
                "url": app.url_for("view.series", name=urllib.parse.quote(tag)),
                "updated": series.update_time,
            }
        )

    return response.json(ret)


class SeriesView(HTTPMethodView):
    PUT_SCHEMA = Schema(
        And(
            {
                Optional("title"): And(str, len),
                Optional("snippets"): And([int], len),
                Optional("authors"): And([int], len),
            },
            len,
        )
    )

    async def get(self, req: Request, tag: str):
        client: discord.Client = app.ctx.client
        redis: aioredis.Redis = app.ctx.redis

        try:
            series = await Series.load(redis, tag)
        except SeriesNotFound:
            raise exceptions.NotFound("Could not find series " + tag)

        snippets = []
        for snippet in series.snippets:
            snippets.append(
                {
                    "content": snippet.content,
                    "message_id": snippet.message_id,
                    "author_id": snippet.author_id,
                }
            )

        authors = [helper.author_id_to_object(client, id) for id in series.author_ids]
        ret = {
            "tag": tag,
            "title": series.title.strip(),
            "snippets": snippets,
            "authors": authors,
            "url": app.url_for("view.series", name=urllib.parse.quote(tag)),
            "updated": series.update_time,
        }

        return response.json(ret)

    async def put(self, req: Request, tag: str):
        pass


series_api.add_route(SeriesView.as_view(), "/<tag>")
