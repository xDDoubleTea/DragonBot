import discord
from typing import List, Dict
from discord import Interaction, TextChannel
from discord.ui import Modal, View, button, Button, TextInput
import re
import yaml
from config.models import CloseMessageType, TicketStatus, TicketType
from core.ticket_manager import TicketManager
from config.constants import DS01, DISCORD_EMOJI
from core.exceptions import ChannelCreationFail
from utils.embed_utils import add_std_footer, create_themed_embed


class ParseError(Exception):
    pass


class SetBusinessHoursModal(Modal):
    def __init__(self):
        super().__init__(title="設定營業時間")
        self.business_hour = TextInput(
            label="設置營業時間",
            style=discord.TextStyle.long,
            placeholder="格式：開始時間(時:分),結束時間(時:分)，用半形冒號!程式會忽略空格\n第幾行就是星期幾\n範例：\n12:00,24:00\n...",
            required=True,
        )
        self.add_item(self.business_hour)

    def parse_input(self, input_val: str) -> List[Dict[str, str]]:
        temp = input_val.splitlines()
        if len(temp) != 7:
            raise ParseError
        try:
            temp = [val.split(",") for val in temp]
            day = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            st = ["start_time", "end_time"]
            out = []
            for i, val in enumerate(temp):
                cur_dict = {"day": day[i]}
                for j, s in enumerate(val):
                    get_match = re.findall(r" *(\d\d) *(:) *(\d\d) *", s)
                    # returns a list
                    if not get_match or len(get_match) > 1:
                        raise ParseError

                    cur_dict[st[j]] = "".join(get_match[0])
                out.append(cur_dict)
            return out

        except (IndexError, TypeError):
            raise ParseError

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            result = {"business_hours": self.parse_input(self.business_hour.value)}
            with open("config.yaml", "w") as file:
                yaml.safe_dump(result, file)
            await interaction.response.send_message(
                "成功設置營業時間！", ephemeral=True
            )
        except ParseError:
            await interaction.response.send_message(
                "輸入資料有誤，請檢查格式\n你的輸入是：\n" + self.business_hour.value,
                ephemeral=True,
            )
        except Exception as e:
            print(f"Error, {e}")
            await interaction.response.send_message(
                "發生未知錯誤，請通知開發者", ephemeral=True
            )


