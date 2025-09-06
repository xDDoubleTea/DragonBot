from discord import (
    DMChannel,
    Guild,
    Interaction,
    Member,
    TextChannel,
    User,
    Message,
)
import discord
import io
import random
from discord.app_commands import CommandOnCooldown, MissingRole
from discord.app_commands.errors import AppCommandError, MissingPermissions
from discord.ext import commands
from discord.ext.commands import Cog
from discord.ext.commands.errors import ChannelNotFound
from discord.ext.commands.hybrid import app_commands
from discord.message import PartialMessage
from config.canned_response import ReplyKeys
from config.constants import (
    My_user_id,
    ticket_system_main_message,
    cus_service_role_id,
    cmd_channel_id,
    ericdragon_user_id,
    epic_dragon_role_id,
    admin_role_id,
    rare_dragon_role_id,
    app_id,
)
from config.models import (
    CloseMessageType,
    FeedbackPromptMessageType,
    PanelMessageData,
    TicketStatus,
)
from config.canned_response import CANNED_RESPONSES
from core.exceptions import ChannelNotTicket, NoParticipants
from core.feedback_manager import FeedbackManager
from core.ticket_manager import TicketManager
from core.ticket_panel_manager import TicketPanelManager
from utils.embed_utils import create_themed_embed
from view.feedback_views import FeedBackSystem, WordSelection
from view.ticket_views import (
    TicketAfterClose,
    TicketCloseToggleView,
    TicketCloseView,
    TicketCreationView,
)
from typing import List, Union, Optional, Dict
from utils.transformers import CannedResponseTransformer
from utils.discord_utils import (
    try_get_channel_by_bot,
    try_get_message,
    try_get_channel,
    try_get_guild,
    try_get_role,
    try_get_user,
)


