from __future__ import annotations

from aiohttp import ClientSession, ClientResponse, ClientResponseError
from aioredis import Redis, RedisError
import logging
import secrets
import time
from typing import Optional, Dict, Iterable, Union, Tuple
from urllib.parse import urljoin, urlencode

from sanic import Sanic
from sanic.request import Request
from sanic.response import redirect, HTTPResponse
from sanic.exceptions import InvalidUsage, ServerError

STATE_START = "unauthenticated"
STATE_INPROGRESS = "in-progress"
STATE_AUTHORIZED = "authorized"
REDIS_BASE_PREFIX = "sessions:auth"

app = Sanic.get_app("basil")


class OAuth2API(object):
    def __init__(
        self,
        authorize_url: str,
        token_url: str,
        revoke_url: str,
        redirect_url: str,
        client_id: str,
        client_secret: str,
        prefix: str,
    ):
        self.authorize_url: str = authorize_url
        self.token_url: str = token_url
        self.revoke_url: str = revoke_url
        self.redirect_url: str = redirect_url
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.prefix: str = prefix

    def authorization_url(self, nonce: str, scopes: str, **kwargs) -> str:
        qstring = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_url,
                "response_type": "code",
                "state": nonce,
                "scope": scopes,
                **kwargs,
            }
        )

        return urljoin(self.authorize_url, "?" + qstring)

    async def exchange_code(
        self, session: ClientSession, scopes: str, code: str
    ) -> ClientResponse:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_url,
            "scope": scopes,
            "grant_type": "authorization_code",
            "code": code,
        }
        return await session.post(
            self.token_url, data=data, headers=headers, raise_for_status=True
        )

    async def refresh_token(
        self, session: ClientSession, scopes: str, refresh_token: str
    ) -> ClientResponse:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_url,
            "scope": scopes,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        return await session.post(
            self.token_url, data=data, headers=headers, raise_for_status=True
        )

    async def revoke_token(self, session: ClientSession, token: str) -> ClientResponse:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "token": token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        return await session.post(
            self.revoke_url, data=data, headers=headers, raise_for_status=True
        )

    async def load_request_context(self, req: Request) -> OAuth2Context:
        return await OAuth2Context.load(
            req.ctx.session, app.ctx.http_session, app.ctx.redis, self
        )


