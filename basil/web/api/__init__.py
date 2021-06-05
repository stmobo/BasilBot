from __future__ import annotations

from sanic import Blueprint
from .series import series_api
from .auth import auth_api

api = Blueprint.group(series_api, auth_api, url_prefix="/api")
