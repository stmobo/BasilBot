from __future__ import annotations

import aioredis
import discord

from ..config import config
from .. import main


class CommandContext(object):
    def __init__(self, client: main.BasilClient, message: discord.Message):
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
        if self.user.guild_permissions.administrator:
            return True

        perms = self.channel.permissions_for(self.user)
        if perms.manage_messages or perms.administrator:
            return True

        management_role_name: str = config.management_role_name.strip().casefold()
        if len(management_role_name) > 0:
            return any(
                r.name.strip().casefold() == management_role_name
                for r in self.user.roles
            )
        else:
            return False

    async def reply(
        self, content: str, as_reply=True, mention_author=True, ephemeral=True, **kwargs
    ) -> discord.Message:
        if as_reply:
            reply_msg = await self.channel.send(
                content=content,
                reference=self.message,
                mention_author=mention_author,
                **kwargs
            )
        else:
            reply_msg = await self.channel.send(content=content, **kwargs)

        if ephemeral:
            await reply_msg.delete(delay=7.0)

        return reply_msg
