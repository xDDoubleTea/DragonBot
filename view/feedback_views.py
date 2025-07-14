from typing import List, Union
from discord import (
    Client,
    Embed,
    Interaction,
    Member,
    SelectOption,
    TextChannel,
    TextStyle,
    ButtonStyle,
    User,
)
from discord.ui import TextInput, Modal, View, select, button, Button, Select
from config.constants import feedback_channel_id
from config.models import FeedbackEntry
from core.feedback_manager import FeedbackManager
from utils import embed_utils
from utils.discord_utils import try_get_channel_by_bot

words_options = [
    SelectOption(label="服務速度快速", emoji="✅", default=False),
    SelectOption(label="服務態度良好", emoji="✅", default=False),
    SelectOption(label="服務優質", emoji="✅", default=False),
]


class FeedbackModal(Modal):
    def __init__(
        self, ticket_id: int, guild_id: int, feedback_manager: FeedbackManager
    ):
        super().__init__(title="評語", timeout=None)
        self.ticket_id = ticket_id
        self.guild_id = guild_id
        self.feedback_manager = feedback_manager

    text = TextInput(
        label="評語",
        placeholder="服務速度快速",
        style=TextStyle.short,
        max_length=30,
    )

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        assert interaction.message
        await interaction.message.edit(view=None)
        await self.feedback_manager.update_feedback_message(
            ticket_id=self.ticket_id,
            guild_id=self.guild_id,
            customer_id=interaction.user.id,
            feedback_message=self.text.value,
        )
        channel = await try_get_channel_by_bot(
            bot=interaction.client, channel_id=feedback_channel_id
        )
        assert isinstance(channel, TextChannel)
        embed = embed_utils.create_themed_embed(
            title="顧客回饋", description="回饋", client=interaction.client
        )
        output = self.text.value
        embed.add_field(name="顧客", value=interaction.user.mention, inline=True)
        embed.add_field(name="評語", value=f"`{output}`", inline=True)
        embed.set_thumbnail(url="https://i.imgur.com/AgKFvBT.png")
        embed_utils.add_std_footer(embed=embed, client=interaction.client)
        assert isinstance(channel, TextChannel)
        await channel.send(embed=embed)
        msg = await interaction.message.reply(f"評語`{output}`已傳送!感謝您的惠顧!")
        return await msg.add_reaction("✅")

    async def on_timeout(self) -> None:
        return await super().on_timeout()


def feedbackEmbed(
    channel: TextChannel,
    client: Client,
) -> Embed:
    embed = embed_utils.create_themed_embed(
        title="顧客意見調查表",
        description="調查顧客之意見使龍龍代購更好",
        client=client,
    )
    embed.add_field(name="剛剛的服務頻道", value=channel.name)
    embed_utils.add_std_footer(embed=embed, client=client)
    return embed


class FeedBackSystem(View):
    def __init__(
        self, ticket_id: int, guild_id: int, feedback_manager: FeedbackManager
    ):
        super().__init__(timeout=86400)
        self.ticket_id = ticket_id
        self.guild_id = guild_id
        self.feedback_manager = feedback_manager
        for i in range(1, 6):
            star_emoji = "⭐" * i
            btn = Button(
                label=star_emoji,
                style=ButtonStyle.blurple,
                custom_id=f"rating_{i}",
            )
            btn.callback = self.btns_callback
            self.add_item(btn)

    @staticmethod
    def get_feedback_embed(client: Client, rating: int, user: Union[User, Member]):
        embed = embed_utils.create_themed_embed(
            title="顧客回饋", description="回饋單", client=client
        )
        embed.add_field(name="顧客", value=user.mention, inline=True)
        embed.add_field(name="滿意度", value="⭐" * rating, inline=True)
        embed.set_thumbnail(url="https://i.imgur.com/AgKFvBT.png")
        embed_utils.add_std_footer(embed=embed, client=client)
        return embed

    async def btns_callback(self, interaction: Interaction):
        assert interaction.message
        await interaction.message.edit(view=None)
        assert interaction.data
        star = interaction.data.get("custom_id")
        assert star
        star = int(star.split("_")[1])
        star_emoji = "⭐" * star
        embed = self.get_feedback_embed(
            client=interaction.client, rating=star, user=interaction.user
        )
        await interaction.response.send_message(
            f"評分 {star_emoji} 已傳送!感謝您的惠顧!"
        )
        feedback_entry = FeedbackEntry(
            ticket_id=self.ticket_id,
            guild_id=self.guild_id,
            rating=star,
            customer_id=interaction.user.id,
        )
        await self.feedback_manager.insert_feedback_entry(feedback_entry=feedback_entry)

        feed_back_channel = await try_get_channel_by_bot(
            bot=interaction.client, channel_id=feedback_channel_id
        )
        assert isinstance(feed_back_channel, TextChannel)
        new_name = f"⭐評價{await self.feedback_manager.get_avg_rating(guild_id=self.guild_id)}星"
        await feed_back_channel.edit(topic=new_name)
        await feed_back_channel.send(embed=embed)
        await interaction.user.send(
            "若您有興趣的話，請選擇想與今天服務人員說的話，或點擊按鈕輸入(擇1)。",
            view=words_selction(
                ticket_id=self.ticket_id,
                guild_id=self.guild_id,
                feedback_manager=self.feedback_manager,
            ),
        )

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
                child.label = "已逾期..."


class words_selction(View):
    def __init__(
        self, ticket_id: int, guild_id: int, feedback_manager: FeedbackManager
    ):
        self.ticket_id = ticket_id
        self.guild_id = guild_id
        self.feedback_manager = feedback_manager
        super().__init__(timeout=86400)

    @staticmethod
    def joined_review_words_and_embed(
        client: Client, values: List[str], user: Union[User, Member]
    ) -> tuple[Embed, str]:
        embed = embed_utils.create_themed_embed(
            title="顧客回饋", description="回饋", client=client
        )
        output = "、".join([f"`{value}`" for value in values])
        embed.add_field(name="顧客", value=user.mention, inline=True)
        embed.add_field(name="評語", value=f"{output}", inline=True)
        embed_utils.add_std_footer(embed=embed, client=client)
        embed.set_thumbnail(url="https://i.imgur.com/AgKFvBT.png")
        return embed, output

    @select(
        placeholder="選擇評語",
        options=words_options,
        custom_id="review",
        min_values=1,
        max_values=len(words_options),
    )
    async def words_callback(self, interaction: Interaction, select: Select):
        assert interaction.message
        await interaction.message.edit(view=None)
        assert interaction.data
        values = select.values
        embed, output = self.joined_review_words_and_embed(
            client=interaction.client,
            values=values,
            user=interaction.user,
        )
        await self.feedback_manager.update_feedback_message(
            ticket_id=self.ticket_id,
            guild_id=self.guild_id,
            customer_id=interaction.user.id,
            feedback_message=output,
        )
        feedback_channel = interaction.client.get_channel(feedback_channel_id)
        assert isinstance(feedback_channel, TextChannel)
        await feedback_channel.send(embed=embed)
        await interaction.response.send_message(f"評語{output}已傳送!感謝您的惠顧!")
        msg = await interaction.original_response()
        return await msg.add_reaction("✅")

    @button(label="輸入評語", style=ButtonStyle.blurple, emoji="⌨")
    async def btn_callback(self, interaction: Interaction, button: Button):
        assert interaction.message
        await interaction.message.edit(view=None)
        return await interaction.response.send_modal(
            FeedbackModal(
                ticket_id=self.ticket_id,
                guild_id=self.guild_id,
                feedback_manager=self.feedback_manager,
            )
        )
