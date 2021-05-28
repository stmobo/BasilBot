from __future__ import annotations

import aioredis
import json
from typing import List, Optional, Union, Set
import time

from .commands import CommandContext
from .snippet import Snippet


SERIES_INDEX_KEY = "series_index"


class SeriesNotFound(Exception):
    pass


class Series:
    def __init__(
        self,
        author_id: int,
        name: str,
        snippets: List[Snippet],
        title: Optional[str] = None,
        update_time: Optional[float] = None,
        subscribers: Optional[Set[int]] = None,
    ):
        name = name.strip()

        if title is None:
            title = name.replace("_", " ")

        if subscribers is None:
            subscribers = set()

        self.name: str = name
        self.author_id: int = author_id
        self.snippets: List[Snippet] = snippets
        self.title: str = title
        self.update_time: Optional[float] = update_time
        self.subscribers: Set[int] = subscribers

    @property
    def redis_prefix(self) -> str:
        return "series:" + self.name

    def append(self, snippet: Snippet):
        self.snippets.append(snippet)

    @classmethod
    async def load(
        cls,
        redis_or_ctx: Union[aioredis.Redis, CommandContext],
        name: str,
    ) -> Series:
        redis: aioredis.Redis = redis_or_ctx

        try:
            redis = redis_or_ctx.redis
        except AttributeError:
            pass

        redis_prefix = "series:" + name

        snippet_ids = await redis.get(redis_prefix + ":snippets", encoding="utf-8")

        if snippet_ids is None:
            raise SeriesNotFound(name)

        title = await redis.get(redis_prefix + ":title", encoding="utf-8")
        author_id = await redis.get(redis_prefix + ":author", encoding="utf-8")
        update_time = await redis.get(redis_prefix + ":updated", encoding="utf-8")
        subscribers = await redis.get(redis_prefix + ":subscribers", encoding="utf-8")

        try:
            update_time = float(update_time)
        except TypeError:
            pass

        if subscribers is not None:
            subscribers = set(json.loads(subscribers))

        snippet_ids = json.loads(snippet_ids)
        snippets = []
        for msg_id in snippet_ids:
            snippet = await Snippet.load(redis, msg_id)
            snippets.append(snippet)

        return cls(int(author_id), name, snippets, title, update_time, subscribers)

    async def save(
        self, redis_or_ctx: Union[aioredis.Redis, CommandContext], update_time=True
    ):
        redis: aioredis.Redis = redis_or_ctx

        try:
            redis = redis_or_ctx.redis
        except AttributeError:
            pass

        if update_time:
            self.update_time = time.time()

        snippet_ids = [s.message_id for s in self.snippets]
        tr = redis.multi_exec()

        tr.set(
            self.redis_prefix + ":snippets",
            json.dumps(snippet_ids),
        )

        tr.set(
            self.redis_prefix + ":title",
            self.title,
        )

        tr.sadd(SERIES_INDEX_KEY, self.name)
        tr.set(self.redis_prefix + ":author", str(self.author_id))
        tr.set(self.redis_prefix + ":subscribers", json.dumps(list(self.subscribers)))

        if update_time:
            tr.set(self.redis_prefix + ":updated", str(self.update_time))

        await tr.execute()

    async def delete(self, redis_or_ctx: Union[aioredis.Redis, CommandContext]):
        redis: aioredis.Redis = redis_or_ctx

        try:
            redis = redis_or_ctx.redis
        except AttributeError:
            pass

        tr = redis.multi_exec()
        tr.delete(self.redis_prefix + ":snippets")
        tr.delete(self.redis_prefix + ":title")
        tr.delete(self.redis_prefix + ":author")
        tr.delete(self.redis_prefix + ":updated")
        tr.delete(self.redis_prefix + ":subscribers")
        tr.srem(SERIES_INDEX_KEY, self.name)
        await tr.execute()

    async def rename(
        self, redis_or_ctx: Union[aioredis.Redis, CommandContext], new_tag: str
    ):
        redis: aioredis.Redis = redis_or_ctx

        try:
            redis = redis_or_ctx.redis
        except AttributeError:
            pass

        tr = redis.multi_exec()

        new_prefix = "series:" + new_tag

        tr.rename(
            self.redis_prefix + ":snippets",
            new_prefix + ":snippets",
        )

        tr.rename(
            self.redis_prefix + ":title",
            new_prefix + ":title",
        )

        tr.rename(
            self.redis_prefix + ":author",
            new_prefix + ":author",
        )

        tr.rename(
            self.redis_prefix + ":updated",
            new_prefix + ":updated",
        )

        tr.rename(
            self.redis_prefix + ":subscribers",
            new_prefix + ":subscribers",
        )

        tr.srem(SERIES_INDEX_KEY, self.name)
        tr.sadd(SERIES_INDEX_KEY, new_tag)

        await tr.execute()
        self.name = new_tag
