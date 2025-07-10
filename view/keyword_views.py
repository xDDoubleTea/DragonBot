from discord import ButtonStyle, Interaction, TextStyle
from discord.ui import Modal, TextInput, View, button, Button

from config.models import boolean_to_str, Keyword, KeywordType, str_to_boolean
from core.keyword_manager import KeywordManager


class KeywordChangeModal(Modal):
    def __init__(
        self,
        keyword: Keyword,
        new_keyword: Keyword,
        keyword_manager: KeywordManager,
        title: str = "確認變更關鍵字之設定，可直接打上新的設定來覆蓋原本設定。",
    ):
        super().__init__(title=title + "\n關鍵字：" + keyword.trigger)
        self.keyword = keyword
        self.new_keyword = new_keyword
        self.keyword_manager = keyword_manager
        self.response_input = TextInput(
            label="回覆",
            style=TextStyle.paragraph,
            placeholder=f"{keyword.response}->{new_keyword.response}",
            required=False,
            max_length=300,
        )
        self.type_input = TextInput(
            label="關鍵字類型(句首或句中)",
            style=TextStyle.short,
            placeholder=f"{keyword.kw_type.value}->{new_keyword.kw_type.value}",
            required=False,
            min_length=0,
            max_length=2,
        )
        self.in_ticket_only_input = TextInput(
            label="只在客服頻道內觸發（是或否）",
            style=TextStyle.short,
            max_length=1,
            required=False,
            placeholder=f"{boolean_to_str(keyword.in_ticket_only)}->{boolean_to_str(new_keyword.in_ticket_only)}",
        )
        self.mention_participants_input = TextInput(
            label="提及參與者（是或否）",
            style=TextStyle.short,
            max_length=1,
            required=False,
            placeholder=f"{boolean_to_str(keyword.mention_participants)}->{boolean_to_str(new_keyword.mention_participants)}",
        )
        self.add_item(self.response_input)
        self.add_item(self.type_input)
        self.add_item(self.in_ticket_only_input)
        self.add_item(self.mention_participants_input)

    async def on_submit(self, interaction: Interaction) -> None:
        new_response = self.response_input.value or self.new_keyword.response
        kw_type_val = self.type_input.value or self.new_keyword.kw_type.value
        if kw_type_val and kw_type_val not in {
            KeywordType.IS_SUBSTR.value,
            KeywordType.MATCH_START.value,
        }:
            await interaction.response.send_message(
                f"錯誤：類型 '{kw_type_val}' 不是 '句首' 或 '句中'。", ephemeral=True
            )
            return

        ticket_only_val = self.in_ticket_only_input.value or boolean_to_str(
            self.new_keyword.in_ticket_only
        )
        if ticket_only_val and ticket_only_val not in {
            boolean_to_str(True),
            boolean_to_str(False),
        }:
            await interaction.response.send_message(
                f"錯誤：僅在客服頻道觸發的值 '{ticket_only_val}' 不是 '是' 或 '否'。",
                ephemeral=True,
            )
            return

        mention_val = self.mention_participants_input.value or boolean_to_str(
            self.new_keyword.mention_participants
        )
        if mention_val and mention_val not in {boolean_to_str(True), boolean_to_str(False)}:
            await interaction.response.send_message(
                f"錯誤：提及參與者的值 '{mention_val}' 不是 '是' 或 '否'。",
                ephemeral=True,
            )
            return
        # Everything is valid, proceed to update the keyword
        update_data = {}
        if new_response:
            update_data["response"] = new_response
        if kw_type_val:
            update_data["kw_type"] = KeywordType(kw_type_val)
        if ticket_only_val:
            update_data["in_ticket_only"] = str_to_boolean(ticket_only_val)
        if mention_val:
            update_data["mention_participants"] = str_to_boolean(mention_val)

        # --- Database Update Step ---
        if not update_data:
            await interaction.response.send_message("沒有任何變更。", ephemeral=True)
            return

        await self.keyword_manager.update_keyword(
            guild_id=self.keyword.guild_id,
            trigger=self.keyword.trigger,
            data=update_data,
        )
        await interaction.response.send_message("關鍵字已成功更新！", ephemeral=True)


class KeywordChange(View):
    def __init__(
        self,
        keyword: Keyword,
        new_keyword: Keyword,
        keyword_manager: KeywordManager,
    ):
        self.keyword = keyword
        self.keyword_manager = keyword_manager
        self.new_keyword = new_keyword
        super().__init__(timeout=None)

    @button(label="是", custom_id="是", style=ButtonStyle.green)
    async def yes_callback(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(
            KeywordChangeModal(
                keyword=self.keyword,
                new_keyword=self.new_keyword,
                keyword_manager=self.keyword_manager,
            )
        )

    @button(label="否", custom_id="否", style=ButtonStyle.red)
    async def no_callback(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("已取消更動", ephemeral=True)
