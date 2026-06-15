from discord import Client, Embed

from utils.embed_utils import create_themed_embed


def giveaway_settings_to_embed(client: Client, giveaway_settings: dict) -> Embed:
    embed = create_themed_embed(title="抽獎設定", client=client)
    for key, val in giveaway_settings.items():
        embed.add_field(name=f"獎品：{key}", value=f"機率：{val}", inline=False)
    return embed
