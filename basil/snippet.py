from __future__ import annotations
from operator import eq

import aioredis
import discord
import logging
import json
import re
from typing import Optional, Union, List, Iterator
import urllib

from discord.errors import Forbidden, NotFound

from .commands import CommandContext
from .helper import ensure_redis

IMAGE_ATTACHMENT_TYPES = set(["image/jpeg", "image/png", "image/gif", "image/webp"])
CW_REGEX = r"^[\(\[\<\|\s]*[CcTt][Ww]\W+(\w.*?)[\)\]\|\>\s]*$"


class SnippetNotFound(Exception):
    pass


class InvalidMessageURL(Exception):
    pass


class Snippet:
    def __init__(
        self,
        redis: aioredis.Redis,
        content: str,
        message_id: int,
        channel_id: int,
        author_id: int,
        attachment_urls: List[str],
    ):
        self.redis: aioredis.Redis = redis
        self.content: str = content
        self.author_id: int = author_id
        self.message_id: int = message_id
        self.channel_id: int = channel_id
        self.attachment_urls: List[str] = attachment_urls

    @property
    def escaped_content(self) -> str:
        return json.dumps(self.content)

    @property
    def json_attachment_urls(self) -> str:
        return json.dumps(self.attachment_urls)

    @property
    def content_warnings(self) -> Iterator[str]:
        for match in re.finditer(CW_REGEX, self.content, re.MULTILINE):
            yield match[1].strip()

    def wordcount(self) -> int:
        stripped = re.sub(
            r"\<(?:\@[\!\&]?|\#|a?\:\w+\:)\d+\>", "", self.content
        ).strip()

        return len(stripped.split())

    @classmethod
    def from_message(
        cls, redis_or_ctx: Union[CommandContext, aioredis.Redis], msg: discord.Message
    ) -> Snippet:
        attachment_urls = []
        for attachment in msg.attachments:
            if attachment.content_type in IMAGE_ATTACHMENT_TYPES:
                attachment_urls.append(attachment.url)

        return cls(
            ensure_redis(redis_or_ctx),
            msg.content,
            msg.id,
            msg.channel.id,
            msg.author.id,
            attachment_urls,
        )

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

        return cls.from_message(ctx, message)

    @classmethod
    async def load(
        cls, redis_or_ctx: Union[CommandContext, aioredis.Redis], message_id: int
    ) -> Snippet:
        redis = ensure_redis(redis_or_ctx)

        content = await redis.get("snippet:" + str(message_id) + ":content")
        author_id = await redis.get("snippet:" + str(message_id) + ":author")
        channel_id = await redis.get("snippet:" + str(message_id) + ":channel")
        attachment_list = await redis.get("snippet:" + str(message_id) + ":attachments")

        if content is None or author_id is None:
            raise SnippetNotFound(message_id)

        if attachment_list is not None:
            attachment_list = json.loads(attachment_list)
        else:
            attachment_list = []

        return cls(
            redis, content, message_id, int(author_id), int(channel_id), attachment_list
        )

    async def save(self):
        async with self.redis.pipeline(transaction=True) as tr:
            tr.set("snippet:" + str(self.message_id) + ":content", self.content)
            tr.set("snippet:" + str(self.message_id) + ":author", str(self.author_id))
            tr.set("snippet:" + str(self.message_id) + ":channel", str(self.channel_id))
            tr.set(
                "snippet:" + str(self.message_id) + ":attachments",
                json.dumps(self.attachment_urls),
            )
            await tr.execute()


async def scan_message_channels(client: discord.Client, redis: aioredis.Redis):
    ver = await redis.get("snippet_schema:version")
    if ver is not None:
        ver = int(ver)
    else:
        ver = 0

    if ver >= 1:
        return

    key: str
    async for key in redis.scan_iter(match="snippet:*:content"):
        message_id = int(key.split(":", 2)[1])

        channel: discord.TextChannel
        for channel in filter(
            lambda c: isinstance(c, discord.TextChannel),
            client.get_all_channels(),
        ):
            try:
                message: discord.Message = await channel.fetch_message(message_id)
                async with redis.pipeline(transaction=True) as tr:
                    tr.set("snippet:" + str(message_id) + ":channel", str(channel.id))

                    attachments = []
                    for attachment in message.attachments:
                        if attachment.content_type in IMAGE_ATTACHMENT_TYPES:
                            attachments.append(attachment.url)

                    tr.set(
                        "snippet:" + str(message_id) + ":attachments",
                        json.dumps(attachments),
                    )

                    tr.set(
                        "snippet:" + str(message_id) + ":content",
                        message.content,
                    )

                    await tr.execute()

                logging.info(
                    "Added message channel and attachment data for snippet "
                    + str(message_id)
                )
                break
            except (NotFound, Forbidden) as e:
                continue

    await redis.set("snippet_schema:version", 1)
