from __future__ import annotations

import discord
from typing import Tuple, Union
import urllib.parse

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
            + "register [series tag]`\nℹ️ This command must be used as a reply to a snippet you have posted."
        )

    ref: discord.MessageReference = ctx.message.reference
    if (
        ref is None
        or ref.resolved is None
        or isinstance(ref.resolved, discord.DeletedReferencedMessage)
    ):
        return await ctx.reply(
            "❌  Could not retrieve snippet message.\nℹ️ This command must be used as a **reply** to a snippet that you have posted."
        )

    reply_msg: discord.Message = ref.resolved
    if reply_msg.author.id != ctx.user.id and not ctx.authorized:
        return await ctx.reply("❌  That snippet was not posted by you.")

    name = " ".join(args)
    new_series = False

    try:
        series = await Series.load(ctx, name)
    except SeriesNotFound:
        series = Series(ctx.user.id, name, [])
        new_series = True

    if series.author_id != ctx.user.id and not ctx.authorized:
        return await ctx.reply("❌  That series does not belong to you.")

    previous_snippet_ids = set(s.message_id for s in series.snippets)
    new_snippets = []
    cur_msg = reply_msg

    while (
        isinstance(cur_msg, discord.Message)
        and (cur_msg.author.id == ctx.user.id)
        and cur_msg.id not in previous_snippet_ids
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
            "✅  Created series `{}` with {} snippets.".format(
                name, len(series.snippets)
            )
        )
    else:
        return await ctx.reply(
            "✅  Appended {} new snippets to series `{}`.".format(
                len(new_snippets), name
            )
        )


@command("title", summary="Set the title of a series.")
async def set_title(ctx: CommandContext, args: Tuple[str], cmd: Command):
    if len(args) != 2:
        return await ctx.reply(
            "**USAGE:** `"
            + config.get().summon_prefix
            + "title [series tag] [series title]`",
        )

    tag, title = args

    try:
        series = await Series.load(ctx, tag)
    except SeriesNotFound:
        return await ctx.reply(
            "❌  There exists no series going by the tag `{}`.".format(tag)
        )

    if series.author_id != ctx.user.id and not ctx.authorized:
        return await ctx.reply("❌  That series does not belong to you.")

    series.title = title
    await series.save(ctx)

    return await ctx.reply(
        '✅  Set title of series `{}` to **"{}"**.'.format(tag, title)
    )


@command("rename", summary="Change the tag of a series.")
async def rename_series(ctx: CommandContext, args: Tuple[str], cmd: Command):
    if len(args) != 2:
        return await ctx.reply(
            "**USAGE:** `"
            + config.get().summon_prefix
            + "rename [old series tag] [new series tag]`",
        )

    old_tag, new_tag = args

    try:
        series = await Series.load(ctx, old_tag)
    except SeriesNotFound:
        return await ctx.reply(
            "❌  There exists no series going by the tag `{}`.".format(old_tag)
        )

    if series.author_id != ctx.user.id and not ctx.authorized:
        return await ctx.reply("❌  That series does not belong to you.")

    await series.rename(ctx, new_tag)
    return await ctx.reply(
        "✅  Renamed series tag `{}` to `{}`.".format(old_tag, new_tag)
    )


@command("delete", summary="Change the tag of a series.")
async def rename_series(ctx: CommandContext, args: Tuple[str], cmd: Command):
    if len(args) != 1:
        return await ctx.reply(
            "**USAGE:** `" + config.get().summon_prefix + "delete [series tag]`",
        )

    tag = args[0]

    try:
        series = await Series.load(ctx, tag)
    except SeriesNotFound:
        return await ctx.reply(
            "❌  There exists no series going by the tag `{}`.".format(tag)
        )

    if series.author_id != ctx.user.id and not ctx.authorized:
        return await ctx.reply("❌  That series does not belong to you.")

    await series.delete(ctx)
    return await ctx.reply("✅  Deleted series `{}`.".format(tag))


@command("link", summary="Get a link to a series.")
async def get_link(ctx: CommandContext, args: Tuple[str], cmd: Command):
    if len(args) != 1:
        return await ctx.reply(
            "**USAGE:** `" + config.get().summon_prefix + "link [series tag]`",
        )

    tag = args[0]

    try:
        await Series.load(ctx, tag)
    except SeriesNotFound:
        return await ctx.reply(
            "❌  There exists no series going by the tag `{}`.".format(tag)
        )

    url = urllib.parse.urljoin(config.get().api_base_url, "/series/" + tag)
    return await ctx.reply("ℹ️  Link to series: " + url, ephemeral=False)