class QuestionModal(Modal):
    def __init__(self, ticket_manager: TicketManager, ticket_type: TicketType):
        super().__init__(
            title=f"問題表單，客服頻道種類：{ticket_type.value if ticket_type != TicketType.CUSTOM_PURCHASE else '自定義代購'}"
        )
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
                placeholder="遊戲或商品名稱",
                required=True,
            )
            self.add_item(self.item_purchase_input)
            self.description_input = TextInput(
                label="商品連結以及購買方法",
                style=discord.TextStyle.paragraph,
                placeholder="網站類請提供您要購買的商品連結、登入方式(如有)、價格(商品原本之價格)、商品原本之付款方式\n手遊、APP類 就是app名稱、登入方式、購買/付款方式(如跳轉google play付款)、價格",
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
        footer = discord.ui.TextDisplay("若濫用此功能可能會被停權！")
        self.add_item(self.description_input)
        self.add_item(footer)

    async def on_submit(self, interaction: Interaction) -> None:
        # Defer ephemerally. This shows a private "thinking" message
        # while we create the channel, preventing timeouts.
        await interaction.response.send_message(ephemeral=True, content="處理中...")

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
            await interaction.edit_original_response(
                content=f"已將問題描述傳送至客服頻道：{new_channel.mention}"
            )

        except Exception as e:
            print(f"Error during modal ticket creation: {e}")
            await interaction.followup.send(
                "❌ 建立頻道時發生錯誤，請稍後再試一次！", ephemeral=True
            )


class TicketCreationView(View):
    def __init__(self, ticket_manager: TicketManager):
        self.ticket_manager = ticket_manager
        super().__init__(timeout=None)

    @button(
        label="代購問題",
        style=discord.ButtonStyle.blurple,
        custom_id=TicketType.PURCHASE.value,
        emoji=DS01,
    )
    async def pur_callback(self, interaction: Interaction, button: Button):
        assert button.custom_id
        modal = QuestionModal(
            ticket_manager=self.ticket_manager, ticket_type=TicketType(button.custom_id)
        )
        await interaction.response.send_modal(modal)

    @button(
        label="🛒自定義代購",
        style=discord.ButtonStyle.blurple,
        custom_id=TicketType.CUSTOM_PURCHASE.value,
    )
    async def custom_order_callback(self, interaction: Interaction, button: Button):
        assert button.custom_id
        modal = QuestionModal(
            ticket_manager=self.ticket_manager, ticket_type=TicketType(button.custom_id)
        )
        await interaction.response.send_modal(modal)

    @button(
        label="群組問題",
        style=discord.ButtonStyle.blurple,
        custom_id=TicketType.GUILD.value,
        emoji=DISCORD_EMOJI,
    )
    async def guild_callback(self, interaction: Interaction, button: Button):
        assert button.custom_id
        modal = QuestionModal(
            ticket_manager=self.ticket_manager, ticket_type=TicketType(button.custom_id)
        )
        await interaction.response.send_modal(modal)

    # @button(
    #     label="其他問題",
    #     style=discord.ButtonStyle.blurple,
    #     custom_id=TicketType.OTHERS.value,
    #     emoji="📩",
    # )
    # async def others_callback(self, interaction: Interaction, button: Button):
    #     assert button.custom_id
    #     modal = QuestionModal(
    #         ticket_manager=self.ticket_manager, ticket_type=TicketType(button.custom_id)
    #     )
    #     await interaction.response.send_modal(modal)


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
        resp = await interaction.response.send_message(
            content="你確定你想要關閉此頻道?",
            view=TicketCloseView(ticket_manager=self.ticket_manager),
        )
        assert resp.message_id
        ticket = await self.ticket_manager.get_ticket(channel_id=interaction.channel_id)
        assert ticket
        # This button can only be inside a ticket channel
        if ticket.status in {TicketStatus.OPEN, TicketStatus.IN_PROGRESS}:
            await self.ticket_manager.set_ticket_status(
                ticket=ticket, new_status=TicketStatus.RESOLVED
            )
        await self.ticket_manager.set_close_msg_id(
            channel_id=interaction.channel.id,
            close_msg_id=resp.message_id,
            close_msg_type=CloseMessageType.CLOSE,
        )


class TicketCloseView(View):
    def __init__(self, ticket_manager: TicketManager):
        super().__init__(timeout=None)
        self.ticket_manager = ticket_manager

    @button(label="關閉頻道", style=discord.ButtonStyle.red)
    async def close_callback(self, interaction: Interaction, button: Button):
        try:
            assert (
                interaction.message
                and interaction.channel
                and isinstance(interaction.channel, TextChannel)
            )
            await interaction.response.send_message(
                content="正在生成頻道紀錄以及傳送回饋單給顧客..."
            )
            await interaction.message.edit(view=None)
            # Actually close the channel
            await self.ticket_manager.close_ticket(
                channel=interaction.channel, client=interaction.client
            )
            view = TicketAfterClose(ticket_manager=self.ticket_manager)
            # This saves an api call, which is perfect.
            msg = await interaction.edit_original_response(
                content=f"頻道已被{interaction.user.mention}關閉。接下來你想要？",
                view=view,
            )
            await self.ticket_manager.set_close_msg_id(
                channel_id=interaction.channel.id,
                close_msg_id=msg.id,
                close_msg_type=CloseMessageType.AFTER_CLOSE,
            )
        except Exception as e:
            print("Error: ", e)
            try:
                await interaction.edit_original_response(
                    content="關閉頻道時發生錯誤，請稍後再試。"
                )
            except (discord.errors.NotFound, discord.errors.Forbidden):
                pass

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
        ticket = await self.ticket_manager.get_ticket(channel_id=interaction.channel_id)
        assert ticket
        if ticket.status == TicketStatus.RESOLVED:
            await self.ticket_manager.set_ticket_status(
                ticket=ticket, new_status=TicketStatus.IN_PROGRESS
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
