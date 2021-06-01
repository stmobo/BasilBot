from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from typing import Optional, Dict, Any, Tuple, List
import secrets
import urllib.parse

import aiohttp
from aioredis import Redis
import discord
from discord import guild
from itsdangerous import Signer, BadSignature
from sanic import Sanic, Blueprint, response, exceptions
from sanic.request import Request
from sanic.response import HTTPResponse

from ... import config
from ..oauth2 import OAuth2API, OAuth2Context
from .. import helper

SESSION_COOKIE_ID = "session"
REDIS_KEY_PREFIX = "auth:sessions:"
DISCORD_API_URL = "https://discordapp.com/api/v9"
REQUIRED_SCOPES = "identify"

cookie_signer = Signer(
    bytes.fromhex(config.get().cookie_signer_key), digest_method=hashlib.sha256
)
auth_api = Blueprint("auth_api", url_prefix="/auth")
app = Sanic.get_app("basil")

oauth2_api = OAuth2API(
    DISCORD_API_URL + "/oauth2/authorize",
    DISCORD_API_URL + "/oauth2/token",
    DISCORD_API_URL + "/oauth2/token/revoke",
    config.get().oauth2_redirect_uri,
    config.get().client_id,
    config.get().client_secret,
    "discord",
)


class DiscordUserInfo(object):
    def __init__(
        self,
        user_id: int,
        ctx: OAuth2Context,
    ):
        self.id: int = user_id
        self.ctx: OAuth2Context = ctx

    def get_member_names(self) -> Tuple[List[str], str, str]:
        return helper.get_member_names(app.ctx.client, self.id)

    def is_snippet_manager(self) -> bool:
        primary_guild: discord.Guild = app.ctx.client.get_guild(
            config.get().primary_server_id
        )
        member: discord.Member = guild.get_member(self.id)

        if member is None:
            return False

        management_role_name: str = config.get().management_role_name.strip().casefold()
        for role in member.roles:
            if role.permissions.administrator or (
                len(management_role_name) > 0
                and role.name.strip().casefold() == management_role_name
            ):
                return True
        return False

    def as_dict(self) -> Dict[str, Any]:
        ret = helper.author_id_to_object(app.ctx.client, self.id)
        ret["is_manager"] = self.is_snippet_manager()
        return ret

    async def save(self):
        redis: Redis = app.ctx.redis

        async with redis.pipeline(transaction=True) as tr:
            tr.set("sessions:users:" + self.ctx.session_id, self.id)
            tr.expireat("sessions:users:" + self.ctx.session_id, self.ctx.expire_time)
            await tr.execute()

    @classmethod
    async def load(cls, req: Request) -> Optional[DiscordUserInfo]:
        discord_ctx: OAuth2Context = await oauth2_api.load_request_context(req)
        redis: Redis = app.ctx.redis
        http_sess: aiohttp.ClientSession = app.ctx.http_session

        auth = await discord_ctx.auth_header()
        if auth is None:
            # not logged in
            await redis.delete("sessions:users:" + discord_ctx.session_id)
            return None

        cached_user_id = await redis.get("sessions:users:" + discord_ctx.session_id)
        if cached_user_id is not None:
            return cls(cached_user_id, discord_ctx)

        async with http_sess.get(DISCORD_API_URL + "/users/@me", headers=auth) as resp:
            if resp.status >= 400:
                resp_text = await resp.text()
                logging.error(
                    "Could not get user info for session {}: {}".format(
                        discord_ctx.session_id, resp_text
                    )
                )

                raise exceptions.ServerError("Could not get Discord user info")

            user_data = await resp.json()

        ret = cls(user_data["id"], discord_ctx)
        await ret.save()

        return ret


@app.middleware("request")
async def load_session_id(request: Request):
    origin_ip = request.remote_addr
    if origin_ip is None or len(origin_ip) == 0:
        origin_ip = request.ip

    sess_id = None
    try:
        cookie_data = request.cookies["session"]
        sess_id = cookie_signer.unsign(cookie_data).decode("utf-8")
    except (BadSignature, UnicodeDecodeError):
        logging.warning("IP {} presented invalid session cookie".format(origin_ip))
    except KeyError:
        pass

    if sess_id is None:
        sess_id = secrets.token_urlsafe(16)
        request.ctx.add_sess_cookie = True
    else:
        request.ctx.add_sess_cookie = False
    request.ctx.session = sess_id


@app.middleware("response")
async def save_session_id(request: Request, response: HTTPResponse):
    if request.ctx.session is not None and request.ctx.add_sess_cookie:
        signed = cookie_signer.sign(request.ctx.session).decode("utf-8")
        response.cookies["session"] = signed
        response.cookies["session"]["secure"] = True
        response.cookies["session"]["max-age"] = 86400 * 7


@app.middleware("request")
async def load_session_id(request: Request):
    origin_ip = request.remote_addr
    if origin_ip is None or len(origin_ip) == 0:
        origin_ip = request.ip

    sess_id = None
    try:
        cookie_data = request.cookies["session"]
        sess_id = cookie_signer.unsign(cookie_data).decode("utf-8")
    except (BadSignature, UnicodeDecodeError):
        logging.warning("IP {} presented invalid session cookie".format(origin_ip))
    except KeyError:
        pass

    if sess_id is None:
        sess_id = secrets.token_urlsafe(16)
        request.ctx.add_sess_cookie = True
    else:
        request.ctx.add_sess_cookie = False
    request.ctx.session = sess_id


@app.middleware("response")
async def save_session_id(request: Request, response: HTTPResponse):
    if request.ctx.session is not None and request.ctx.add_sess_cookie:
        signed = cookie_signer.sign(request.ctx.session).decode("utf-8")
        response.cookies["session"] = signed
        response.cookies["session"]["secure"] = True
        response.cookies["session"]["max-age"] = 86400 * 7



@auth_api.get("/me")
async def get_login_data(request: Request):
    discord_user = await DiscordUserInfo.load(request)

    data = {
        "logged_in": discord_user is not None,
        "session_id": request.ctx.session,
        "dev_mode": config.get().dev_mode,
    }

    if discord_user is not None:
        data["user_data"] = discord_user.as_dict()
    else:
        data["user_data"] = None

    return response.json(data)


@auth_api.get("/logout")
async def logout(request: Request):
    discord_ctx: OAuth2Context = await oauth2_api.load_request_context(request)

    await discord_ctx.reset()
    return response.redirect(config.get().login_redirect_target, status=303)


@auth_api.get("/login")
async def start_oauth2(request: Request):
    discord_ctx: OAuth2Context = await oauth2_api.load_request_context(request)
    return await discord_ctx.start(
        REQUIRED_SCOPES, config.get().login_redirect_target, prompt="none"
    )


@auth_api.get("/authorized")
async def oauth2_complete(request: Request):
    try:
        state: str = request.args["state"][0]
    except (KeyError, IndexError):
        raise exceptions.InvalidUsage("Missing required parameter 'state'")

    try:
        code: str = request.args["code"][0]
    except (KeyError, IndexError):
        raise exceptions.InvalidUsage("Missing required parameter 'code'")

    discord_ctx: OAuth2Context = await oauth2_api.load_request_context(request)
    return await discord_ctx.redirect(code, state)
