from . import command, COMMANDS
from .router import (
    Command,
    CommandNotFoundError,
    AmbiguousCommandError,
    CommandNotAuthorizedError,
)
from .context import CommandContext
from .. import config

from typing import Tuple


async def specific_cmd_help(ctx: CommandContext, args: Tuple[str], _cmd: Command):
    summon_prefix: str = config.get().summon_prefix

    try:
        cmd, _ = COMMANDS.route(ctx.message, args)
        return await ctx.reply(cmd.help_text(ctx.authorized), ephemeral=False)
    except CommandNotFoundError:
        return await ctx.reply(
            "I can't find any commands like that. Maybe try checking the general help section?",
        )
    except AmbiguousCommandError as e:
        cur_path = " ".join(e.args[0])
        lines = ["There's more than one command you could mean by that:"]

        for name, _ in e.args[1]:
            lines.append("-    `" + summon_prefix + cur_path + " " + name + "`")
        return await ctx.reply("\n".join(lines), ephemeral=False)
    except CommandNotAuthorizedError:
        return await ctx.reply("You aren't authorized to access that command.")


@command("help")
async def help_cmd(ctx: CommandContext, args: Tuple[str], cmd: Command):
    """Get help with Basil's commands."""

    if len(args) > 0:
        return await specific_cmd_help(ctx, args, cmd)

    lines = [
        "**Basil Command List:**",
        "Commands must be prefixed with `{}`.".format(config.get().summon_prefix),
    ]

    for cmd in COMMANDS.visible_subrouters(ctx.authorized):
        lines.append("    " + cmd.summary_entry())

    return await ctx.reply("\n".join(lines), ephemeral=False)
