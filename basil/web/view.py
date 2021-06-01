from __future__ import annotations

import discord
from jinja2 import Environment, PackageLoader, select_autoescape
from sanic import Sanic, Blueprint, Request, response, exceptions
import urllib.parse

from ..series import Series, SeriesNotFound
from . import helper

view = Blueprint("view", url_prefix="/series")
app = Sanic.get_app("basil")
env = Environment(loader=PackageLoader("basil.web"), autoescape=select_autoescape())

series_template = env.get_template("series.html.j2")


@view.get("/<name>")
async def series(_req: Request, name: str):
    name = urllib.parse.unquote(name)

    try:
        series = await Series.load(app.ctx.redis, name)
    except SeriesNotFound:
        raise exceptions.NotFound("Could not find series " + name)

    client: discord.Client = app.ctx.client
    display_names, username, discriminator = helper.get_member_names(
        client, series.author_id
    )

    rendered = series_template.render(
        snippets=series.snippets,
        series_name=series.name,
        series_title=series.title,
        display_name=" / ".join(display_names),
        username=username,
        discriminator=discriminator,
    )
    return response.html(rendered)