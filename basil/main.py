from __future__ import annotations

import asyncio
import aioredis
import discord
import logging

from typing import Optional

from . import config
from . import commands

logging.basicConfig(level=logging.INFO)
bot_root_logger = logging.getLogger("bot")

discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.INFO)

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.typing = False
INTENTS.voice_states = False


class BasilClient(discord.Client):
    perms_integer = 379968
    ready = False

    _inst: Optional[BasilClient] = None

    def __init__(self, *args, **kwargs):
        if BasilClient._inst is not None:
            raise RuntimeError("attempting to initialize two clients")
        BasilClient._inst = self
        super().__init__(*args, **kwargs)

    @classmethod
    def get(cls) -> BasilClient:
        """Get the global BasilClient instance."""
        if cls._inst is None:
            raise RuntimeError("BasilClient not initialized yet")
        else:
            return cls._inst

    async def on_ready(self):
        logging.info(
            "Logged in as {name} ({id})\n------\nInvite URL:\nhttps://discordapp.com/api/oauth2/authorize?client_id={id}&scope=bot%20applications.commands&permissions={perms}".format(
                name=self.user.name, id=self.user.id, perms=self.perms_integer
            )
        )

        self.redis = await aioredis.create_redis(config.primary_redis_url)

        if config.get().maintenance_mode:
            await self.change_presence(
                activity=discord.CustomActivity("Maintenance Mode")
            )
        else:
            await self.change_presence(
                activity=discord.CustomActivity("Organizing Snippets")
            )

        self.ready = True

    async def on_message(self, msg):
        if not self.ready:
            return

        if msg.author.id == self.user.id or msg.author.bot:
            return

        if msg.type != discord.MessageType.default:
            return

        return await commands.dispatch(self, msg)


def main():
    client = BasilClient(
        activity=discord.CustomActivity("Starting..."), intents=INTENTS
    )

    # Initialize logging handlers:
    handler = logging.FileHandler(
        filename=config.get().discord_log, encoding="utf-8", mode="w"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
    )
    discord_logger.addHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
    )
    bot_root_logger.addHandler(handler)

    return asyncio.run(client.start(config.get().token))