class OAuth2Context(object):
    def __init__(
        self,
        session_id: str,
        http_session: ClientSession,
        redis: Redis,
        api: OAuth2API,
        **kwargs
    ):
        self.session_id = session_id
        self.http = http_session
        self.redis = redis
        self.api = api

        self.state: str = kwargs.get("state", STATE_START)
        self.nonce: Optional[str] = kwargs.get("nonce")
        self.landing_page: Optional[str] = kwargs.get("landing")
        self.scopes: Optional[str] = kwargs.get("scopes")

        self.access_token: Optional[str] = kwargs.get("access_token")
        self.token_type: Optional[str] = kwargs.get("token_type")
        self.refresh_token: Optional[str] = kwargs.get("refresh_token")
        self.expire_time: Optional[float] = None

        if "expire_time" in kwargs:
            self.expire_time = float(kwargs["expire_time"])

    @property
    def auth_data_key(self) -> str:
        return REDIS_BASE_PREFIX + ":" + self.api.prefix + ":" + self.session_id

    @property
    def expire_in(self) -> float:
        if self.expire_time is None:
            return 0

        return self.expire_time - time.time()

    @staticmethod
    def generate_nonce() -> str:
        return secrets.token_urlsafe(16)

    @classmethod
    async def load(
        cls, session_id: str, http_session: ClientSession, redis: Redis, api: OAuth2API
    ) -> OAuth2Context:
        data = await redis.hgetall(
            REDIS_BASE_PREFIX + ":" + api.prefix + ":" + session_id
        )
        if data is None:
            data = {}

        return cls(session_id, http_session, redis, api, **data)

    async def reset(self):
        """Completely reset all state associated with this context."""
        if self.access_token is not None and self.expire_in > 0:
            try:
                resp = await self.api.revoke_token(self.http, self.access_token)
                async with resp:
                    msg = await resp.text()
                    logging.info(
                        "Revoked token for session {}: {}".format(self.session_id, msg)
                    )
            except ClientResponseError:
                logging.error(
                    "Could not revoke token for session {}".format(self.session_id),
                    exc_info=True,
                )

        try:
            await self.redis.delete(self.auth_data_key)
        except RedisError:
            logging.error(
                "Could not delete Redis key {} for session {}".format(
                    self.auth_data_key, self.session_id
                ),
                exc_info=True,
            )

        self.access_token = None
        self.token_type = None
        self.refresh_token = None
        self.expire_time = None
        self.nonce = None
        self.landing_page = None
        self.scopes = None
        self.state = STATE_START

    async def start(
        self, scopes: Union[str, Iterable[str]], landing_page: str, **kwargs
    ) -> HTTPResponse:
        """Begin an OAuth2 client authentication flow."""
        if isinstance(scopes, str):
            scopes = scopes.split()
        else:
            scopes = list(scopes)

        await self.reset()

        self.scopes = " ".join(scopes)
        self.nonce = self.generate_nonce()
        self.landing_page = landing_page
        self.state = STATE_INPROGRESS

        async with self.redis.pipeline(transaction=True) as tr:
            tr.hmset(
                self.auth_data_key,
                {
                    "state": STATE_INPROGRESS,
                    "nonce": self.nonce,
                    "scopes": self.scopes,
                    "landing": landing_page,
                },
            )
            tr.expire(self.auth_data_key, 900)
            await tr.execute()

        return redirect(
            self.api.authorization_url(self.nonce, self.scopes, **kwargs), status=303
        )

    async def _save_token(self, resp: ClientResponse):
        async with resp:
            token_data: dict = await resp.json()

            self.access_token = token_data["access_token"]
            self.token_type = token_data["token_type"]
            self.refresh_token = token_data.get("refresh_token")
            self.expire_time = time.time() + token_data["expires_in"]
            if "scope" in token_data:
                self.scopes = token_data["scope"]

        try:
            async with self.redis.pipeline(transaction=True) as tr:
                tr.hmset(
                    self.auth_data_key,
                    {
                        "state": STATE_AUTHORIZED,
                        "access_token": self.access_token,
                        "token_type": self.token_type,
                        "refresh_token": self.refresh_token,
                        "expire_time": str(self.expire_time),
                        "scopes": self.scopes,
                    },
                )
                tr.hdel(self.auth_data_key, "nonce", "landing")
                tr.expireat(self.auth_data_key, self.expire_time)
                await tr.execute()
        except RedisError:
            raise ServerError("Could not save authorization data to Redis")

    async def redirect(self, code: str, state_param: str) -> HTTPResponse:
        """Handle an authorization redirection in the OAuth2 flow."""
        if self.state != STATE_INPROGRESS:
            raise ServerError(
                "Authorization flow in incorrect state for handling redirect"
            )

        if self.nonce != state_param:
            raise InvalidUsage("Incorrect state parameter in redirect")

        try:
            resp = await self.api.exchange_code(self.http, self.scopes, code)
        except ClientResponseError as err:
            raise ServerError(
                "Could not get access token (error {}): {}".format(
                    err.status, err.message
                )
            )
        await self._save_token(resp)

        return redirect(self.landing_page, status=303)

    async def refresh(self):
        """Refresh the access token associated with this context."""
        if self.state != STATE_AUTHORIZED:
            return

        try:
            resp = await self.api.refresh_token(
                self.http, self.scopes, self.refresh_token
            )
        except ClientResponseError as err:
            raise ServerError(
                "Could not get access token (error {}): {}".format(
                    err.status, err.message
                )
            )
        await self._save_token(resp)

    async def credentials(self) -> Optional[Tuple[str, str]]:
        """Get the access token and its type, refreshing as necessary.

        If the token is close to expiring, it will automatically be refreshed.
        If the token has expired or has not been obtained yet, returns None.
        """
        if self.state != STATE_AUTHORIZED:
            return None

        if self.expire_in <= 0:
            await self.reset()
            return None
        elif self.expire_in <= 86400:
            await self.refresh()

        if self.token_type is None or self.access_token is None:
            return None

        return (self.token_type, self.access_token)

    async def auth_header(self) -> Optional[Dict[str, str]]:
        """Get the HTTP headers used for authorizing requests in this context."""
        creds = await self.credentials()
        if creds is None:
            return None
        return {"Authorization": creds[0] + " " + creds[1]}
