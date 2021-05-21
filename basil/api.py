from __future__ import annotations

import aioredis
from sanic import Sanic, Request, response, exceptions
from jinja2 import Environment, PackageLoader, select_autoescape

from . import config
from .snippet import Snippet, SnippetNotFound

api_app = Sanic("Basil")
env = Environment(loader=PackageLoader("basil"), autoescape=select_autoescape())
snippet_template = env.get_template("snippet.html")


@api_app.before_server_start
async def setup_redis(app, loop):
    app.ctx.redis = await aioredis.create_redis(config.get().primary_redis_url)


@api_app.get("/api/snippet/<msg_id:int>")
async def render_snippet(_req: Request, msg_id: int):
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
