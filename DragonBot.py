import os
import discord
from discord.ext import commands
from config import pre, app_id, bot_token, My_user_id, version, app_mode


class DragonBot(commands.Bot):
    def __init__(self):
        assert pre is not None, "Prefix must be defined in the config"
        super().__init__(
            command_prefix=pre,
            intents=discord.Intents.all(),
            help_command=None,
            description=f"Dragon Bot version {version}\n Mode {app_mode}",
            application_id=app_id,
        )

    async def on_ready(self):
        print(f"{self.user} is now online!")
        await self.change_presence(
            activity=discord.Game(f"Developed by {self.get_user(My_user_id)}")
        )
        # with open("purchase_msg_info.json", "r") as file:
        #     data = json.load(file)
        #
        # v = OpenButtons(client=self)
        # if not data:
        #     cnl = self.get_channel(data["message_cnl_id"])
        #     assert isinstance(cnl, discord.TextChannel)
        #     msg = await cnl.fetch_message(data["message_id"])
        #     return await msg.edit(view=v)
        # with open("channel_data.json", "r") as file:
        #     data = json.load(file)

    async def setup_hook(self):
        for cog in filter(
            lambda file: os.path.isfile(file) and file.endswith(".py"),
            os.listdir("./cogs"),
        ):
            await self.load_extension(f"cogs.{cog[:-3]}")


client = DragonBot()
assert bot_token is not None
client.run(bot_token)
