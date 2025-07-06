import discord
from discord import TextChannel, Interaction, app_commands, Message
from discord.ext import commands
from typing import Literal, Optional
from discord.ext.commands import Cog

from config.models import Keyword, KeywordType
from core.keyword_manager import KeywordManager
from view.keyword_views import KeywordChange


class keyword(Cog):
    def __init__(self, bot: commands.Bot, keyword_manager: KeywordManager):
        self.bot = bot
        self.keyword_manager = keyword_manager

    @Cog.listener()
    async def on_message(self, message: Message):
        pass

    @app_commands.command(name="add_keyword", description="加入關鍵字")
    @app_commands.describe(
        trigger="關鍵字",
        response="回覆",
        response_type="句首關鍵字意思是只檢查訊息開頭，句中關鍵字是檢查關鍵字是否出現在整個訊息中",
        channel="可觸發的頻道。未填則只會在客服頻道中觸發",
        in_ticket_only="是否只在客服頻道中觸發",
        customer_mention="在客服頻道中是否需要tag",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_keyword(
        self,
        interaction: Interaction,
        trigger: str,
        response: str,
        response_type: Literal["句首", "句中"],
        channel: Optional[TextChannel],
        in_ticket_only: bool = True,
        customer_mention: bool = False,
    ):
        if not interaction.guild:
            return await interaction.response.send_message("此指令只能在伺服器中使用！")
        kw_data = self.keyword_manager.get_keyword_by_trigger(trigger=trigger)
        if kw_data:
            keyword = Keyword(
                id=kw_data.id,
                trigger=kw_data.trigger,
                response=response,
                kw_type=KeywordType(response_type),
                guild_id=interaction.guild.id,
                in_ticket_only=in_ticket_only,
                customer_mention=customer_mention,
            )
            if channel:
                keyword.allowed_channel_ids.append(channel.id)
            else:
                keyword.allowed_channel_ids = kw_data.allowed_channel_ids
            v = KeywordChange(
                keyword=kw_data,
                keyword_manager=self.keyword_manager,
            )
            return await interaction.response.send_message(
                f"{trigger}已經在資料庫中,你想要做更動嗎?", view=v, ephemeral=True
            )
        try:
            keyword = await self.keyword_manager.create_keyword(
                trigger=trigger,
                response=response,
                kw_type=KeywordType(response_type),
                in_ticket_only=in_ticket_only,
                allowed_channel_ids=[channel.id] if channel else None,
                guild_id=interaction.guild.id,
            )
            if keyword:
                await interaction.response.send_message(
                    f"{trigger}加入成功!", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "連線到資料庫時發生錯誤，請稍後再試。", ephemeral=True
                )
        except Exception as e:
            return await interaction.response.send_message(
                f"Error: {e}", ephemeral=True
            )

    @add_keyword.error
    async def add_keyword_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                f"{interaction.user.mention}無權限使用此指令!", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"發生錯誤: {error}", ephemeral=True
            )

    @app_commands.command(name="remove_keyword", description="刪除關鍵字")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_keyword(self, interaction: Interaction, trigger: str):
        if not interaction.guild:
            return await interaction.response.send_message("此指令只能在伺服器中使用！")
        try:
            was_deleted = await self.keyword_manager.delete_keyword(trigger=trigger)
            if was_deleted:
                await interaction.response.send_message(
                    f"{trigger} 刪除成功!", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"資料庫中沒有關鍵字 {trigger}", ephemeral=True
                )
        except Exception as e:
            return await interaction.response.send_message(
                f"Error: {e}", ephemeral=True
            )

    @remove_keyword.error
    async def remove_keyword_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                f"{interaction.user.mention}無權限使用此指令!", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"發生錯誤: {error}", ephemeral=True
            )


async def setup(client):
    await client.add_cog(keyword(bot=client, keyword_manager=client.keyword_manager))
