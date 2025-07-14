import discord
from discord import Interaction, TextChannel
from discord.ui import Modal, View, button, Button, TextInput

from config.models import CloseMessageType, TicketType
from core.ticket_manager import TicketManager
from config.constants import DS01, DISCORD_EMOJI
from core.exceptions import ChannelCreationFail
from utils.embed_utils import add_std_footer, create_themed_embed


class QuestionModal(Modal):
    def __init__(self, ticket_manager: TicketManager, ticket_type: TicketType):
        super().__init__(title=f"問題表單，客服頻道種類：{ticket_type.value}")
        self.ticket_manager = ticket_manager
        self.ticket_type = ticket_type

        if self.ticket_type == TicketType.PURCHASE:
            self.order_id_input = TextInput(
                label="訂單編號（選填，若已經下單，可以填入訂單編號加快處理速度）",
                style=discord.TextStyle.short,
                placeholder="#25565",
                required=False,
            )
            self.add_item(self.order_id_input)
        elif self.ticket_type == TicketType.GUILD:
            self.guild_problem_input = TextInput(
                label="群組問題分類（選填，若有特定群組問題，可以填入）",
                style=discord.TextStyle.short,
                placeholder="例如：領獎/身分組/檢舉/問題回報...等",
                required=False,
            )
            self.add_item(self.guild_problem_input)
        elif self.ticket_type == TicketType.CUSTOM_PURCHASE:
            self.item_purchase_input = TextInput(
                label="想要代購的商品",
                style=discord.TextStyle.short,
                placeholder="遊戲點數",
                required=True,
            )
            self.add_item(self.item_purchase_input)
            self.description_input = TextInput(
                label="商品連結以及購買方法",
                style=discord.TextStyle.paragraph,
                placeholder="連結：...",
                required=True,
                max_length=1024,
            )
        if self.ticket_type != TicketType.CUSTOM_PURCHASE:
            self.description_input = TextInput(
                label="問題描述",
                style=discord.TextStyle.paragraph,
                placeholder="詳細說明遇到的問題",
                required=True,
                max_length=1500,
            )
        self.add_item(self.description_input)

    async def on_submit(self, interaction: Interaction) -> None:
        # Defer ephemerally. This shows a private "thinking" message
        # while we create the channel, preventing timeouts.
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            assert interaction.guild is not None

            # 1. Create the ticket channel.
            new_channel = await self.ticket_manager.create_ticket(
                user=interaction.user,
                guild=interaction.guild,
                ticket_type=self.ticket_type,
                close_view=TicketCloseToggleView(self.ticket_manager),
            )

            if not new_channel:
                raise ChannelCreationFail("Ticket manager failed to return a channel.")

            # 2. Send the user's question directly into the new channel.
            if self.ticket_type != TicketType.CUSTOM_PURCHASE:
                await new_channel.send(
                    content=f"**來自 {interaction.user.mention} 的問題：**\n>>> {self.description_input.value}"
                )
            else:
                embed = create_themed_embed(
                    title="自定義代購商品",
                    description=f"{interaction.user.mention}想要自定義代購商品",
                    client=interaction.client,
                )
                add_std_footer(embed=embed, client=interaction.client)
                embed.add_field(
                    name="商品名稱",
                    value=f"{self.item_purchase_input.value}",
                    inline=False,
                )
                embed.add_field(
                    name="購買連結與方法",
                    value=f"{self.description_input.value}",
                    inline=False,
                )
                await new_channel.send(embed=embed)

            if self.ticket_type == TicketType.PURCHASE and self.order_id_input.value:
                await new_channel.send(
                    content=f"**訂單編號**：`{self.order_id_input.value}`"
                )
            elif (
                self.ticket_type == TicketType.GUILD and self.guild_problem_input.value
            ):
                await new_channel.send(
                    content=f"**群組問題分類**：`{self.guild_problem_input.value}`"
                )

            # 3. Send a final, persistent confirmation to the user.
            await interaction.followup.send(
                f"已將問題描述傳送至客服頻道：{new_channel.mention}"
            )

        except Exception as e:
            print(f"Error during modal ticket creation: {e}")
            await interaction.followup.send("❌ 建立頻道時發生錯誤，請稍後再試一次！")


