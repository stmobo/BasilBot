from __future__ import annotations

import aioredis
import discord
from sanic import Sanic, Blueprint, Request, response, exceptions
from sanic.views import HTTPMethodView
from schema import Schema, And, Optional, SchemaError
import urllib.parse

from ...series import Series, SeriesNotFound, SERIES_INDEX_KEY
from .. import helper
from .auth import DiscordUserInfo

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
    PATCH_SCHEMA = Schema(
        And(
            {
                Optional("tag"): And(str, lambda s: len(s.strip())),
                Optional("title"): And(str, lambda s: len(s.strip())),
            },
            len,
        )
    )

    @staticmethod
    def respond_with_series(series: Series, **kwargs) -> response.HTTPResponse:
        client: discord.Client = app.ctx.client

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
        return response.json(
            {
                "tag": series.tag,
                "title": series.title.strip(),
                "snippets": snippets,
                "authors": authors,
                "url": app.url_for("view.series", name=urllib.parse.quote(series.tag)),
                "updated": series.update_time,
            },
            **kwargs
        )

    async def get(self, req: Request, tag: str):
        try:
            series = await Series.load(app.ctx.redis, tag)
        except SeriesNotFound:
            raise exceptions.NotFound("Could not find series " + tag)

        return SeriesView.respond_with_series(series)

    async def patch(self, req: Request, tag: str):
        redis: aioredis.Redis = app.ctx.redis
        discord_user = await DiscordUserInfo.load(req)

        if discord_user is None:
            raise exceptions.Forbidden("Not logged in")

        try:
            series = await Series.load(redis, tag)
        except SeriesNotFound:
            raise exceptions.NotFound("Could not find series " + tag)

        if (
            discord_user.id not in series.author_ids
            and not discord_user.is_snippet_manager()
        ):
            raise exceptions.Forbidden("User is not series author")

        try:
            data = self.PATCH_SCHEMA.validate(req.json)
        except SchemaError:
            raise exceptions.InvalidUsage("Payload does not fit schema")

        if "tag" in data:
            await series.change_tag(data["tag"].strip())

        if "title" in data:
            await series.change_title(data["title"].strip())

        return SeriesView.respond_with_series(series)

    async def delete(self, req: Request, tag: str):
        redis: aioredis.Redis = app.ctx.redis
        discord_user = await DiscordUserInfo.load(req)

        if discord_user is None:
            raise exceptions.Forbidden("Not logged in")

        try:
            series = await Series.load(redis, tag)
        except SeriesNotFound:
            raise exceptions.NotFound("Could not find series " + tag)

        if (
            discord_user.id not in series.author_ids
            and not discord_user.is_snippet_manager()
        ):
            raise exceptions.Forbidden("User is not series author")

        await series.delete()
        return response.empty()


series_api.add_route(SeriesView.as_view(), "/<tag>")
