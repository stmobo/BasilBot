from __future__ import annotations

from sanic import Blueprint
from .snippet import snippet_api
from .series import series_api

api = Blueprint.group(snippet_api, series_api, url_prefix="/api")
