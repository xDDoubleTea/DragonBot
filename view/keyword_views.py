from discord import ButtonStyle, Interaction, TextStyle
from discord.ui import Modal, TextInput, View, button, Button

from config.models import Keyword, KeywordType
from core.keyword_manager import KeywordManager


class KeywordChangeModal(Modal):
    def __init__(self, keyword: Keyword, keyword_manager: KeywordManager):
        super().__init__(
            title=f"確認變更關鍵字「{keyword.trigger}」之設定（輸入區顯示的為新的設定）"
        )
        self.trigger = keyword.trigger
        self.response = keyword.response
        self.kw_type = keyword.kw_type
        self.in_ticket_only = keyword.in_ticket_only
        self.guild_id = keyword.guild_id
        self.channel_ids = keyword.allowed_channel_ids
        self.keyword_manager = keyword_manager
        self.customer_mention = keyword.customer_mention
        self.trigger_input = TextInput(
            label="關鍵字",
            style=TextStyle.short,
            max_length=50,
            required=False,
            placeholder=self.trigger,
        )
        self.response_input = TextInput(
            label="回覆",
            style=TextStyle.paragraph,
            placeholder=self.response,
            required=False,
            max_length=300,
        )
        self.type_input = TextInput(
            label="關鍵字類型(句首或句中)",
            style=TextStyle.short,
            placeholder=self.kw_type.value,
            required=False,
            min_length=2,
            max_length=2,
        )
        self.in_ticket_only_input = TextInput(
            label="只在客服頻道內觸發（是或否）",
            style=TextStyle.short,
            max_length=1,
            required=False,
            placeholder="是" if self.in_ticket_only else "否",
        )
        self.add_item(self.trigger_input)
        self.add_item(self.response_input)
        self.add_item(self.type_input)
        self.add_item(self.in_ticket_only_input)

    async def on_submit(self, interaction: Interaction) -> None:
        return await super().on_submit(interaction)


class KeywordChange(View):
    def __init__(
        self,
        keyword: Keyword,
        keyword_manager: KeywordManager,
    ):
        self.keyword = keyword
        self.keyword_manager = keyword_manager
        super().__init__(timeout=None)

    @button(label="是", custom_id="是", style=ButtonStyle.green)
    async def yes_callback(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(
            KeywordChangeModal(
                keyword=self.keyword,
                keyword_manager=self.keyword_manager,
            )
        )

    @button(label="否", custom_id="否", style=ButtonStyle.red)
    async def no_callback(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("已取消更動", ephemeral=True)
