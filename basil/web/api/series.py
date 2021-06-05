from __future__ import annotations
from basil.snippet import Snippet
from typing import Dict, List

import aioredis
import discord
from sanic import Sanic, Blueprint, Request, response, exceptions
from sanic.views import HTTPMethodView
from schema import Schema, And, Optional, SchemaError
import urllib.parse

from ...series import Series, SeriesNotFound, SERIES_INDEX_KEY
from .auth import DiscordUserInfo

series_api = Blueprint("series_api", url_prefix="/series")
app = Sanic.get_app("basil")


@series_api.exception(
    exceptions.NotFound, exceptions.Forbidden, exceptions.InvalidUsage
)
async def api_exception_handler(_req: Request, exception: exceptions.SanicException):
    return response.text(exception.args[0], status=exception.status_code)


@series_api.get("/")
async def get_all_series(req: Request):
    redis: aioredis.Redis = app.ctx.redis
    discord_user = await DiscordUserInfo.load(req)
    ret = []

    tag: str
    async for tag in redis.sscan_iter(SERIES_INDEX_KEY):
        try:
            series = await Series.load(redis, tag)
        except SeriesNotFound:
            continue

        d = series.as_dict_trimmed
        if discord_user is not None:
            d["can_edit"] = series.can_edit(discord_user.as_author)
        else:
            d["can_edit"] = False

        ret.append(d)

    return response.json(ret)


class SeriesView(HTTPMethodView):
    PATCH_SCHEMA = Schema(
        And(
            {
                Optional("tag"): And(str, lambda s: len(s.strip())),
                Optional("title"): And(str, lambda s: len(s.strip())),
                Optional("snippets"): And([int], len),
            },
            len,
        )
    )

    @staticmethod
    async def respond_with_series(
        req: Request, series: Series
    ) -> response.HTTPResponse:
        ret = series.as_dict
        discord_user = await DiscordUserInfo.load(req)

        if discord_user is not None:
            ret["can_edit"] = series.can_edit(discord_user.as_author)
        else:
            ret["can_edit"] = False

        return response.json(ret)

    async def get(self, req: Request, tag: str):
        tag = urllib.parse.unquote(tag)

        try:
            series = await Series.load(app.ctx.redis, tag)
        except SeriesNotFound:
            raise exceptions.NotFound("Could not find series " + tag)

        return SeriesView.respond_with_series(req, series)

    async def patch(self, req: Request, tag: str):
        tag = urllib.parse.unquote(tag)
        redis: aioredis.Redis = app.ctx.redis
        discord_user = await DiscordUserInfo.load(req)

        if discord_user is None:
            raise exceptions.Forbidden("Not logged in")

        try:
            series = await Series.load(redis, tag)
        except SeriesNotFound:
            raise exceptions.NotFound("Could not find series " + tag)

        author = discord_user.as_author

        if discord_user.id not in series.author_ids and not series.is_snippet_manager(
            author
        ):
            raise exceptions.Forbidden("User is not series author")

        try:
            data = self.PATCH_SCHEMA.validate(req.json)
        except SchemaError:
            raise exceptions.InvalidUsage("Payload does not fit schema")

        if "tag" in data and data["tag"].strip() != series.tag:
            new_tag = data["tag"].strip()

            try:
                await Series.load(redis, new_tag)
                raise exceptions.InvalidUsage(
                    'A series with tag "{}" already exists.'.format(new_tag)
                )
            except SeriesNotFound:
                pass

            await series.change_tag(new_tag)

        if "title" in data and data["title"].strip() != series.title:
            await series.change_title(data["title"].strip())

        if "snippets" in data:
            old_snippets: Dict[int, Snippet] = {}
            for snippet in series.snippets:
                old_snippets[snippet.message_id] = snippet

            new_snippet_seq: List[Snippet] = []
            snippet_id: int
            for snippet_id in data["snippets"]:
                try:
                    new_snippet_seq.append(old_snippets[snippet_id])
                except KeyError:
                    raise exceptions.InvalidUsage(
                        "Cannot add new snippets to series"
                    ) from None

            if len(new_snippet_seq) == 0:
                raise exceptions.InvalidUsage("Series cannot be empty")

            series.snippets = new_snippet_seq
            await series.save()

        return SeriesView.respond_with_series(req, series)

    async def delete(self, req: Request, tag: str):
        tag = urllib.parse.unquote(tag)
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
