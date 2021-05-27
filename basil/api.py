from __future__ import annotations

import aioredis
import discord
from sanic import Sanic, Request, response, exceptions
from jinja2 import Environment, PackageLoader, select_autoescape
import urllib.parse

from . import config
from .snippet import Snippet, SnippetNotFound
from .series import Series, SeriesNotFound, SERIES_INDEX_KEY

api_app = Sanic("Basil")
env = Environment(loader=PackageLoader("basil"), autoescape=select_autoescape())
snippet_template = env.get_template("snippet.html")
series_template = env.get_template("series.html")


@api_app.before_server_start
async def setup_redis(app, loop):
    app.ctx.redis = await aioredis.create_redis(config.get().primary_redis_url)


@api_app.get("/api/snippet/<msg_id:int>")
async def get_snippet(_req: Request, msg_id: int):
    try:
        snippet = await Snippet.load(api_app.ctx.redis, msg_id)
    except SnippetNotFound:
        raise exceptions.NotFound("Could not find snippet " + msg_id)

    return response.text(snippet.content)


@api_app.get("/snippet/<msg_id:int>")
async def render_snippet(_req: Request, msg_id: int):
    try:
        snippet = await Snippet.load(api_app.ctx.redis, msg_id)
    except SnippetNotFound:
        raise exceptions.NotFound("Could not find snippet " + msg_id)

    rendered = snippet_template.render(snippet_name="Snippet", snippet_id=msg_id)
    return response.html(rendered)


@api_app.get("/series/<name>")
async def render_series(_req: Request, name: str):
    name = urllib.parse.unquote(name)

    try:
        series = await Series.load(api_app.ctx.redis, name)
    except SeriesNotFound:
        raise exceptions.NotFound("Could not find series " + name)

    client: discord.Client = api_app.ctx.client
    primary_server: discord.Guild = client.get_guild(config.get().primary_server_id)
    member: discord.Member = primary_server.get_member(series.author_id)

    rendered = series_template.render(
        snippets=series.snippets,
        series_name=series.name,
        series_title=series.title,
        display_name=member.display_name,
        username=member.name,
        discriminator=member.discriminator,
    )
    return response.html(rendered)


@api_app.get("/series")
async def get_all_series(_req: Request):
    client: discord.Client = api_app.ctx.client
    primary_server: discord.Guild = client.get_guild(config.get().primary_server_id)

    ret = []
    async for tag_bytes in api_app.ctx.redis.isscan(SERIES_INDEX_KEY):
        tag: str = tag_bytes.decode("utf-8")
        try:
            series = await Series.load(api_app.ctx.redis, tag)
        except SeriesNotFound:
            continue

        member: discord.Member = primary_server.get_member(series.author_id)
        ret.append(
            {
                "tag": tag,
                "title": series.title,
                "n_snippets": len(series.snippets),
                "author": {
                    "id": series.author_id,
                    "username": member.name,
                    "display_name": member.display_name,
                    "discriminator": member.discriminator,
                },
            }
        )

    return response.json(ret)
