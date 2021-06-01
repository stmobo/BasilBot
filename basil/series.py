from __future__ import annotations

import aioredis
import json
from typing import List, Optional, Union, Set
import time

from .commands import CommandContext
from .snippet import Snippet
from .helper import ensure_redis


SERIES_INDEX_KEY = "series_index"


class SeriesNotFound(Exception):
    pass


class Series:
    def __init__(
        self,
        redis: aioredis.Redis,
        name: str,
        author_ids: Set[int],
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

        self.redis: aioredis.Redis = redis
        self.name: str = name
        self.author_ids: Set[int] = author_ids
        self.snippets: List[Snippet] = snippets
        self.title: str = title
        self.update_time: Optional[float] = update_time
        self.subscribers: Set[int] = subscribers

    @property
    def redis_prefix(self) -> str:
        return "series:" + self.name

    def wordcount(self) -> int:
        return sum(snippet.wordcount() for snippet in self.snippets)

    @classmethod
    async def load(
        cls,
        redis_or_ctx: Union[aioredis.Redis, CommandContext],
        name: str,
    ) -> Series:
        redis = ensure_redis(redis_or_ctx)
        redis_prefix = "series:" + name

        snippet_ids = await redis.get(redis_prefix + ":snippets")

        if snippet_ids is None:
            raise SeriesNotFound(name)

        author_ids = set(json.loads(await redis.get(redis_prefix + ":authors")))
        title = await redis.get(redis_prefix + ":title")
        update_time = await redis.get(redis_prefix + ":updated")
        subscribers = await redis.get(redis_prefix + ":subscribers")

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

        return cls(redis, name, author_ids, snippets, title, update_time, subscribers)

    async def save(self, update_time=True):
        if update_time:
            self.update_time = time.time()

        snippet_ids = [s.message_id for s in self.snippets]

        async with self.redis.pipeline(transaction=True) as tr:
            tr.sadd(SERIES_INDEX_KEY, self.name)

            tr.set(
                self.redis_prefix + ":snippets",
                json.dumps(snippet_ids),
            )

            tr.set(
                self.redis_prefix + ":title",
                self.title,
            )

            tr.set(self.redis_prefix + ":authors", json.dumps(list(self.author_ids)))
            tr.set(
                self.redis_prefix + ":subscribers", json.dumps(list(self.subscribers))
            )

            if update_time:
                tr.set(self.redis_prefix + ":updated", str(self.update_time))

            await tr.execute()

    async def delete(self):
        async with self.redis.pipeline(transaction=True) as tr:
            tr.delete(self.redis_prefix + ":snippets")
            tr.delete(self.redis_prefix + ":title")
            tr.delete(self.redis_prefix + ":authors")
            tr.delete(self.redis_prefix + ":updated")
            tr.delete(self.redis_prefix + ":subscribers")
            tr.srem(SERIES_INDEX_KEY, self.name)
            await tr.execute()

    async def rename(self, new_tag: str):
        new_prefix = "series:" + new_tag

        async with self.redis.pipeline(transaction=True) as tr:
            tr.rename(
                self.redis_prefix + ":snippets",
                new_prefix + ":snippets",
            )

            tr.rename(
                self.redis_prefix + ":title",
                new_prefix + ":title",
            )

            tr.rename(
                self.redis_prefix + ":authors",
                new_prefix + ":authors",
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


async def check_series_schema(redis: aioredis.Redis):
    index_exists = bool(int(await redis.exists(SERIES_INDEX_KEY)))

    async with redis.pipeline(transaction=True) as tr:
        do_exec = index_exists

        key: str
        async for key in redis.scan_iter(match="series:*:snippets"):
            tag = key.split(":", 2)[1]
            redis_prefix = "series:" + tag

            if not index_exists:
                tr.sadd(SERIES_INDEX_KEY, tag)

            old_author_key = bool(int(await redis.exists(redis_prefix + ":author")))

            if old_author_key:
                author_id = int(await redis.get(redis_prefix + ":author"))
                tr.delete(redis_prefix + ":author")
                tr.set(redis_prefix + ":authors", json.dumps([author_id]))
                do_exec = True

        if do_exec:
            await tr.execute()
