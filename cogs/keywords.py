import discord
from discord import (
    DMChannel,
    TextChannel,
    Interaction,
    app_commands,
    Message,
    Embed,
)
from discord.ext import commands
from typing import Literal, Optional, List
from discord.ext.commands import Cog

from config.constants import THEME_COLOR
from config.models import (
    AddRemove,
    boolean_to_str,
    Keyword,
    KeywordType,
    KeywordPaginationMetaData,
)
from core.keyword_manager import KeywordManager
from core.ticket_manager import TicketManager
from main import DragonBot
from utils import embed_utils
from view.keyword_views import KeywordChange, KeywordChangeModal
from view.pagination_view import KeywordPaginationView


class KeywordCog(Cog):
    def __init__(
        self,
        bot: commands.Bot,
        keyword_manager: KeywordManager,
        ticket_manager: TicketManager,
    ):
        self.bot = bot
        self.keyword_manager = keyword_manager
        self.ticket_manger = ticket_manager

    async def _get_response(self, keyword: Keyword, channel_id: int) -> str:
        """
        Private helper function to correctly generate the response.
        """
        resp = keyword.response
        ticket_check = await self.ticket_manger.get_ticket(channel_id=channel_id)
        if keyword.mention_participants and ticket_check:
            member_list = await self.ticket_manger.get_ticket_participants_member(
                ticket_id=ticket_check.db_id
            )
            if member_list:
                resp += ", ".join([member.mention for member in member_list])
        return resp

    async def auto_complete_keyword(self, interaction: Interaction, current: str):
        """
        Auto complete function of the trigger parameter in the slash commands to improve UX
        """
        if not interaction.guild:
            return []
        keywords = self.keyword_manager.get_all_keywords_in_guild(interaction.guild.id)
        return [
            app_commands.Choice(name=kw.trigger, value=kw.trigger)
            for kw in keywords.values()
            if current.lower() in kw.trigger.lower()
        ]

    @Cog.listener()
    async def on_message(self, message: Message):
        if (
            not message.guild
            or message.author.bot
            or not isinstance(message.channel, TextChannel)
        ):
            return
        all_keywords = self.keyword_manager.get_all_keywords_in_guild(message.guild.id)
        for trigger, keyword in all_keywords.items():
            if not keyword.is_allowed_in(
                channel_id=message.channel.id,
                is_ticket_channel=await self.ticket_manger.is_ticket_channel(
                    channel_id=message.channel.id
                ),
            ):
                continue

            if (
                message.content.startswith(trigger)
                and keyword.kw_type.name == KeywordType.MATCH_START.name
            ):
                await message.channel.send(
                    await self._get_response(
                        keyword=keyword, channel_id=message.channel.id
                    )
                )
            elif (
                trigger in message.content
                and keyword.kw_type.name == KeywordType.IS_SUBSTR.name
            ):
                await message.channel.send(
                    await self._get_response(
                        keyword=keyword, channel_id=message.channel.id
                    )
                )

    @app_commands.command(name="add_keyword", description="加入關鍵字")
    @app_commands.describe(
        trigger="關鍵字",
        response="回覆",
        response_type="句首關鍵字意思是只檢查訊息開頭，句中關鍵字是檢查關鍵字是否出現在整個訊息中",
        channel="可觸發的頻道。未填則只會在客服頻道中觸發",
        in_ticket_only="是否只在客服頻道中觸發，預設為是",
        mention_participants="在客服頻道中是否需要tag，預設為是",
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
        mention_participants: bool = True,
    ):
        """
        App command that adds a keyword to the cache and the database, sends modal for editing if the keyword already exists.
        Do not directly call this function.
        """
        if not interaction.guild:
            return await interaction.response.send_message("此指令只能在伺服器中使用！")
        kw_data = self.keyword_manager.get_keyword_by_trigger(
            trigger=trigger, guild_id=interaction.guild.id
        )
        if kw_data:
            keyword = Keyword(
                id=kw_data.id,
                trigger=kw_data.trigger,
                response=response,
                kw_type=KeywordType(response_type),
                guild_id=interaction.guild.id,
                in_ticket_only=in_ticket_only,
                mention_participants=mention_participants,
            )
            if channel:
                keyword.allowed_channel_ids.append(channel.id)
            else:
                keyword.allowed_channel_ids = kw_data.allowed_channel_ids
            v = KeywordChange(
                keyword=kw_data,
                new_keyword=keyword,
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
                mention_participants=mention_participants,
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
    @app_commands.describe(trigger="關鍵字")
    @app_commands.autocomplete(trigger=auto_complete_keyword)
    async def remove_keyword(self, interaction: Interaction, trigger: str):
        if not interaction.guild:
            return await interaction.response.send_message("此指令只能在伺服器中使用！")
        try:
            was_deleted = await self.keyword_manager.delete_keyword(
                trigger=trigger, guild_id=interaction.guild.id
            )
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

    @app_commands.command(name="keyword_edit", description="編輯關鍵字")
    @app_commands.describe(
        trigger="關鍵字",
        response="回覆",
        response_type="句首關鍵字意思是只檢查訊息開頭，句中關鍵字是檢查關鍵字是否出現在整個訊息中",
        in_ticket_only="是否只在客服頻道中觸發，預設為是",
        mention_participants="在客服頻道中是否需要tag，預設為是",
    )
    @app_commands.autocomplete(trigger=auto_complete_keyword)
    @app_commands.checks.has_permissions(administrator=True)
    async def keyword_edit(
        self,
        interaction: Interaction,
        trigger: str,
        response: Optional[str],
        response_type: Optional[Literal["句首", "句中"]],
        in_ticket_only: bool = True,
        mention_participants: bool = True,
    ):
        if not interaction.guild:
            return await interaction.response.send_message("此指令只能在伺服器中使用！")
        kw_data = self.keyword_manager.get_keyword_by_trigger(
            trigger=trigger, guild_id=interaction.guild.id
        )
        if not kw_data:
            return await interaction.response.send_message(
                f"關鍵字 {trigger} 不存在！", ephemeral=True
            )
        keyword = Keyword(
            id=kw_data.id,
            trigger=kw_data.trigger,
            response=response or kw_data.response,
            kw_type=KeywordType(response_type or kw_data.kw_type.value),
            guild_id=interaction.guild.id,
            in_ticket_only=in_ticket_only,
            mention_participants=mention_participants,
        )

        await interaction.response.send_modal(
            KeywordChangeModal(
                keyword=kw_data,
                new_keyword=keyword,
                keyword_manager=self.keyword_manager,
            )
        )

    def format_keyword_embed(
        self, keyword_metadata: KeywordPaginationMetaData, keywords_list: List[Keyword]
    ) -> Embed:
        embed = embed_utils.create_themed_embed(
            title="關鍵字列表",
            description=f"{keyword_metadata.guild_name}的關鍵字列表",
            client=keyword_metadata.client,
        )
        for keyword in keywords_list:
            embed.add_field(
                name=f"**關鍵字**：{keyword.trigger}",
                value=f"""
                回覆：{keyword.response}，類型：{keyword.kw_type.value}，只在客服頻道中觸發：{boolean_to_str(keyword.in_ticket_only)}，在客服頻道中tag客戶：{boolean_to_str(keyword.mention_participants)}
                可觸發頻道：{", ".join(map(lambda cnl: cnl.mention, keyword_metadata.keyword_channel_obj.get(keyword.trigger, []))) if not keyword.in_ticket_only else "只在客服頻道中觸發"}""",
                inline=False,
            )
        return embed

    @app_commands.command(name="keyword_list", description="關鍵字列表")
    @app_commands.checks.has_permissions(administrator=True)
    async def keyword_list(self, interaction: Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("此指令只能在伺服器中使用！")
        kw_dict = self.keyword_manager.get_all_keywords_in_guild(interaction.guild.id)
        guild = interaction.guild
        channel = interaction.channel
        user = interaction.user
        if not channel or isinstance(channel, DMChannel):
            return await interaction.response.send_message("此指令只能在伺服器中使用！")
        keyword_metadata = KeywordPaginationMetaData(
            guild_name=guild.name,
            guild_id=guild.id,
            channel_name=channel.name or "No name",
            channel_id=channel.id,
            user_name=user.name,
            user_id=user.id,
            client=interaction.client,
            theme_color=THEME_COLOR,
            guild=guild,
            keyword_channel_obj={
                trigger: self.keyword_manager.get_keyword_channels_obj(
                    trigger=trigger, guild=guild
                )
                for trigger in kw_dict.keys()
            },
        )
        view = KeywordPaginationView(
            metadata=keyword_metadata,
            data=[kw for kw in kw_dict.values()],
            format_page=self.format_keyword_embed,
        )
        await view.send_initial_message(interaction)

    @app_commands.command(
        name="keyword_edit_channel", description="編輯關鍵字可觸發頻道"
    )
    @app_commands.describe(
        trigger="關鍵字",
        channel="可觸發的頻道。未填則只會在客服頻道中觸發",
    )
    @app_commands.autocomplete(trigger=auto_complete_keyword)
    @app_commands.checks.has_permissions(administrator=True)
    async def keyword_edit_channel(
        self,
        interaction: Interaction,
        trigger: str,
        channel: TextChannel,
        add_or_remove: Optional[Literal["加入", "移除"]],
    ):
        if not interaction.guild:
            return await interaction.response.send_message("此指令只能在伺服器中使用！")
        kw_data = self.keyword_manager.get_keyword_by_trigger(
            trigger=trigger, guild_id=interaction.guild.id
        )
        if not kw_data:
            return await interaction.response.send_message(
                f"關鍵字 {trigger} 不存在！", ephemeral=True
            )
        addremove = AddRemove(add_or_remove) if add_or_remove else None
        if addremove == AddRemove.ADD:
            await self.keyword_manager.append_keyword_channels(
                trigger=trigger,
                channel_ids=[channel.id],
                guild_id=interaction.guild.id,
            )
        elif addremove == AddRemove.REMOVE:
            await self.keyword_manager.remove_keyword_channels(
                trigger=trigger,
                channel_ids=[channel.id],
                guild_id=interaction.guild.id,
            )
        await interaction.response.send_message(
            f"{addremove.value if addremove else '更新'}關鍵字 {trigger} 的頻道成功!",
            ephemeral=True,
        )


async def setup(client: DragonBot):
    await client.add_cog(
        KeywordCog(
            bot=client,
            keyword_manager=client.keyword_manager,
            ticket_manager=client.ticket_manager,
        )
    )
