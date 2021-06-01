from __future__ import annotations

import discord
from typing import Tuple, List

def get_member_names(
    client: discord.Client, user_id: int
) -> Tuple[List[str], str, str]:
    display_names = set()
    username = None
    discriminator = None

    for guild in client.guilds:
        member: discord.Member = guild.get_member(user_id)

        if member is None:
            continue

        display_names.add(member.display_name)
        username = member.name
        discriminator = member.discriminator

    return sorted(display_names), username, discriminator

