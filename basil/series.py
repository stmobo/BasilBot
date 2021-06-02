from __future__ import annotations

import aioredis
import json
import re
from typing import List, Optional, Union, Set, Dict
import time

from .commands import CommandContext
from .snippet import Snippet
from .helper import ensure_redis


SERIES_INDEX_KEY = "series_index"
MAIN_TITLE_INDEX_KEY = "series_title_index:main"
TITLE_SUBINDEX_PREFIX = "series_title_index:sub:"

# KEYS[1] is the series title key.
# KEYS[2] is the main index key.
# KEYS[3] is the title subindex key.
#
# ARGV[1] is the series tag.
# ARGV[2] is the normalized series title.
REMOVE_SERIES_TITLE_SCRIPT = r"""
-- delete series title key
redis.call("delete", KEYS[1])

-- remove tag from subindex
redis.call("srem", KEYS[3], ARGV[1])

-- if subindex is empty, delete it
if redis.call("scard", KEYS[3]) == 0 then
    redis.call("delete", KEYS[3])
    redis.call("srem", KEYS[2], ARGV[2])
end
"""

# KEYS[1] is the series title key.
# KEYS[2] is the main index key.
# KEYS[3] is the old title subindex key.
# KEYS[4] is the new title subindex key.
#
# ARGV[1] is the series tag.
# ARGV[2] is the new unnormalized series title.
# ARGV[3] is the old normalized series title.
# ARGV[4] is the new normalized series title.
RENAME_SERIES_TITLE_SCRIPT = r"""
-- set series title key
redis.call("set", KEYS[1], ARGV[2])

-- move tag from old subindex to new
redis.call("srem", KEYS[3], ARGV[1])
redis.call("sadd", KEYS[4], ARGV[1])

-- add new normalized title to main index
redis.call("sadd", KEYS[2], ARGV[4])

-- if old subindex is empty, delete it
if redis.call("scard", KEYS[3]) == 0 then
    redis.call("delete", KEYS[3])
    redis.call("srem", KEYS[2], ARGV[3])
end
"""


class SeriesNotFound(Exception):
    pass


