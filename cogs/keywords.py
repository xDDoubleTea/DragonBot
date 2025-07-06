import discord
from discord import TextChannel, Interaction, app_commands
from discord.ext import commands
from typing import Literal, Optional, Union
from discord.ext.commands import Context, Cog, ExtensionNotFound
from discord.ext.commands.core import ExtensionFailed
from discord.ext.commands.errors import ExtensionAlreadyLoaded, ExtensionNotLoaded

from config.models import KeywordType
from core.keyword_manager import KeywordManager
from view.keyword_views import KeywordChange


class keyword(Cog):
    def __init__(self, bot: commands.Bot, keyword_manager: KeywordManager):
        self.bot = bot
        self.keyword_manager = keyword_manager

    @app_commands.command(name="add_keyword", description="加入關鍵字")
    @app_commands.describe(
        word="關鍵字",
        response="回覆",
        response_type="句首關鍵字意思是只檢查訊息開頭，句中關鍵字是檢查關鍵字是否出現在整個訊息中",
        channel="可觸發的頻道。未填則只會在客服頻道中觸發",
        customer_mention="在客服頻道中是否需要tag",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_keyword(
        self,
        interaction: Interaction,
        word: str,
        response: str,
        response_type: Literal["句首", "句中"],
        channel: Optional[TextChannel],
        in_ticket_only: bool = True,
        customer_mention: Optional[bool] = False,
    ):
        kw_data = []
        if self.has_word(word):
            v = KeywordChange(
                keyword=word,
                response=response,
                kw_type=KeywordType(response_type),
                in_ticket_only=in_ticket_only,
                keyword_manager=self.keyword_manager,
            )
            return await interaction.response.send_message(
                f"{word}已經在資料庫中,你想要做更動嗎?", view=v, ephemeral=True
            )

        else:
            new_key = 0
            if not channel:
                new_key = {
                    "word": word,
                    "response": response,
                    "type": response_type,
                    "channel": 0,
                    "customer_mention": customer_mention,
                }
            else:
                new_key = {
                    "word": word,
                    "response": response,
                    "type": response_type,
                    "channel": str(channel.id),
                    "customer_mention": customer_mention,
                }
            kw_data["keyword"].append(new_key)

            with open("keyword.json", "w") as file:
                json.dump(kw_data, file, indent=4)
            await interaction.response.send_message(f"{word}加入成功!", ephemeral=True)
            msg = await interaction.original_response()
            return await msg.add_reaction("✅")

    @add_keyword.error
    async def add_keyword_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                f"{interaction.user.mention}無權限使用此指令!", ephemeral=True
            )
            msg = await interaction.original_response()
            return await msg.add_reaction("❌")


async def setup(client):
    await client.add_cog(keyword(client))