class TicketCreationView(View):
    def __init__(self, ticket_manager: TicketManager):
        self.ticket_manager = ticket_manager
        super().__init__(timeout=None)

    @button(
        label="代購問題",
        style=discord.ButtonStyle.blurple,
        custom_id="代購",
        emoji=DS01,
    )
    async def pur_callback(self, interaction: Interaction, button: Button):
        assert button.custom_id
        modal = QuestionModal(
            ticket_manager=self.ticket_manager, ticket_type=TicketType(button.custom_id)
        )
        await interaction.response.send_modal(modal)

    @button(
        label="群組問題",
        style=discord.ButtonStyle.blurple,
        custom_id="群組",
        emoji=DISCORD_EMOJI,
    )
    async def guild_callback(self, interaction: Interaction, button: Button):
        assert button.custom_id
        modal = QuestionModal(
            ticket_manager=self.ticket_manager, ticket_type=TicketType(button.custom_id)
        )
        await interaction.response.send_modal(modal)

    @button(
        label="🛪自定義代購",
        style=discord.ButtonStyle.blurple,
        custom_id="自定義代購",
    )
    async def custom_order_callback(self, interaction: Interaction, button: Button):
        assert button.custom_id
        modal = QuestionModal(
            ticket_manager=self.ticket_manager, ticket_type=TicketType(button.custom_id)
        )
        await interaction.response.send_modal(modal)

    @button(
        label="其他問題",
        style=discord.ButtonStyle.blurple,
        custom_id="其他",
        emoji="📩",
    )
    async def others_callback(self, interaction: Interaction, button: Button):
        assert button.custom_id
        modal = QuestionModal(
            ticket_manager=self.ticket_manager, ticket_type=TicketType(button.custom_id)
        )
        await interaction.response.send_modal(modal)


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
        msg = await interaction.original_response()
        await self.ticket_manager.set_close_msg_id(
            channel_id=interaction.channel.id,
            close_msg_id=msg.id,
            close_msg_type=CloseMessageType.CLOSE,
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
        await interaction.response.defer(thinking=True)
        await interaction.message.edit(view=None)
        # Actually close the channel
        try:
            await self.ticket_manager.close_ticket(
                channel=interaction.channel, client=interaction.client
            )
            view = TicketAfterClose(ticket_manager=self.ticket_manager)
            await interaction.followup.send(
                content=f"頻道已被{interaction.user.mention}關閉。接下來你想要？",
                view=view,
            )
            msg = await interaction.original_response()
            await self.ticket_manager.set_close_msg_id(
                channel_id=interaction.channel.id,
                close_msg_id=msg.id,
                close_msg_type=CloseMessageType.AFTER_CLOSE,
            )
        except Exception as e:
            print("Error: ", e)
            await interaction.followup.send(
                "關閉頻道時發生錯誤，請稍後再試。", ephemeral=True
            )

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
        await self.ticket_manager.set_close_msg_id(
            channel_id=interaction.channel.id,
            close_msg_id=interaction.message.id,
            close_msg_type=CloseMessageType.CLOSE_TOGGLE,
        )


class TicketAfterClose(View):
    def __init__(self, ticket_manager: TicketManager):
        super().__init__(timeout=None)
        self.ticket_manager = ticket_manager

    @button(label="刪除頻道", style=discord.ButtonStyle.red)
    async def del_callback(self, interaction: Interaction, button: Button):
        await interaction.response.defer(thinking=True)
        assert isinstance(interaction.channel, TextChannel)
        await self.ticket_manager.delete_ticket(channel=interaction.channel)

    @button(label="重新開啟頻道", style=discord.ButtonStyle.green)
    async def reopen_callback(self, interaction: Interaction, button: Button):
        await interaction.response.defer(thinking=True)
        assert isinstance(interaction.channel, TextChannel)
        await self.ticket_manager.reopen_ticket(channel=interaction.channel)
        await interaction.followup.send(
            "頻道已經被重新開啟！", view=TicketCloseToggleView(self.ticket_manager)
        )
        msg = await interaction.original_response()
        assert interaction.message
        await interaction.message.edit(view=None)
        await self.ticket_manager.set_close_msg_id(
            channel_id=interaction.channel.id,
            close_msg_id=msg.id,
            close_msg_type=CloseMessageType.CLOSE_TOGGLE,
        )
