from __future__ import annotations

import asyncio
import aioredis
import discord
import logging
from typing import Optional

from . import config
from . import commands
from . import web
from .snippet import Snippet, SnippetNotFound, scan_message_channels
from .series import check_series_schema, get_author_count, get_series_count

logging.basicConfig(level=logging.INFO)
bot_root_logger = logging.getLogger("bot")

discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.INFO)

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.typing = False
INTENTS.voice_states = False


class BasilClient(discord.Client):
    perms_integer = 85056
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

    async def update_presence_loop(self):
        ctr = 0
        while True:
            try:
                if config.get().maintenance_mode:
                    await self.change_presence(
                        activity=discord.Game("Maintenance Mode")
                    )
                else:
                    if ctr == 0:
                        series_count = await get_series_count(self.redis)
                        await self.change_presence(
                            activity=discord.Game(str(series_count) + " Snippets")
                        )
                    elif ctr == 1:
                        author_count = await get_author_count(self.redis)
                        await self.change_presence(
                            activity=discord.Game(str(author_count) + " Authors")
                        )
                    elif ctr == 2:
                        prefix = config.get().summon_prefix
                        await self.change_presence(
                            activity=discord.Game(prefix + "help")
                        )
                    ctr = (ctr + 1) % 3
            except Exception:
                logging.exception("Caught exception in presence update loop")

            await asyncio.sleep(15)

    async def on_ready(self):
        logging.info(
            "Logged in as {name} ({id})\n------\nInvite URL:\nhttps://discordapp.com/api/oauth2/authorize?client_id={id}&scope=bot&permissions={perms}".format(
                name=self.user.name, id=self.user.id, perms=self.perms_integer
            )
        )

        self.redis = aioredis.from_url(
            config.get().primary_redis_url, encoding="utf-8", decode_responses=True
        )

        await check_series_schema(self.redis)
        await scan_message_channels(self, self.redis)
        asyncio.create_task(self.update_presence_loop())

        self.ready = True

    async def on_message(self, msg):
        if not self.ready:
            return

        if msg.author.id == self.user.id or msg.author.bot:
            return

        if msg.type != discord.MessageType.default:
            return

        return await commands.dispatch(self, msg)

    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        channel_id = payload.channel_id
        msg_id = payload.message_id

        try:
            snippet = await Snippet.load(self.redis, msg_id)
        except SnippetNotFound:
            return

        channel: discord.abc.Messageable = self.get_channel(channel_id)
        message: discord.Message = await channel.fetch_message(msg_id)

        snippet.content = message.content
        await snippet.save()


@web.app.before_server_start
async def start_bot(app, loop):
    client = BasilClient(activity=discord.Game("Starting..."), intents=INTENTS)

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

    app.ctx.client = client
    app.add_task(client.start(config.get().token))


def app_main():
    return web.app.run(host="0.0.0.0", port=8080)
