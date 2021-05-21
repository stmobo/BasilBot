from __future__ import annotations

import aioredis
import discord
from typing import Tuple

from .. import main, config


class CommandContext(object):
    def __init__(
        self,
        client: main.BasilClient,
        message: discord.Message
    ):
        self.client: main.BasilClient = client
        self.message: discord.Message = message

    @property
    def guild(self) -> discord.Guild:
        return self.message.guild

    @property
    def channel(self) -> discord.TextChannel:
        return self.message.channel

    @property
    def user(self) -> discord.Member:
        return self.message.author

    @property
    def redis(self) -> aioredis.Redis:
        return self.client.redis

    @property
    def authorized(self) -> bool:
        perms = self.channel.permissions_for(self.user)
        if perms.manage_messages or perms.administrator:
            return True

        management_role_name: str = config.get().management_role_name.strip().casefold()
        if len(management_role_name) > 0:
            return any(
                r.name.strip().casefold == management_role_name for r in self.user.roles
            )
        else:
            return False

    async def reply(self, content: str, as_reply=True, **kwargs) -> discord.Message:
        if as_reply:
            return await self.channel.send(
                content=content,
                reference=self.message,
                mention_author=True,
                **kwargs
            )
        else:
            return await self.channel.send(content=content, **kwargs)


