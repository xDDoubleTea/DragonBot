import discord
from discord import Message, Interaction, Embed
from discord.ui import Button, View, button, select, Select
from typing import Any, Callable, Optional, List, Dict


class PaginationView(View):
    def __init__(
        self,
        *,
        timeout: Optional[int] = 180,
        data: List[Any],
        format_page: Callable[[Interaction, List[Any]], Embed],
        items_per_page: int = 10,
    ):
        super().__init__(timeout=timeout)
        self.data = data

    @button(label="上一頁◀️", style=discord.ButtonStyle.blurple)
    async def pre_callback(self, interaction: Interaction, button: Button):
        pass

    @button(label="下一頁▶️", style=discord.ButtonStyle.blurple)
    async def next_callback(self, interaction: Interaction, button: Button):
        pass
