import discord
from discord import Message, Interaction, Embed
from discord.ui import Button, View, button
from typing import Any, Callable, Generic, Optional, List, TypeVar

from config.models import (
    BasePaginationMetaData,
    KeywordPaginationMetaData,
    PaginationViewButtonLayouts,
)

T_meta = TypeVar("T_meta", bound=BasePaginationMetaData)


class BasePaginationView(View, Generic[T_meta]):
    def __init__(
        self,
        *,
        timeout: Optional[int] = 180,
        metadata: T_meta,
        data: List[Any],
        format_page: Callable[[T_meta, List[Any]], Embed],
        items_per_page: int = 10,
        attached_message: Optional[Message] = None,
        ephemeral=True,
    ):
        super().__init__(timeout=timeout)
        self.metadata = metadata
        self.data = data
        self.format_page = format_page
        self.items_per_page = items_per_page
        self.attached_message = attached_message
        self.current_page = 0
        self.total_pages = (len(data) + items_per_page - 1) // items_per_page
        if self.total_pages == 0:
            self.total_pages = 1
        self.ephemeral = ephemeral

    def _get_embed(self) -> Embed:
        start = self.current_page * self.items_per_page
        end = min(start + self.items_per_page, len(self.data))
        return self.format_page(
            self.metadata,
            self.data[start:end],
        )
        # We actually don't have to take minimum because python handles it for us.
        # i.e., the upper bound is automatically set to min((self.current_page + 1) * self.items_per_page, len(self.data)) even if we don't explictly set it.

    async def send_initial_message(self, interaction: Interaction):
        """Sends the initial message and stores it for later edits."""
        self._update_button_states()
        embed = self._get_embed()
        await interaction.response.send_message(
            embed=embed, view=self, ephemeral=self.ephemeral
        )
        self.attached_message = await interaction.original_response()

    def _update_button_states(self):
        for item in self.children:
            if isinstance(item, Button):
                match item.custom_id:
                    case PaginationViewButtonLayouts.FIRST_PAGE.name:
                        item.disabled = self.current_page <= 0
                    case PaginationViewButtonLayouts.PREV_PAGE.name:
                        item.disabled = self.current_page <= 0
                    case PaginationViewButtonLayouts.PAGE_DISPLAY.name:
                        item.label = f"第{self.current_page + 1} / {self.total_pages}頁"
                    case PaginationViewButtonLayouts.NEXT_PAGE.name:
                        item.disabled = self.current_page >= self.total_pages - 1
                    case PaginationViewButtonLayouts.LAST_PAGE.name:
                        item.disabled = self.current_page >= self.total_pages - 1

    async def _update_page(self, interaction: Interaction):
        embed = self._get_embed()
        self._update_button_states()
        await interaction.response.send_message(embed=embed, ephemeral=self.ephemeral)

    @button(
        label="第一頁⏮️",
        style=discord.ButtonStyle.blurple,
        disabled=True,
        custom_id=PaginationViewButtonLayouts.FIRST_PAGE.name,
    )
    async def first_callback(self, interaction: Interaction, button: Button):
        self.current_page = 0
        await self._update_page(interaction)

    @button(
        label="上一頁◀️",
        style=discord.ButtonStyle.blurple,
        custom_id=PaginationViewButtonLayouts.PREV_PAGE.name,
    )
    async def pre_callback(self, interaction: Interaction, button: Button):
        self.current_page = max(self.current_page - 1, 0)
        await self._update_page(interaction)

    @button(
        label="第1/1頁",
        style=discord.ButtonStyle.blurple,
        custom_id=PaginationViewButtonLayouts.PAGE_DISPLAY.name,
    )
    async def page_display_btn(self, interaction: Interaction, button: Button):
        await interaction.response.defer(ephemeral=self.ephemeral)

    @button(
        label="下一頁▶️",
        style=discord.ButtonStyle.blurple,
        custom_id=PaginationViewButtonLayouts.NEXT_PAGE.name,
    )
    async def next_callback(self, interaction: Interaction, button: Button):
        self.current_page = min(self.current_page + 1, self.total_pages - 1)
        await self._update_page(interaction)

    @button(
        label="最後一頁⏭️",
        style=discord.ButtonStyle.blurple,
        custom_id=PaginationViewButtonLayouts.LAST_PAGE.name,
    )
    async def last_callback(self, interaction: Interaction, button: Button):
        self.current_page = self.total_pages - 1
        await self._update_page(interaction)

    async def on_timeout(self) -> None:
        if self.attached_message:
            try:
                for item in self.children:
                    if isinstance(item, Button):
                        if (
                            item.custom_id
                            == PaginationViewButtonLayouts.PAGE_DISPLAY.name
                        ):
                            item.label = "已過期"
                        item.style = discord.ButtonStyle.grey
                        item.disabled = True
                await self.attached_message.edit(view=self)
            except discord.NotFound:
                return


class KeywordPaginationView(BasePaginationView[KeywordPaginationMetaData]):
    def __init__(
        self,
        *,
        timeout: Optional[int] = 180,
        metadata: KeywordPaginationMetaData,
        data: List[Any],
        format_page: Callable[[KeywordPaginationMetaData, List[Any]], Embed],
        items_per_page: int = 10,
        attached_message: Optional[Message] = None,
        ephemeral=True,
    ):
        super().__init__(
            timeout=timeout,
            metadata=metadata,
            data=data,
            format_page=format_page,
            items_per_page=items_per_page,
            attached_message=attached_message,
            ephemeral=ephemeral,
        )
