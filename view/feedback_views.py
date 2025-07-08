from typing import List, Union
from discord import (
    Client,
    Embed,
    File,
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
from utils import embed_utils

words_options = [
    SelectOption(label="服務速度快速", emoji="✅", default=False),
    SelectOption(label="服務態度良好", emoji="✅", default=False),
    SelectOption(label="服務優質", emoji="✅", default=False),
]


class FeedbackModal(Modal):
    def __init__(self):
        super().__init__(title="評語", timeout=None)

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
        channel = await interaction.client.fetch_channel(feedback_channel_id)
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
    def __init__(self):
        super().__init__(timeout=86400)
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
        msg = await interaction.response.send_message(
            f"評分 {star_emoji} 已傳送!感謝您的惠顧!"
        )
        msg = await interaction.original_response()
        await msg.add_reaction("✅")

        await interaction.user.send(
            "若您有興趣的話，請選擇想與今天服務人員說的話，或點擊按鈕輸入(擇1)。",
            view=words_selction(),
        )
        feed_back_channel = interaction.client.get_channel(feedback_channel_id)
        assert isinstance(feed_back_channel, TextChannel)
        await feed_back_channel.send(embed=embed)


class words_selction(View):
    def __init__(self):
        super().__init__(timeout=86400)

    @staticmethod
    def review_words_embed(
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
        embed, output = self.review_words_embed(
            client=interaction.client,
            values=values,
            user=interaction.user,
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
        return await interaction.response.send_modal(FeedbackModal())
