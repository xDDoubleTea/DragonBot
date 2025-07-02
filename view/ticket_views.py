import discord
from discord import Interaction, TextChannel
from discord.ui import View, button, Button

from core.ticket_manager import TicketManager
from config.constants import DS01, DISCORD_EMOJI
from core.exceptions import ChannelCreationFail


class TicketCreationView(View):
    def __init__(self, ticket_manager: TicketManager):
        self.ticket_manager = ticket_manager
        super().__init__(timeout=None)

    async def _handle_cnl_creation(self, interaction: Interaction, ticket_type: str):
        await interaction.response.send_message("建立新頻道中...", ephemeral=True)
        try:
            assert interaction.guild
            new_channel = await self.ticket_manager.create_channel(
                user=interaction.user,
                guild=interaction.guild,
                ticket_type=ticket_type,
                close_view=TicketCloseToggleView(self.ticket_manager),
            )
            if not new_channel:
                raise ChannelCreationFail("Failed creating channel.")
            msg = await interaction.original_response()
            return await msg.edit(content=f"建立了一個新頻道!{new_channel.mention}")
        except Exception as e:
            print("Error during ticket creation :", e)
            msg = await interaction.original_response()
            await msg.edit(content="發生錯誤，請再試一次！")

    @button(
        label="代購問題",
        style=discord.ButtonStyle.blurple,
        custom_id="代購",
        emoji=DS01,
    )
    async def pur_callback(self, interaction: Interaction, button: Button):
        assert button.custom_id
        await self._handle_cnl_creation(
            interaction=interaction, ticket_type=button.custom_id
        )

    @button(
        label="群組問題",
        style=discord.ButtonStyle.blurple,
        custom_id="群組",
        emoji=DISCORD_EMOJI,
    )
    async def guild_callback(self, interaction: Interaction, button: Button):
        assert button.custom_id
        await self._handle_cnl_creation(
            interaction=interaction, ticket_type=button.custom_id
        )

    @button(
        label="其他問題",
        style=discord.ButtonStyle.blurple,
        custom_id="其他",
        emoji="📩",
    )
    async def others_callback(self, interaction: Interaction, button: Button):
        assert button.custom_id
        await self._handle_cnl_creation(
            interaction=interaction, ticket_type=button.custom_id
        )


class TicketCloseToggleView(View):
    def __init__(self, ticket_manager: TicketManager):
        super().__init__(timeout=None)
        self.ticket_manager = ticket_manager

    @button(label="關閉頻道", style=discord.ButtonStyle.blurple)
    async def close_callback(self, interaction: Interaction, button: Button):
        assert (
            interaction.message
            and interaction.channel
            and isinstance(interaction.channel, TextChannel)
        )
        await interaction.message.edit(view=None)
        msg = interaction.message
        if msg.components is not None:
            await msg.edit(view=None)

        await interaction.response.send_message(
            content="你確定你想要關閉此頻道?",
            view=TicketCloseView(ticket_manager=self.ticket_manager),
        )


class TicketCloseView(View):
    def __init__(self, ticket_manager: TicketManager):
        super().__init__(timeout=None)
        self.ticket_manager = ticket_manager

    @button(label="關閉頻道", style=discord.ButtonStyle.red)
    async def close_callback(self, interaction: Interaction, button: Button):
        assert (
            interaction.message
            and interaction.channel
            and isinstance(interaction.channel, TextChannel)
        )
        await interaction.message.edit(view=None)
        msg = interaction.message
        if msg.components is not None:
            await msg.edit(view=None)
        # Actually close the channel
        await self.ticket_manager.close_channel(channel=interaction.channel)
        await interaction.response.send_message(content="頻道已關閉。接下來你想要？")

    @button(label="取消", style=discord.ButtonStyle.gray)
    async def cancel_callback(self, interaction: Interaction, button: Button):
        assert (
            interaction.message
            and interaction.channel
            and isinstance(interaction.channel, TextChannel)
        )
        await interaction.message.edit(view=TicketCloseToggleView(self.ticket_manager))
        await interaction.response.send_message(
            content="關閉頻道已取消。", ephemeral=True
        )
