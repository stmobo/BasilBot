from __future__ import annotations

import discord
import re
from typing import Optional, Iterable, Any

from .router import (
    CommandRouter,
    Command,
    CommandNotFoundError,
    AmbiguousCommandError,
    CommandNotAuthorizedError,
)

from .. import main, config
from .context import CommandContext


COMMANDS = CommandRouter("")
CMD_REGEX = r"\"([^\"]+)\"|\'([^\']+)\'|\`\`\`([^\`]+)\`\`\`|\`([^\`]+)\`|(\S+)"


def command(
    name: str,
    *,
    summary: Optional[str] = None,
    authorized_only: bool = False,
    shortcuts: Iterable[str] = tuple(),
    group: Optional[Any] = None,
    needs_cmd_obj: bool = False,
    hidden: str = "never",
    aliases: Iterable[str] = tuple(),
):
    global COMMANDS

    def wrapper(func):
        cmd = Command(
            func,
            name,
            summary=summary,
            authorized_only=authorized_only,
            group=group,
            needs_cmd_obj=needs_cmd_obj,
            hidden=hidden,
        )
        COMMANDS.add_router(name, cmd)

        for shortcut in shortcuts:
            COMMANDS.add_router(shortcut, cmd, as_shortcut=True)
        for alias in aliases:
            COMMANDS.add_router(alias, cmd, as_alias=True)

        return cmd

    return wrapper


def global_alias(aliases: Iterable[str], *, shortcuts: Iterable[str] = tuple()):
    global COMMANDS

    def wrapper(cmd):
        for shortcut in shortcuts:
            COMMANDS.add_router(shortcut, cmd, as_shortcut=True)
        for alias in aliases:
            COMMANDS.add_router(alias, cmd, as_alias=True)
        return cmd

    return wrapper


async def dispatch(client: main.BasilClient, msg: discord.Message):
    ctx = CommandContext(client, msg)
    summon_prefix: str = config.get().summon_prefix

    if config.get().maintenance_mode and not ctx.authorized:
        return

    # Check for summoning prefix:

    content: str = msg.content.strip()
    _prefixes = (
        summon_prefix.casefold(),
        "<@" + str(client.user.id) + ">",
        "<@!" + str(client.user.id) + ">",
    )

    for prefix in _prefixes:
        if content[: len(prefix)].casefold().startswith(prefix):
            content = content[len(prefix) :].strip()
            break
    else:
        # no summoning prefixes found
        return

    # Split and clean command arguments:

    args = []
    for m in re.finditer(CMD_REGEX, content):
        for group in m.groups():
            if group is not None:
                args.append(group)
                break

    if len(args) == 0:
        cmd = "help"
    else:
        cmd = args[0].lower().strip()

    # Route command:

    try:
        cmd_obj, final_args = COMMANDS.route(msg, (cmd,) + tuple(args[1:]))
    except CommandNotFoundError:
        return await ctx.reply(
            "I can't find any commands like that. Maybe try checking the general help section?",
        )
    except AmbiguousCommandError as e:
        cur_path = " ".join(e.args[0])
        lines = [
            "There's more than one command you could mean by that:".format(
                msg.author.id
            )
        ]

        for name, _ in e.args[1]:
            lines.append("-    `" + summon_prefix + cur_path + " " + name + "`")

        return await ctx.reply("\n".join(lines))
    except CommandNotAuthorizedError:
        return await ctx.reply("You aren't authorized to access that command.")

    # Shouldn't happen
    if cmd_obj is None:
        return

    # Execute command:

    try:
        return await cmd_obj(ctx, final_args)
    except Exception:
        await ctx.reply(
            "I seem to have run into an unexpected error while processing that command.\nIf you see any of my developers, could you ask them to check the logs? Sorry!"
        )
        raise


from . import snippet
from . import help_cmd