class Series:
    @staticmethod
    def normalize_name(title: str) -> str:
        """Normalize a series title or tag for use in search queries."""
        ret = title.casefold()
        return re.sub(r"[\W\-]", "", ret)

    def __init__(
        self,
        redis: aioredis.Redis,
        tag: str,
        author_ids: Set[int],
        snippets: List[Snippet],
        title: Optional[str] = None,
        update_time: Optional[float] = None,
        subscribers: Optional[Set[int]] = None,
    ):
        tag = tag.strip()

        if title is None:
            title = tag.replace("_", " ").replace("-", " ").strip()

        if subscribers is None:
            subscribers = set()

        self.redis: aioredis.Redis = redis
        self.tag: str = tag
        self.author_ids: Set[int] = author_ids
        self.snippets: List[Snippet] = snippets
        self.title: str = title
        self.update_time: Optional[float] = update_time
        self.subscribers: Set[int] = subscribers

    @property
    def redis_prefix(self) -> str:
        return "series:" + self.tag

    def __eq__(self, o: object) -> bool:
        try:
            return self.tag == o.tag
        except AttributeError:
            return self.tag == o

    def __hash__(self) -> int:
        return hash(self.tag)

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

    @classmethod
    async def get_title_subindex(
        cls,
        redis_or_ctx: Union[aioredis.Redis, CommandContext],
        title: str,
        *,
        normalize: bool = True,
    ) -> Set[Series]:
        ret: Set[Series] = set()
        redis = ensure_redis(redis_or_ctx)

        if normalize:
            normalized = cls.normalize_name(title)
        else:
            normalized = title

        async for tag in redis.sscan_iter(TITLE_SUBINDEX_PREFIX + normalized):
            series = await Series.load(redis, tag)
            ret.add(series)

        return ret

    @classmethod
    async def find_by_title(
        cls, redis_or_ctx: Union[aioredis.Redis, CommandContext], query: str
    ) -> Dict[str, Set[Series]]:
        redis = ensure_redis(redis_or_ctx)
        normalized = Series.normalize_name(query)
        ret: Dict[str, Set[Series]] = {}

        idx_title: str
        async for idx_title in redis.sscan_iter(MAIN_TITLE_INDEX_KEY):
            if normalized in idx_title:
                ret[idx_title] = await cls.get_title_subindex(
                    redis, idx_title, normalize=False
                )

        return ret

    async def save(self, update_time=True):
        if update_time:
            self.update_time = time.time()

        snippet_ids = [s.message_id for s in self.snippets]

        async with self.redis.pipeline(transaction=True) as tr:
            tr.sadd(SERIES_INDEX_KEY, self.tag)

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

            normalized_title = self.normalize_name(self.title)
            tr.sadd(TITLE_SUBINDEX_PREFIX + normalized_title, self.tag)
            tr.sadd(MAIN_TITLE_INDEX_KEY, normalized_title)

            await tr.execute()

    async def delete(self):
        async with self.redis.pipeline(transaction=True) as tr:
            tr.delete(self.redis_prefix + ":snippets")
            tr.delete(self.redis_prefix + ":authors")
            tr.delete(self.redis_prefix + ":updated")
            tr.delete(self.redis_prefix + ":subscribers")
            tr.srem(SERIES_INDEX_KEY, self.tag)

            normalized_title = self.normalize_name(self.title)
            script = tr.register_script(REMOVE_SERIES_TITLE_SCRIPT)
            script(
                [
                    self.redis_prefix + ":title",
                    MAIN_TITLE_INDEX_KEY,
                    TITLE_SUBINDEX_PREFIX + normalized_title,
                ],
                [self.tag, normalized_title],
            )

            await tr.execute()

    def change_title(self, new_title: str):
        old_norm_title = self.normalize_name(self.title)
        new_norm_title = self.normalize_name(new_title)
        script = self.redis.register_script(RENAME_SERIES_TITLE_SCRIPT)

        self.title = new_title
        return script(
            [
                self.redis_prefix + ":title",
                MAIN_TITLE_INDEX_KEY,
                TITLE_SUBINDEX_PREFIX + old_norm_title,
                TITLE_SUBINDEX_PREFIX + new_norm_title,
            ],
            [self.tag, new_title, old_norm_title, new_norm_title],
        )

    async def change_tag(self, new_tag: str):
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

            tr.srem(SERIES_INDEX_KEY, self.tag)
            tr.sadd(SERIES_INDEX_KEY, new_tag)

            await tr.execute()

        self.tag = new_tag


async def check_series_schema(redis: aioredis.Redis):
    index_exists = bool(int(await redis.exists(SERIES_INDEX_KEY)))
    title_index_exists = bool(int(await redis.exists(MAIN_TITLE_INDEX_KEY)))

    async with redis.pipeline(transaction=True) as tr:
        do_exec = (not index_exists) or (not title_index_exists)

        key: str
        async for key in redis.scan_iter(match="series:*:snippets"):
            tag = key.split(":", 2)[1]
            redis_prefix = "series:" + tag

            if not index_exists:
                tr.sadd(SERIES_INDEX_KEY, tag)

            if not title_index_exists:
                title = await redis.get("series:" + tag + ":title")
                normalized_title = Series.normalize_name(title)

                tr.sadd(MAIN_TITLE_INDEX_KEY, normalized_title)
                tr.sadd(TITLE_SUBINDEX_PREFIX + normalized_title, tag)

            old_author_key = bool(int(await redis.exists(redis_prefix + ":author")))
            if old_author_key:
                author_id = int(await redis.get(redis_prefix + ":author"))
                tr.delete(redis_prefix + ":author")
                tr.set(redis_prefix + ":authors", json.dumps([author_id]))
                do_exec = True

        if do_exec:
            await tr.execute()