class TicketsCog(Cog):
    ticket_operations = app_commands.Group(
        name="ticket_operations",
        description="Actions to act on ticket.",
    )

    def __init__(
        self,
        bot: commands.Bot,
        ticket_manager: TicketManager,
        ticket_panel_manager: TicketPanelManager,
        feedback_manager: FeedbackManager,
    ):
        self.bot = bot
        self.ticket_manager = ticket_manager
        self.ticket_panel_manager = ticket_panel_manager
        self.feedback_manager = feedback_manager
        self.panel_messages: Dict[int, PanelMessageData] = (
            self.ticket_panel_manager.ticket_panels
        )

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: AppCommandError
    ):
        """A global error handler for all commands in this cog."""
        if isinstance(error, MissingPermissions):
            await interaction.response.send_message(
                "你不是管理員，沒有權限使用此指令！", ephemeral=True
            )
        # Handle cases where the interaction has already been responded to
        elif isinstance(error, discord.errors.InteractionResponded):
            await interaction.followup.send(
                "發生了一個內部錯誤，但已成功回覆。", ephemeral=True
            )
        elif isinstance(error, MissingRole):
            await interaction.response.send_message(
                "只有客服人員才能使用此指令！", ephemeral=True
            )
        elif isinstance(error, CommandOnCooldown):
            await interaction.response.send_message(
                f"這個指令有冷卻時間，請稍等{round(error.retry_after, 1)}秒後再試",
                ephemeral=True,
            )
        else:
            # For other errors, you can log them or send a generic message
            print(f"An unhandled error occurred in RoleRequest cog: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"發生未知的錯誤: {error}", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"發生未知的錯誤: {error}", ephemeral=True
                )

    async def restore_feedback_prompt_view(self):
        print("Restoring feedback prompts.")
        prompts = await self.feedback_manager.get_all_feedback_prompts()
        if not prompts:
            print("Nothing to restore...Skipping")
            return
        for prompt in prompts:
            user = await try_get_user(bot=self.bot, user_id=prompt.user_id)
            if not user:
                print(f"User with id {prompt.user_id} not found, skipping.")
                await self.feedback_manager.remove_user_feedback_prompt(
                    user_id=prompt.user_id,
                    ticket_id=prompt.ticket_id,
                    guild_id=prompt.guild_id,
                )
                continue
            dm_channel = await try_get_channel_by_bot(
                bot=self.bot, channel_id=prompt.channel_id
            )

            if not dm_channel:
                print(
                    "User has no dm channel associated with the bot, maybe it has been deleted by user, skipping."
                )
                await self.feedback_manager.remove_user_feedback_prompt(
                    user_id=prompt.user_id,
                    ticket_id=prompt.ticket_id,
                    guild_id=prompt.guild_id,
                )
                continue
            assert isinstance(dm_channel, DMChannel)
            message = await try_get_message(
                channel=dm_channel, message_id=prompt.message_id
            )
            if not message:
                await self.feedback_manager.remove_user_feedback_prompt(
                    user_id=prompt.user_id,
                    ticket_id=prompt.ticket_id,
                    guild_id=prompt.guild_id,
                )
                print(
                    f"Message with ID {prompt.message_id} was not found in the dm channel, this is unexpected, skipping for now."
                )
                continue
            try:
                if prompt.message_type == FeedbackPromptMessageType.RATING:
                    print(
                        f"Restoring rating buttons for {user.name} with ticket id {prompt.ticket_id}."
                    )
                    view = FeedBackSystem(
                        user_id=prompt.user_id,
                        ticket_id=prompt.ticket_id,
                        guild_id=prompt.guild_id,
                        feedback_manager=self.feedback_manager,
                    )
                    view.message = await message.edit(view=view)
                elif prompt.message_type == FeedbackPromptMessageType.SELECT:
                    print(
                        f"Restoring drop down menu for {user.name} with ticket id {prompt.ticket_id}."
                    )

                    view = WordSelection(
                        user_id=prompt.user_id,
                        ticket_id=prompt.ticket_id,
                        guild_id=prompt.guild_id,
                        feedback_manager=self.feedback_manager,
                    )
                    view.message = await message.edit(view=view)
            except discord.errors.NotFound:
                print("That message was not found.")
                pass
        print("Done!")

    @Cog.listener(name="on_ready")
    async def on_ready(self):
        await self.restore_ticket_panel()
        await self.restore_close_buttons()
        await self.restore_feedback_prompt_view()

    async def _try_get_guild(
        self,
        guild_id: int,
    ) -> Optional[Guild]:
        """
        Attempts to get a channel by ID from the guild, falling back to fetching it if not found.
        """
        return await try_get_guild(self.bot, guild_id=guild_id)

    @staticmethod
    def _admin_mentioned(message: Message) -> bool:
        return bool(
            (len(message.raw_mentions) or len(message.raw_role_mentions))
            and (
                cus_service_role_id in message.raw_role_mentions
                or app_id in message.raw_mentions
                or ericdragon_user_id in message.raw_mentions
                or My_user_id in message.raw_mentions
                or admin_role_id in message.raw_role_mentions
                or epic_dragon_role_id in message.raw_role_mentions
                or rare_dragon_role_id in message.raw_role_mentions
            )
        )

    async def restore_ticket_panel(self):
        all_panel_messages = (
            await self.ticket_panel_manager.load_ticket_panel_messages()
        )
        for message in all_panel_messages:
            view = TicketCreationView(ticket_manager=self.ticket_manager)
            try:
                await message.edit(view=view)
            except discord.errors.NotFound:
                print("The message might have been deleted.")
                assert message.channel.guild
                await self.ticket_panel_manager.delete_panel_by_guild_id(
                    guild_id=message.channel.guild.id,
                )
            except Exception as e:
                print(e)

        print("Done!")

    async def restore_close_buttons(self):
        print("Restoring all close buttons...")
        all_tickets = await self.ticket_manager.database_manager.select(
            table_name="tickets"
        )
        if not all_tickets:
            print("No tickets found in database, skipping...")
            return
        assert isinstance(all_tickets, list)
        close_view: List[
            Union[
                type[TicketCloseToggleView],
                type[TicketCloseView],
                type[TicketAfterClose],
            ]
        ] = [TicketCloseToggleView, TicketCloseView, TicketAfterClose]
        deleted_tickets_id = []
        for ticket in all_tickets:
            ticket = await self.ticket_manager.get_ticket(ticket_id=ticket["id"])
            assert ticket
            close_msg_id = ticket.close_msg_id
            close_msg_type = ticket.close_msg_type
            guild_id = ticket.guild_id
            guild = await self._try_get_guild(guild_id=guild_id)
            if not guild:
                print(f"Could not find the guild with guild id {guild_id}, skipping...")
                continue
            channel_id = ticket.channel_id
            channel = await try_get_channel(guild=guild, channel_id=channel_id)
            if not channel or not isinstance(channel, TextChannel):
                print(
                    f"Could not find the channel with id {channel_id}, deleting ticket {ticket.db_id} from database."
                )
                await self.ticket_manager.database_manager.delete(
                    table_name="tickets", criteria={"id": ticket.db_id}
                )
                deleted_tickets_id.append(ticket.db_id)
                continue
            try:
                message = await channel.fetch_message(close_msg_id)
                print(f"Restoring close buttons in ticket with id {ticket.db_id}")
                view = close_view[CloseMessageType(close_msg_type)](
                    ticket_manager=self.ticket_manager,
                )
                await message.edit(view=view)
                print(f"Setting channel name for ticket with id {ticket.db_id}")
                await self.ticket_manager.set_ticket_status(
                    ticket=ticket,
                    new_status=ticket.status,
                )
            except discord.errors.NotFound:
                print(
                    f"Could not find the closing message with id {close_msg_id}. Resending the close button message."
                )
                # TODO: Send new close button message
            except Exception as e:
                print("Error: ", e)
        if deleted_tickets_id:
            await self.ticket_manager.database_manager.delete(
                table_name="tickets", criteria={"id": deleted_tickets_id}
            )
        print("Done!")

    @Cog.listener(name="on_message")
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        ticket = await self.ticket_manager.get_ticket(channel_id=message.channel.id)
        if not ticket:
            # We don't care about the message sent outside of tickets.
            return

        assert (
            message.guild
            and isinstance(message.channel, TextChannel)
            and isinstance(message.author, Member)
        )
        # Because ticket is a TextChannel in a Guild, AssertionError won't be raised
        cus_service_role = message.guild.get_role(cus_service_role_id)
        if (
            ticket.status == TicketStatus.OPEN
            and cus_service_role in message.author.roles
        ):
            await self.ticket_manager.set_ticket_status(
                ticket=ticket, new_status=TicketStatus.IN_PROGRESS
            )
        if self._admin_mentioned(message=message):
            await message.channel.send(
                "你好！我們已收到你的訊息，感謝你與我們聯繫。待上線後將會回答您的問題~"
            )

    @Cog.listener(name="on_message_edit")
    async def on_message_edit(self, before: Message, after: Message):
        if after.author.bot:
            return
        if self._admin_mentioned(message=after) and not self._admin_mentioned(
            message=before
        ):
            await after.channel.send(
                "你好！我們已收到你的訊息，感謝你與我們聯繫。待上線後將會回答您的問題~"
            )

    @Cog.listener(name="on_guild_channel_delete")
    async def on_guild_channel_delete(self, channel):
        if not isinstance(channel, TextChannel):
            return
        if panel := await self.ticket_panel_manager.get_panel(
            guild_id=channel.guild.id, channel_id=channel.id, message_id=None
        ):
            await self.ticket_panel_manager.delete_panel(panel_message_data=panel)

    @Cog.listener(name="on_message_delete")
    async def on_message_delete(self, message: Message):
        if not message.guild or not isinstance(message.channel, TextChannel):
            return
        if panel := await self.ticket_panel_manager.get_panel(
            guild_id=message.channel.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
        ):
            await self.ticket_panel_manager.delete_panel(panel_message_data=panel)

    @ticket_operations.command(
        name="close_ticket",
        description="將生成一個新的關閉頻道訊息，只能在客服頻道中且只能被客服人員使用。",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_role(cus_service_role_id)
    async def close_ticket(self, interaction: Interaction):
        try:
            assert isinstance(
                interaction.channel, TextChannel
            ) and await self.ticket_manager.is_ticket_channel(
                channel_id=interaction.channel.id
            )
            # First send the message
            await interaction.response.send_message(
                "新的關閉頻道按鈕",
                view=TicketCloseToggleView(self.ticket_manager),
            )
            # Delete the old close message, if any
            old_close_msg_id = await self.ticket_manager.get_close_msg_id(
                interaction.channel.id
            )
            if old_close_msg_id:
                if msg := await try_get_message(
                    channel=interaction.channel, message_id=old_close_msg_id
                ):
                    await msg.edit(view=None)

            # Set the new close message id to the response message
            msg = await interaction.original_response()
            assert msg
            await self.ticket_manager.set_close_msg_id(
                channel_id=interaction.channel.id,
                close_msg_id=msg.id,
                close_msg_type=CloseMessageType.CLOSE_TOGGLE,
            )

        except AssertionError:
            await interaction.response.send_message(
                "這裡不是客服頻道！", ephemeral=True
            )

    @ticket_operations.command(
        name="open_ticket",
        description="將生成一個新的開啟客服頻道之訊息。需要管理員權限才可使用。",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def open_ticket(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        if not interaction.guild:
            return await interaction.followup.send(
                content="Please try again.", ephemeral=True
            )
        cus_service_role = await try_get_role(
            guild=interaction.guild, role_id=cus_service_role_id
        )
        cmd_channel = await try_get_channel(
            guild=interaction.guild, channel_id=cmd_channel_id
        )
        if not cus_service_role or not cmd_channel:
            return await interaction.followup.send(
                content="Please try again.", ephemeral=True
            )
        if not isinstance(interaction.channel, TextChannel):
            return await interaction.followup.send(
                "You should put this message in a text channel.", ephemeral=True
            )
        try:
            if panel := await self.ticket_panel_manager.get_panel(
                guild_id=interaction.guild.id,
                channel_id=None,
                message_id=None,
            ):
                print(panel)
                panel_cnl = await try_get_channel(
                    guild=interaction.guild, channel_id=panel.channel_id
                )
                assert isinstance(panel_cnl, TextChannel)
                panel_msg = await try_get_message(
                    channel=panel_cnl, message_id=panel.message_id
                )
                assert isinstance(panel_msg, Message) or isinstance(
                    panel_msg, PartialMessage
                )
                return await interaction.followup.send(
                    content=f"There should only exist one open message for each guild. The url of the open message in your guild is {panel_msg.jump_url}",
                    ephemeral=True,
                )
        except AssertionError:
            # This means at least one of the values, panel_cnl or panel_msg is None, which means the message is not found.
            pass
            # If the message is not found, we can safely create a new one.
        # First we delete the record.
        # Since panel should be unique per guild, we can just delete by guild_id.
        await self.ticket_panel_manager.delete_panel_by_guild_id(
            guild_id=interaction.guild.id
        )

        view = TicketCreationView(ticket_manager=self.ticket_manager)
        embed = create_themed_embed(
            title="【DRAGON龍龍】客服專區",
            description="請點下方按鈕開啟客服頻道，點擊後會開啟一個只有您跟客服人員才看的到的私人頻道，即可至開啟的頻道傳送訊息，謝謝您。",
        )
        embed.url = "https://dragonshop.org/"
        embed.set_image(url="https://i.imgur.com/AgKFvBT.png")
        assert isinstance(cmd_channel, TextChannel)
        try:
            await interaction.followup.send(content="Done")
        except discord.errors.NotFound:
            pass
        except Exception as e:
            print(e)
        msg = await interaction.channel.send(
            content=ticket_system_main_message(
                role=cus_service_role, cmd_channel=cmd_channel
            ),
            view=view,
            embed=embed,
        )
        await self.ticket_panel_manager.insert_or_update_panel(
            panel_message_data=PanelMessageData(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                message_id=msg.id,
            )
        )

    @ticket_operations.command(
        name="add_participant",
        description="將使用者加入客服頻道，需要客服人員身份組才可使用。",
    )
    @app_commands.checks.has_role(cus_service_role_id)
    async def add_participant(self, interaction: Interaction, user: User):
        try:
            if user.bot:
                return await interaction.response.send_message(
                    content="你不能將機器人加入客服頻道。", ephemeral=True
                )
            assert interaction.channel
            member_updated = await self.ticket_manager.add_ticket_participants(
                interaction.channel.id, participants_id=[user.id]
            )
            return await interaction.response.send_message(
                content=f"成功將{user.mention}加入此頻道！"
                if member_updated
                else f"{user.mention}已經在此頻道中！",
                ephemeral=True,
            )
        except AssertionError:
            return await interaction.response.send_message(
                content="你不該看到此訊息的...", ephemeral=True
            )
        except ChannelNotTicket:
            return await interaction.response.send_message(
                content="此指令只能在客服頻道中使用。", ephemeral=True
            )

    @ticket_operations.command(name="archive_ticket", description="將客服頻道歸檔。")
    @app_commands.checks.has_role(cus_service_role_id)
    @app_commands.checks.cooldown(1, 600.0, key=lambda i: (i.guild_id, i.channel_id))
    @app_commands.guild_only()
    async def archive_ticket(self, interaction: Interaction):
        assert interaction.channel
        await interaction.response.defer(thinking=True)
        try:
            transcript_file, filename = await self.ticket_manager.archive_ticket(
                channel_id=interaction.channel.id
            )
            return await interaction.followup.send(
                "頻道紀錄",
                ephemeral=True,
                file=discord.File(
                    fp=io.BytesIO(transcript_file), filename=f"{filename}"
                ),
            )
        except ChannelNotTicket:
            return await interaction.response.send_message(
                "這裡不是客服頻道！", ephemeral=True
            )
        except ChannelNotFound as e:
            return await interaction.response.send_message(content=e)

    @ticket_operations.command(
        name="remove_participant",
        description="將使用者移出客服頻道，需要客服人員身份組才可使用。",
    )
    @app_commands.checks.has_role(cus_service_role_id)
    async def remove_participant(self, interaction: Interaction, user: User):
        try:
            if user.bot:
                return await interaction.response.send_message(
                    content="你不能將機器人從客服頻道中移除。", ephemeral=True
                )
            assert interaction.channel
            member_updated = await self.ticket_manager.remove_ticket_participants(
                interaction.channel.id, participants_id=[user.id]
            )
            return await interaction.response.send_message(
                content=f"成功將{user.mention}移出此頻道！"
                if member_updated
                else f"{user.mention}不在此頻道中！",
                ephemeral=True,
            )
        except AssertionError:
            return await interaction.response.send_message(
                content="你不該看到此訊息的...", ephemeral=True
            )
        except ChannelNotTicket:
            return await interaction.response.send_message(
                content="此指令只能在客服頻道中使用。", ephemeral=True
            )
        except NoParticipants:
            return await interaction.response.send_message(
                content="此客服頻道已經沒有客戶了，你在幹麻？？？", ephemeral=True
            )

    @ticket_operations.command(name="choose-抽獎", description="抽獎")
    @app_commands.guild_only()
    @app_commands.checks.has_role(cus_service_role_id)
    async def choose_sth(self, interaction: Interaction):
        if not isinstance(interaction.channel, TextChannel):
            return await interaction.response.send_message(
                "這裡不是客服頻道！", ephemeral=True
            )

        ticket = await self.ticket_manager.get_ticket(channel_id=interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message(
                "這裡不是客服頻道！", ephemeral=True
            )
        assert interaction.guild
        assert isinstance(interaction.user, Member)

        choices = {
            "麥當勞 大蛋捲冰淇淋電子券": 0.4,
            "50元購物金": 0.3,
            "100元購物金": 0.1,
            "Discord Nitro Basic一個月": 0.1,
            "Discord Nitro一個月": 0.09,
            "龍龍代購網600元以內商品任選一個": 0.01,
        }
        temp = [(choice, choices[choice] * 100) for choice in choices]

        res_list = random.sample(
            population=[ele[0] for ele in temp],
            counts=[int(ele[1]) for ele in temp],
            k=1,
        )
        result = res_list[0]
        members = await self.ticket_manager.get_ticket_participants_member(
            ticket_id=ticket.db_id
        )
        if not members:
            return await interaction.response.send_message(
                "Something is wrong...", ephemeral=True
            )
        members_mention = "".join([member.mention for member in members])
        return await interaction.response.send_message(
            f"{members_mention}恭喜您抽中**{result}**！"
        )

    @choose_sth.error
    async def choose_sth_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, MissingRole):
            return await interaction.response.send_message(
                "只有客服人員能夠使用此指令！", ephemeral=True
            )

    @app_commands.command(name="r", description="回覆指令(只有客服人員能夠使用)")
    @app_commands.checks.has_role(cus_service_role_id)
    async def r(
        self,
        interaction: Interaction,
        reply: app_commands.Transform[ReplyKeys, CannedResponseTransformer(ReplyKeys)],
    ):
        # check if in channel

        if not interaction.channel or not isinstance(interaction.channel, TextChannel):
            # The ticket channel must be a TextChannel because that's how it's coded.
            return await interaction.response.send_message(
                "這裡不是客服頻道！", ephemeral=True
            )

        ticket = await self.ticket_manager.get_ticket(channel_id=interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message(
                "這裡不是客服頻道！", ephemeral=True
            )
        # get customer id & tag stuff
        response_data = CANNED_RESPONSES.get(reply)
        if not response_data:
            return await interaction.response.send_message(
                "錯誤：找不到該回覆訊息。", ephemeral=True
            )
        final_response = response_data.text
        if response_data.mention_user:
            participants = await self.ticket_manager.get_ticket_participants_member(
                ticket_id=ticket.db_id
            )
            if not participants:
                return await interaction.response.send_message(
                    "這個客服頻道沒有客戶，非常詭異", ephemeral=True
                )
            final_response = f"""{", ".join(map(lambda participant: participant.mention, participants))} 
{final_response}"""

        await interaction.response.send_message(final_response)

        if reply in {ReplyKeys.CLOSE_PROMPT, ReplyKeys.DONE_PROCESS}:
            await self.ticket_manager.set_ticket_status(
                ticket=ticket, new_status=TicketStatus.RESOLVED
            )


async def setup(client):
    await client.add_cog(
        TicketsCog(
            bot=client,
            ticket_manager=client.ticket_manager,
            ticket_panel_manager=client.ticket_panel_manager,
            feedback_manager=client.feedback_manager,
        )
    )
