from discord import ButtonStyle, Interaction, TextStyle
from discord.ui import Modal, TextInput, View, button, Button

from config.models import KeywordType
from core.keyword_manager import KeywordManager


class KeywordChangeModal(Modal):
    def __init__(
        self,
        keyword: str,
        response: str,
        kw_type: KeywordType,
        in_ticket_only: bool,
        keyword_manager: KeywordManager,
    ):
        super().__init__(
            title=f"確認變更關鍵字{keyword}之設定（輸入區顯示的為新的設定）"
        )
        self.keyword = keyword
        self.response = response
        self.kw_type = kw_type
        self.in_ticket_only = in_ticket_only
        self.keyword_manager = keyword_manager
        self.keyword_input = TextInput(
            label="關鍵字",
            style=TextStyle.short,
            max_length=50,
            required=False,
            placeholder=self.keyword,
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
            placeholder=kw_type.value,
            required=False,
            min_length=2,
            max_length=2,
        )
        self.in_ticket_only_input = TextInput(
            label="只在客服頻道內觸發（是或否）",
            style=TextStyle.short,
            max_length=1,
            required=False,
            placeholder="是" if in_ticket_only else "否",
        )
        self.add_item(self.keyword_input)
        self.add_item(self.response_input)
        self.add_item(self.type_input)
        self.add_item(self.in_ticket_only_input)

    async def on_submit(self, interaction: Interaction) -> None:
        return await super().on_submit(interaction)


class KeywordChange(View):
    def __init__(
        self,
        keyword: str,
        response: str,
        kw_type: KeywordType,
        in_ticket_only: bool,
        keyword_manager: KeywordManager,
    ):
        self.keyword = keyword
        self.response = response
        self.kw_type = kw_type
        self.in_ticket_only = in_ticket_only
        self.keyword_manager = keyword_manager
        super().__init__(timeout=None)

    @button(label="是", custom_id="是", style=ButtonStyle.green)
    async def yes_callback(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(
            KeywordChangeModal(
                keyword=self.keyword,
                response=self.response,
                kw_type=self.kw_type,
                in_ticket_only=self.in_ticket_only,
                keyword_manager=self.keyword_manager,
            )
        )

    @button(label="否", custom_id="否", style=ButtonStyle.red)
    async def no_callback(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("已取消更動", ephemeral=True)
