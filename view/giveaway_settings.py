from discord import TextStyle, Interaction
from discord.ui import Modal, TextInput
import json

from utils.giveaway_embed import giveaway_settings_to_embed


class GiveawaySettings(Modal):
    def __init__(
        self,
        title: str = "抽獎設定",
    ):
        super().__init__(title=title)
        self.settings_input = TextInput(
            label="抽獎",
            style=TextStyle.paragraph,
            placeholder="格式：『獎品:機率』",
            required=True,
            max_length=300,
        )
        self.add_item(self.settings_input)

    def validate_data(self, input_value: str) -> dict:
        items = input_value.splitlines()
        data = dict()
        sum = 0.0
        for item in items:
            k, v = item.split(":")
            if k in data.keys():
                raise Exception("重複的獎品")

            v = float(v)
            if v <= 0:
                raise Exception("機率只能是正數")
            if sum + v > 1.0:
                raise Exception("機率和大於1")
            data[k] = v
            sum += v

        print(sum)
        if round(sum, 2) != 1.00:
            raise Exception("機率和不是1")
        return data

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            data = self.validate_data(self.settings_input.value)
        except Exception as e:
            print(e)
            await interaction.followup.send(content=f"設定有誤！{e}", ephemeral=True)
            return

        with open("config/giveaway.json", "w") as file:
            json.dump(data, file, indent=4)

        await interaction.followup.send(
            content="設置完成！",
            embed=giveaway_settings_to_embed(
                client=interaction.client, giveaway_settings=data
            ),
            ephemeral=True,
        )
