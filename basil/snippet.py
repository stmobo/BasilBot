from __future__ import annotations

import aioredis
import discord
import json
import re
from typing import Optional, Union
import urllib

from .commands import CommandContext
from .helper import ensure_redis


class SnippetNotFound(Exception):
    pass


class InvalidMessageURL(Exception):
    pass


class Snippet:
    def __init__(
        self, redis: aioredis.Redis, content: str, message_id: int, author_id: int
    ):
        self.redis: aioredis.Redis = redis
        self.content: str = content
        self.author_id: int = author_id
        self.message_id: int = message_id

    @property
    def escaped_content(self) -> str:
        return json.dumps(self.content)

    def wordcount(self) -> int:
        stripped = re.sub(
            r"\<(?:\@[\!\&]?|\#|a?\:\w+\:)\d+\>", "", self.content
        ).strip()
        
        return len(stripped.split())

    @classmethod
    async def from_message_url(cls, ctx: CommandContext, url: str) -> Snippet:
        res = urllib.parse.urlparse(url, scheme="https")

        if not (
            res.hostname.endswith("discord.com")
            or res.hostname.endswith("discordapp.com")
        ):
            raise InvalidMessageURL(url)

        path_parts = tuple(res.path.split("/")[1:])

        if path_parts[0] != "channels":
            raise InvalidMessageURL(url)

        channel_id = int(path_parts[2])
        msg_id = int(path_parts[3])

        channel: Optional[discord.abc.Messageable] = await ctx.client.fetch_channel(
            channel_id
        )
        if channel is None:
            raise SnippetNotFound(msg_id)

        try:
            message: discord.Message = await channel.fetch_message(msg_id)
        except discord.NotFound:
            raise SnippetNotFound(msg_id) from None

        return cls(ctx.redis, message.content, message.id, message.author.id)

    @classmethod
    def from_message(
        cls, redis_or_ctx: Union[CommandContext, aioredis.Redis], msg: discord.Message
    ) -> Snippet:
        return cls(ensure_redis(redis_or_ctx), msg.content, msg.id, msg.author.id)

    @classmethod
    async def load(
        cls, redis_or_ctx: Union[CommandContext, aioredis.Redis], message_id: int
    ) -> Snippet:
        redis = ensure_redis(redis_or_ctx)

        content = await redis.get("snippet:" + str(message_id) + ":content")
        author_id = await redis.get("snippet:" + str(message_id) + ":author")

        if content is None or author_id is None:
            raise SnippetNotFound(message_id)

        return cls(redis, content, message_id, int(author_id))

    async def save(self):
        async with self.redis.pipeline(transaction=True) as tr:
            tr.set("snippet:" + str(self.message_id) + ":content", self.content)
            tr.set("snippet:" + str(self.message_id) + ":author", str(self.author_id))
            await tr.execute()
