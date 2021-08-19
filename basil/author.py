from __future__ import annotations

import asyncio
import discord
import json
from typing import Any, Dict, Set, Tuple, Optional

from . import series
from .helper import get_client
from .config import config


def get_member_names(user_id: int) -> Tuple[Set[str], str, str]:
    display_names = set()
    username: str = None
    discriminator: str = None

    guild: discord.Guild
    for guild in get_client().guilds:
        member: discord.User = guild.get_member(user_id)

        if member is None:
            continue

        display_names.add(member.display_name)
        username = member.name
        discriminator = member.discriminator

    if username is None:
        # todo: fix this
        username = "User " + str(user_id)
        discriminator = "????"
        display_names.add(username)

    #     loop = asyncio.get_running_loop()
    #     user = loop.run_until_complete(get_client().fetch_user(user_id))

    #     username = user.name
    #     discriminator = user.discriminator
    #     display_names.add(user.display_name)

    return display_names, username, discriminator


class Author:
    def __init__(
        self,
        author_id: int,
        display_names: Set[str],
        username: str,
        discriminator: str,
    ):
        self.id: int = author_id
        self.display_names: Set[str] = display_names
        self.username: str = username
        self.discriminator: str = discriminator

    @classmethod
    def get_by_id(cls, author_id: int) -> Author:
        return cls(author_id, *get_member_names(author_id))

    @property
    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "display_names": sorted(self.display_names),
            "username": self.username,
            "discriminator": self.discriminator,
        }

    @property
    def as_json(self) -> str:
        return json.dumps(self.as_dict)

    @property
    def is_administrator(self) -> bool:
        return self.id in config.administrators

    @property
    def joined_display_names(self) -> str:
        return " / ".join(sorted(self.display_names))

    def is_snippet_manager_for(self, s: series.Series) -> bool:
        return s.is_snippet_manager(self)

    def __eq__(self, o: Any) -> bool:
        try:
            return self.id == o.id
        except AttributeError:
            return self.id == o

    def __hash__(self) -> int:
        return hash(self.id)
