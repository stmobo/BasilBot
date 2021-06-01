from __future__ import annotations

from sanic import Sanic, Blueprint, Request, response, exceptions

from ...snippet import Snippet, SnippetNotFound

snippet_api = Blueprint("snippet_api", url_prefix="/snippet")
app = Sanic.get_app("basil")


@snippet_api.get("/<msg_id:int>")
async def get_snippet(_req: Request, msg_id: int):
    try:
        snippet = await Snippet.load(app.ctx.redis, msg_id)
    except SnippetNotFound:
        raise exceptions.NotFound("Could not find snippet " + msg_id)

    return response.text(snippet.content)
