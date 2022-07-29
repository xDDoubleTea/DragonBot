import os
import discord
from discord.ext import commands
from config.bot_info import pre, bot_token

class DragonBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = pre, intents= discord.Intents.all(), help_command = None)

    async def on_ready(self):
        print(f'{self.user} is now online!')


    async def setup_hook(self):
        for files in os.listdir('./cogs'):
            if files.endswith('.py'):
                await self.load_extension(f'cogs.{files[:-3]}')

client = DragonBot()
client.run(bot_token)