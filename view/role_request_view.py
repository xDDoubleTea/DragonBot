from discord import Embed, Member, ButtonStyle, Role, Interaction, TextStyle
from discord.ui import Modal, View, Button, button, TextInput


class reason_Modal(Modal):
    def __init__(self, embed: Embed, role_name: str, member: Member):
        super().__init__(title="不通過之原因", timeout=None)
        self.embed = embed
        self.role_name = role_name
        self.member = member

    reason = TextInput(label="原因", style=TextStyle.long)

    async def on_submit(self, interaction: Interaction) -> None:
        assert interaction.guild and self.embed.title and interaction.message
        await self.member.send(
            content=f"先前在「{interaction.guild.name}」所提出之身分組申請被拒絕了"
        )
        await self.member.send(content=f"原因如下：\n{self.reason.value}")
        await self.member.send(content="你所提供的資料：", embed=self.embed)
        await interaction.response.send_message(
            "已將拒絕原因傳送給申請人！", ephemeral=True
        )
        self.embed.title = self.embed.title + "(未通過)"
        self.embed.description = f"申請身分組：{self.role_name}"
        await interaction.message.edit(embed=self.embed)


class request_view(View):
    def __init__(self, role: Role, member: Member):
        super().__init__(timeout=None)
        self.role = role
        self.member = member

    @button(label="通過", style=ButtonStyle.green)
    async def confirm_callback(self, interaction: Interaction, button: Button):
        try:
            assert interaction.message
            await interaction.message.edit(view=None)
            await self.member.add_roles(self.role)
            await interaction.response.send_message(
                f"已為{self.member.mention}加上{self.role.mention}身分組！",
                ephemeral=True,
            )
            embed = interaction.message.embeds[0]
            assert embed.title
            embed.title += "(已通過)"
            return await interaction.message.edit(embed=embed)
        except AssertionError:
            await interaction.response.send_message("出了點問題", ephemeral=True)

    @button(label="不通過", style=ButtonStyle.red)
    async def reject_callback(self, interaction: Interaction, button: Button):
        try:
            assert interaction.message
            await interaction.message.edit(view=None)
            return await interaction.response.send_modal(
                reason_Modal(
                    embed=interaction.message.embeds[0],
                    role_name=self.role.name,
                    member=self.member,
                )
            )
        except AssertionError:
            await interaction.response.send_message("出了點問題", ephemeral=True)
