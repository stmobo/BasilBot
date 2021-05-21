from __future__ import annotations

import inspect
from typing import Optional, List, Tuple, Dict, Iterable, Any

from discord import Member

from . import Trie
from ..context import CommandContext
from ... import config


class CommandNotFoundError(Exception):
    pass


class AmbiguousCommandError(Exception):
    pass


class CommandNotAuthorizedError(Exception):
    pass


class CommandRouter(object):
    def __init__(
        self,
        name: str,
        authorized_only: bool = False,
        summary: Optional[str] = None,
        group: Optional[Any] = None,
        hidden: str = "never",
    ):
        self.name: str = name
        self.shortcuts: Dict[str, CommandRouter] = {}
        self.authorized_only: bool = authorized_only
        self.summary: Optional[str] = summary
        self.hidden = hidden
        self.group: Optional[Any] = group
        self.children = Trie()
        self.routers_list = []  # for fast iteration
        self.parent: Optional[CommandRouter] = None

    def add_router(
        self,
        name: str,
        child: CommandRouter,
        *,
        as_alias: bool = False,
        as_shortcut: bool = False,
    ):
        """Mount a child router entry under this CommandRouter.

        If `as_alias` is True, then the child router will not be added to the
        `routers_list`.
        This prevents commands that are being mounted under multiple names from
        being displayed multiple times in help text, for example.

        If `as_shortcut` is True, then the child router will be added to the
        `routers_list` as a shortcut mapping.

        Shortcut mappings take precedence over regular routes, but require an
        exact match when routing.
        In addition, shortcut mappings are never added to the `routers_list`.
        """

        if as_shortcut:
            if name in self.shortcuts:
                raise KeyError("shortcut mapping already exists for " + name)
            self.shortcuts[name] = child
        else:
            self.children.insert(name, child)

            if not as_alias:
                self.routers_list.append(child)

    def contains_exact_match(self, name: str) -> bool:
        name = name.casefold()
        return (name in self.shortcuts) or (name in self.children)

    def route(
        self,
        context: CommandContext,
        args: Tuple[str],
        cur_cmd_path: Tuple[str] = tuple(),
    ) -> Tuple[Command, Tuple[str]]:
        """Route a user command message to its final matching command.

        This will ultimately either return a Command and the arguments that
        should be passed to it, or raise an error.
        """

        if self.authorized_only and not context.authorized:
            if self.hidden == "unauthorized":
                raise CommandNotFoundError(cur_cmd_path)
            else:
                raise CommandNotAuthorizedError(cur_cmd_path, self)

        try:
            next_name: str = args[0].casefold()
        except IndexError:
            raise CommandNotFoundError(cur_cmd_path)

        next_cmd_path = cur_cmd_path + (next_name,)
        if next_name in self.shortcuts:
            candidates = [(next_name, self.shortcuts[next_name])]
        else:
            try:
                candidates = list(self.children.search(next_name))
            except KeyError:
                raise CommandNotFoundError(next_cmd_path)

        # If all possible candidates are the same thing, route there.
        # This automatically covers the case of len(candidates) == 1.
        v = candidates[0][1]
        if candidates[0][0] == next_name or all((kv[1] == v) for kv in candidates):
            return v.route(context, args[1:], next_cmd_path)
        else:
            # multiple possible candidates:
            raise AmbiguousCommandError(cur_cmd_path, candidates)

    def subrouters(self) -> List[CommandRouter]:
        return self.routers_list

    def visible_subrouters(self, authorized: bool) -> Iterable[CommandRouter]:
        if authorized:
            return filter(lambda r: r.hidden != "always", self.routers_list)
        else:
            return filter(
                lambda r: r.hidden != "always" and r.hidden != "unauthorized",
                self.routers_list,
            )

    def summary_entry(self) -> str:
        if self.summary is not None:
            return "`{}` - {}".format(self.name, self.summary)
        else:
            return "`{}` - No summary available.".format(self.name)


class Command(CommandRouter):
    def __init__(
        self,
        func,
        name: str,
        summary: Optional[str] = None,
        authorized_only: bool = False,
        group: Optional[Any] = None,
        parent_cmd_path: Tuple[str] = tuple(),
        needs_cmd_obj: bool = False,
        hidden: str = "never",
    ):
        if summary is None and func.__doc__ is not None:
            docstring = inspect.cleandoc(func.__doc__)
            if len(docstring) > 0:
                summary = docstring[: docstring.find("\n")]

        super().__init__(
            name,
            authorized_only=authorized_only,
            summary=summary,
            group=group,
            hidden=hidden,
        )
        self.func = func
        self.cmd_path = parent_cmd_path + (name,)
        self.needs_cmd_obj: bool = needs_cmd_obj

    def route(
        self,
        context: CommandContext,
        args: Tuple[str],
        cur_cmd_path: Tuple[str] = tuple(),
    ) -> Tuple[Command, Tuple[str]]:
        if self.authorized_only and not context.authorized:
            if self.hidden == "unauthorized":
                raise CommandNotFoundError(cur_cmd_path)
            else:
                raise CommandNotAuthorizedError(cur_cmd_path, self)

        cur_cmd_path = cur_cmd_path + (self.name,)
        if len(self.children) > 0 and len(args) > 0:
            try:
                return super().route(context, args, cur_cmd_path)
            except CommandNotFoundError:
                pass

        return (self, args)

    def subcommand(
        self,
        name: str,
        *,
        summary: Optional[str] = None,
        authorized_only: bool = False,
        shortcuts: Iterable[str] = tuple(),
        needs_cmd_obj: bool = False,
        hidden: str = "never",
        aliases: Iterable[str] = tuple(),
        group: Optional[Any] = None,
    ):
        """Add a subcommand to this command."""

        def wrapper(func):
            cmd = Command(
                func,
                name,
                summary=summary,
                authorized_only=authorized_only,
                parent_cmd_path=self.cmd_path,
                needs_cmd_obj=needs_cmd_obj,
                hidden=hidden,
                group=group,
            )

            self.add_router(name, cmd)

            for shortcut in shortcuts:
                self.add_router(shortcut, cmd, as_shortcut=True)

            for alias in aliases:
                self.add_router(alias, cmd, as_alias=True)

            return cmd

        return wrapper

    def help_text(self, authorized: bool = False) -> str:
        text: str = "`" + " ".join(self.cmd_path) + "` - "

        if self.func.__doc__ is not None:
            text += inspect.cleandoc(self.func.__doc__)
        elif self.summary is not None:
            text += self.summary
        else:
            text += "This command has neither help text, nor a summary."

        subrouters = list(self.visible_subrouters(authorized))
        if len(subrouters) > 0:
            text += "\n\n**Subcommands:**\n    "
            text += "\n    ".join(map(lambda cmd: cmd.summary_entry(), subrouters))

        return text

    def __call__(self, context: CommandContext, args: Tuple[str]):
        return self.func(context, args, self)
