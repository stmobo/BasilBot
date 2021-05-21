from __future__ import annotations

import aioredis
import discord
import json
from typing import List, Optional, Union

from .commands import CommandContext
from .snippet import Snippet


class SeriesNotFound(Exception):
    pass


class Series:
    def __init__(self, author_id: int, name: str, snippets: List[Snippet], title: Optional[str]=None):
        if title is None:
            title = name

        self.name: str = name
        self.author_id: int = author_id
        self.snippets: List[Snippet] = snippets
        self.title: str = title

    def append(self, snippet: Snippet):
        self.snippets.append(snippet)

    @classmethod
    async def load(
        cls,
        redis_or_ctx: Union[aioredis.Redis, CommandContext],
        author_id: int,
        name: str,
    ) -> Series:
        redis: aioredis.Redis = redis_or_ctx

        try:
            redis = redis_or_ctx.redis
        except AttributeError:
            pass

        snippet_ids = await redis.get(
            "series:" + str(author_id) + ":" + name + ":snippets", encoding="utf-8"
        )

        if snippet_ids is None:
            raise SeriesNotFound(author_id, name)

        title = await redis.get(
            "series:" + str(author_id) + ":" + name + ":title", encoding="utf-8"
        )

        snippet_ids = json.loads(snippet_ids)
        snippets = []
        for msg_id in snippet_ids:
            snippet = await Snippet.load(redis, msg_id)
            snippets.append(snippet)

        return cls(author_id, name, snippets, title)

    async def save(self, redis_or_ctx: Union[aioredis.Redis, CommandContext]):
        redis: aioredis.Redis = redis_or_ctx

        try:
            redis = redis_or_ctx.redis
        except AttributeError:
            pass

        snippet_ids = [s.message_id for s in self.snippets]
        await redis.set(
            "series:" + str(self.author_id) + ":" + self.name + ":snippets",
            json.dumps(snippet_ids),
        )
        
        await redis.set(
            "series:" + str(self.author_id) + ":" + self.name + ":title",
            self.title,
        )