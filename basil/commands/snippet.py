from __future__ import annotations

import discord
from typing import Tuple, Union

from . import command, CommandContext, Command
from ..snippet import Snippet, SnippetNotFound
from ..series import Series, SeriesNotFound
from .. import config


@command("register", summary="Save or update a snippet series.")
async def register_snippet(ctx: CommandContext, args: Tuple[str], cmd: Command):
    if len(args) < 1:
        return await ctx.reply(
            "**USAGE:** `"
            + config.get().summon_prefix
            + "register [series key]`\nℹ️ This command must be used as a reply to a snippet you have posted.",
            ephemeral=True,
        )

    ref: discord.MessageReference = ctx.message.reference
    if (
        ref is None
        or ref.resolved is None
        or isinstance(ref.resolved, discord.DeletedReferencedMessage)
    ):
        return await ctx.reply(
            "❌ Could not retrieve snippet message.\nℹ️ This command must be used as a **reply** to a snippet that you have posted.",
            ephemeral=True,
        )

    reply_msg: discord.Message = ref.resolved
    if reply_msg.author.id != ctx.user.id:
        return await ctx.reply("❌ That snippet was not posted by you.", ephemeral=True)

    name = " ".join(args)
    new_series = False

    try:
        series = await Series.load(ctx, ctx.user.id, name)
    except SeriesNotFound:
        series = Series(ctx.user.id, name, [])
        new_series = True

    last_snippet_id = None
    if len(series.snippets) > 0:
        last_snippet_id = series.snippets[-1].message_id

    new_snippets = []
    cur_msg = reply_msg

    while (
        isinstance(cur_msg, discord.Message)
        and (cur_msg.author.id == ctx.user.id)
        and cur_msg.id != last_snippet_id
    ):
        snippet = Snippet.from_message(cur_msg)
        await snippet.save(ctx)

        new_snippets.append(snippet)

        if cur_msg.reference is None:
            break

        channel_id = cur_msg.reference.channel_id
        message_id = cur_msg.reference.message_id

        if message_id is None:
            break

        try:
            channel = await ctx.client.fetch_channel(channel_id)
        except discord.NotFound:
            break

        try:
            cur_msg = await channel.fetch_message(message_id)
        except discord.NotFound:
            break

    series.snippets.extend(reversed(new_snippets))
    await series.save(ctx)

    if new_series:
        return await ctx.reply(
            "✅ Created series `{}` with {} snippets.".format(name, len(series.snippets))
        )
    else:
        return await ctx.reply(
            "✅ Appended {} new snippets to series `{}`.".format(len(new_snippets), name)
        )


@command("title", summary="Set the title of a series.")
async def set_title(ctx: CommandContext, args: Tuple[str], cmd: Command):
    if len(args) != 2:
        return await ctx.reply(
            "**USAGE:** `"
            + config.get().summon_prefix
            + "title [series key] [series title]`",
            ephemeral=True,
        )

    key, title = args

    try:
        series = await Series.load(ctx, ctx.user.id, key)
    except SeriesNotFound:
        return await ctx.reply(
            "❌ You have no series going by the key `{}`.".format(key), ephemeral=True
        )

    series.title = title
    await series.save(ctx)

    return await ctx.reply(
        '✅ Set title of series `{}` to **"{}"**.'.format(key, title), ephemeral=True
    )
