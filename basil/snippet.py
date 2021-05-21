from __future__ import annotations

import aioredis
import discord
from typing import Optional, Union
import urllib

from .commands import CommandContext


class SnippetNotFound(Exception):
    pass


class InvalidMessageURL(Exception):
    pass


class Snippet:
    def __init__(self, content: str, message_id: int, author_id: int):
        self.content: str = content
        self.author_id: int = author_id
        self.message_id: int = message_id

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

        return cls(message.content, message.id, message.author.id)

    @classmethod
    def from_message(cls, msg: discord.Message) -> Snippet:
        return cls(msg.content, msg.id, msg.author.id)

    @classmethod
    async def load(
        cls, redis_or_ctx: Union[CommandContext, aioredis.Redis], message_id: int
    ) -> Snippet:
        redis: aioredis.Redis = redis_or_ctx

        try:
            redis = redis_or_ctx.redis
        except AttributeError:
            pass

        content = await redis.get(
            "snippet:" + str(message_id) + ":content", encoding="utf-8"
        )

        author_id = await redis.get(
            "snippet:" + str(message_id) + ":author", encoding="utf-8"
        )

        if content is None or author_id is None:
            raise SnippetNotFound(message_id)

        return cls(content, message_id, int(author_id))

    async def save(self, redis_or_ctx: Union[CommandContext, aioredis.Redis]):
        redis: aioredis.Redis = redis_or_ctx

        try:
            redis = redis_or_ctx.redis
        except AttributeError:
            pass

        tr = redis.multi_exec()
        tr.set("snippet:" + str(self.message_id) + ":content", self.content)
        tr.set("snippet:" + str(self.message_id) + ":author", str(self.author_id))
        await tr.execute()
