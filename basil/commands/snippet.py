from __future__ import annotations

import discord
from typing import Tuple, Union

from . import command, CommandContext, Command
from ..snippet import Snippet, InvalidMessageURL, SnippetNotFound
from .. import config


@command("register", summary="Save a snippet.")
async def register_snippet(ctx: CommandContext, args: Tuple[str], cmd: Command):
    if len(args) < 1:
        return await ctx.reply(
            "**USAGE:** `"
            + config.get().summon_prefix
            + "register [name]`\nℹ️ This command must be used as a reply to a snippet you have posted.",
            ephemeral=True,
        )

    ref: discord.MessageReference = ctx.message.reference
    if ref.resolved is None or isinstance(
        ref.resolved, discord.DeletedReferencedMessage
    ):
        return await ctx.reply(
            "❌ Could not retrieve snippet message.\nℹ️ This command must be used as a **reply** to a snippet that you have posted.",
            ephemeral=True,
        )

    reply_msg: discord.Message = ref.resolved
    if reply_msg.author.id != ctx.user.id:
        return await ctx.reply("❌ That snippet was not posted by you.", ephemeral=True)

    snippet = Snippet.from_message(reply_msg)
    await snippet.save(ctx)

    return await ctx.reply("✅ Snippet saved!")
