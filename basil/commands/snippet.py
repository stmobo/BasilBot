from __future__ import annotations
import logging

import discord
from typing import Tuple, Union
import urllib.parse

from . import command, CommandContext, Command
from ..snippet import Snippet
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

    name = " ".join(args).strip()
    new_series = False
    series: Series

    try:
        series = await Series.resolve(ctx, name, ctx.user.id)
    except SeriesNotFound:
        series = Series(ctx.redis, name, set([ctx.user.id]), [])
        new_series = True

    if ctx.user.id not in series.author_ids and not ctx.authorized:
        return await ctx.reply("❌  That series does not belong to you.")

    previous_snippet_ids = set(s.message_id for s in series.snippets)
    new_snippets = []
    cur_msg = reply_msg

    while (
        isinstance(cur_msg, discord.Message)
        and ((cur_msg.author.id in series.author_ids) or ctx.authorized)
        and cur_msg.id not in previous_snippet_ids
    ):
        snippet = Snippet.from_message(ctx, cur_msg)
        await snippet.save()

        new_snippets.append(snippet)

        if cur_msg.reference is None:
            break

        channel_id = cur_msg.reference.channel_id
        message_id = cur_msg.reference.message_id

        if message_id is None:
            break

        channel: discord.TextChannel = ctx.client.get_channel(channel_id)
        if channel is None:
            break

        try:
            cur_msg = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden) as e:
            break

    if len(new_snippets) == 0:
        if new_series:
            return await ctx.reply(
                "❌  I couldn't find any snippets to collect for this series!"
            )
        else:
            return await ctx.reply(
                "❌  I couldn't find any new snippets to add to this series!"
            )

    series.snippets.extend(reversed(new_snippets))
    await series.save()

    if new_series:
        await ctx.reply(
            '✅  Created series `{}` ("**{}**") with {} snippet{}.'.format(
                series.tag,
                series.title,
                len(series.snippets),
                ("s" if len(series.snippets) > 1 else ""),
            )
        )
    else:
        await ctx.reply(
            '✅  Appended {} new snippet{} to series `{}` ("{}").'.format(
                len(new_snippets),
                ("s" if len(new_snippets) > 1 else ""),
                series.tag,
                series.title,
            )
        )

    await ctx.reply(
        "ℹ️  **Link to series:** " + series.view_url,
        mention_author=False,
        ephemeral=False,
    )

    if " " in name:
        await ctx.reply(
            "⚠️  **Warning:** Your snippet tag has spaces in it. You'll need to **surround the tag name with quotes** if you're using it in other commands!"
        )

    for subscriber_id in series.subscribers:
        user: discord.User = ctx.client.get_user(subscriber_id)

        if user is None:
            continue

        try:
            await user.send(
                "ℹ️  Snippet series **{}** has updated!\n**Link to series:** {}".format(
                    series.title, series.view_url
                )
            )
        except Exception:
            logging.error(
                "Caught error when sending update notifications", exc_info=True
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

    if ctx.user.id not in series.author_ids and not ctx.authorized:
        return await ctx.reply("❌  That series does not belong to you.")

    if series.title != title:
        await series.change_title(title)

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

    if ctx.user.id not in series.author_ids and not ctx.authorized:
        return await ctx.reply("❌  That series does not belong to you.")

    try:
        await Series.load(ctx, new_tag)
        return await ctx.reply(
            "❌  There already exists a series going by the tag `{}`!".format(new_tag)
        )
    except SeriesNotFound:
        pass

    await series.change_tag(new_tag)
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

    if ctx.user.id not in series.author_ids and not ctx.authorized:
        return await ctx.reply("❌  That series does not belong to you.")

    await series.delete()
    return await ctx.reply("✅  Deleted series `{}`.".format(tag))


@command("subscribe")
async def subscribe_to_series(ctx: CommandContext, args: Tuple[str], cmd: Command):
    """Subscribe to updates for a series.

    **Usage:** `b!subscribe [series tag]`
    ⚠️  Series tags must be surrounded by quotes if they contain spaces!

    Subscribing to a series allows you to receive DM notifications whenever that
    series updates with new snippets.

    You can unsubscribe from a series using `b!unsubscribe [series tag]`.
    """

    if len(args) != 1:
        return await ctx.reply(
            "**USAGE:** `" + config.get().summon_prefix + "subscribe [series tag]`",
        )

    tag = args[0]

    try:
        series = await Series.load(ctx, tag)
    except SeriesNotFound:
        return await ctx.reply(
            "❌  There exists no series going by the tag `{}`.".format(tag)
        )

    if ctx.user.id not in series.subscribers:
        series.subscribers.add(ctx.user.id)
        await series.save(update_time=False)

        return await ctx.reply(
            "✅  Subscribed to series **{}** (`{}`).".format(series.title, tag)
        )
    else:
        return await ctx.reply("ℹ️  You are already subscribed to that series.")


@command("unsubscribe")
async def subscribe_to_series(ctx: CommandContext, args: Tuple[str], cmd: Command):
    """Unsubscribe from updates for a series.

    **Usage:** `b!unsubscribe [series tag]`
    ⚠️  Series tags must be surrounded by quotes if they contain spaces!

    This command unsubscribes you from update notifications for the given series;
    you will no longer receive DMs from that series whenever it updates with
    new snippets.
    """

    if len(args) != 1:
        return await ctx.reply(
            "**USAGE:** `" + config.get().summon_prefix + "unsubscribe [series tag]`",
        )

    tag = args[0]

    try:
        series = await Series.load(ctx, tag)
    except SeriesNotFound:
        return await ctx.reply(
            "❌  There exists no series going by the tag `{}`.".format(tag)
        )

    if ctx.user.id in series.subscribers:
        series.subscribers.remove(ctx.user.id)
        await series.save(update_time=False)

        return await ctx.reply(
            "✅  Unsubscribed from series **{}** (`{}`).".format(series.title, tag)
        )
    else:
        return await ctx.reply("ℹ️  You are not subscribed to that series.")


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
        series = await Series.load(ctx, tag)
    except SeriesNotFound:
        return await ctx.reply(
            "❌  There exists no series going by the tag `{}`.".format(tag)
        )

    return await ctx.reply(
        "ℹ️  **Link to series:** " + series.view_url, ephemeral=False
    )


@command("index")
async def get_index(ctx: CommandContext, args: Tuple[str], cmd: Command):
    """Get a link to the series index.

    **Usage:** `b!index`
    """

    url = urllib.parse.urljoin(config.get().api_base_url, "/series_index.html")
    return await ctx.reply("ℹ️  **Link to series index:** " + url, ephemeral=False)
