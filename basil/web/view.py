from __future__ import annotations

import discord
from jinja2 import Environment, PackageLoader, select_autoescape
from sanic import Sanic, Blueprint, Request, response, exceptions
import urllib.parse

from ..series import Series, SeriesNotFound
from ..config import config

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

    rendered = series_template.render(
        series=series, static_manifest=config.static_manifest
    )
    return response.html(rendered)
