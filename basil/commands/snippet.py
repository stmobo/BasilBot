from __future__ import annotations

import discord
from typing import Tuple, Union
import urllib.parse

from . import command, CommandContext, Command
from ..snippet import Snippet, SnippetNotFound
from ..series import SERIES_INDEX_KEY, Series, SeriesNotFound
from .. import config


@command("register")
async def register_snippet(ctx: CommandContext, args: Tuple[str], cmd: Command):
    """Save or update a snippet series.

    **Usage:** `b!register [series tag]`
    ℹ️ This command must be used as a reply to a snippet you have posted.

    This command adds snippets to the series with the given tag name, creating
    it if it does not already exist.

    This command will follow snippet chains and add them in-order to the series
    as necessary.
    """

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
            channel = await ctx.client.get_channel(channel_id)
        except discord.NotFound:
            break

        try:
            cur_msg = await channel.fetch_message(message_id)
        except discord.NotFound:
            break

    series.snippets.extend(reversed(new_snippets))
    await series.save(ctx)

    if new_series:
        await ctx.reply(
            "✅  Created series `{}` with {} snippet{}.".format(
                name, len(series.snippets), ("s" if len(series.snippets) > 1 else "")
            )
        )
    else:
        await ctx.reply(
            "✅  Appended {} new snippet{} to series `{}`.".format(
                len(new_snippets), ("s" if len(new_snippets) > 1 else ""), name
            )
        )

    url = urllib.parse.urljoin(
        config.get().api_base_url, "/series/" + urllib.parse.quote(name)
    )

    await ctx.reply(
        "ℹ️  **Link to series:** " + url, mention_author=False, ephemeral=False
    )

    if " " in name:
        await ctx.reply(
            "⚠️  **Warning:** Your snippet tag has spaces in it. You'll need to **surround the tag name with quotes** if you're using it in other commands!"
        )


@command("title")
async def set_title(ctx: CommandContext, args: Tuple[str], cmd: Command):
    """Set the title of a series.

    **Usage:** `b!title [series tag] [series title]`
    ⚠️ Series tags and titles must be surrounded by quotes if they contain spaces!

    (example: `b!title my_series "My Series"`)
    """
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


@command("rename")
async def rename_series(ctx: CommandContext, args: Tuple[str], cmd: Command):
    """Change the tag for a series you own.

    **Usage:** `b!rename [old series tag] [new series tag]`
    ⚠️  Series tags must be surrounded by quotes if they contain spaces!
    ℹ️  Moderators can rename any series, even ones they do not own.
    """

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

    try:
        await Series.load(ctx, new_tag)
        return await ctx.reply(
            "❌  There already exists a series going by the tag `{}`!".format(new_tag)
        )
    except SeriesNotFound:
        pass

    await series.rename(ctx, new_tag)
    return await ctx.reply(
        "✅  Renamed series tag `{}` to `{}`.".format(old_tag, new_tag)
    )


@command("delete")
async def delete_series(ctx: CommandContext, args: Tuple[str], cmd: Command):
    """Delete a series you own.

    **Usage:** `b!delete [series tag]`
    ⚠️  Series tags must be surrounded by quotes if they contain spaces!
    ℹ️  Moderators can delete any series, even ones they do not own.
    """

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


@command("link")
async def get_link(ctx: CommandContext, args: Tuple[str], cmd: Command):
    """Get a link to a series.

    **Usage:** `b!link [series tag]`
    ⚠️  Series tags must be surrounded by quotes if they contain spaces!
    """
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

    url = urllib.parse.urljoin(
        config.get().api_base_url, "/series/" + urllib.parse.quote(tag)
    )
    return await ctx.reply("ℹ️  **Link to series:** " + url, ephemeral=False)


@command("reindex", authorized_only=True, hidden="unauthorized")
async def reindex(ctx: CommandContext, args: Tuple[str], cmd: Command):
    """Reindex all snippets.

    **Usage:** `b!reindex`
    """

    n_tags = 0

    tr = ctx.redis.multi_exec()
    tr.delete(SERIES_INDEX_KEY)
    async for key_bytes in ctx.redis.iscan(match="series:*:snippets"):
        key: str = key_bytes.decode("utf-8")
        tag = key.split(":", 2)[1]
        tr.sadd(SERIES_INDEX_KEY, tag)
        n_tags += 1

    await tr.execute()

    return await ctx.reply("✅  Reindexed " + str(n_tags) + " series tags.")
