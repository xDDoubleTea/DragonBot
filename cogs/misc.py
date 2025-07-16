from discord.ext.commands import Bot, Cog, CommandError, Context
from discord.ext import commands
from discord import app_commands, Interaction
from discord.abc import GuildChannel, Messageable
from typing import Literal, Optional
from config.models import CurrencyIndex
from core.keyword_manager import KeywordManager
from core.ticket_manager import TicketManager
from main import DragonBot
from utils.checks import IsNotDev, is_me_app_command, is_me_command
from utils.discord_utils import try_get_channel_by_bot
from core import CurrencyManager
from utils.transformers import CurrencyTransformer
import intervals


class misc(Cog):
    def __init__(
        self,
        bot: Bot,
        ticket_manager: TicketManager,
        keyword_manager: KeywordManager,
        currency_manager: CurrencyManager,
    ):
        self.bot = bot
        self.ticket_manager = ticket_manager
        self.keyword_manager = keyword_manager
        self.currency_manager = currency_manager

    @app_commands.command(name="set_tax", description="設置匯率轉換後要加多少錢")
    @app_commands.describe(
        lower_bound="定義從哪裡開始要加多少錢，未填或填入負數則自動設為0",
        upper_bound="定義到哪裡為止要加多少錢，未填則表示沒有上界",
        tax="（轉換之後）要加多少錢（臺幣）",
    )
    async def set_tax(
        self,
        interaction: Interaction,
        lower_bound: Optional[int],
        upper_bound: Optional[int],
        tax: int,
    ):
        pass

    @app_commands.command(name="convert", description="匯率轉換指令，將輸入轉換為NTD")
    @app_commands.describe(
        cur_type="輸入匯率",
        show_result_public="是否要使所有人看見。輸入y, n分別表示是或否，預設為否",
    )
    async def cur_convert(
        self,
        interaction: Interaction,
        amount: float,
        cur_type: app_commands.Transform[
            CurrencyIndex, CurrencyTransformer(CurrencyIndex)
        ],
        show_result_public: Literal["y", "n"] = "n",
    ):
        output = 0
        try:
            amount = float(amount)
        except ValueError:
            return await interaction.response.send_message(
                "請輸入一數字！", ephemeral=True
            )

        currency = await self.currency_manager.get_currency(cur=cur_type)
        if not currency:
            return await interaction.response.send_message(
                "台灣銀行爬蟲網站爆炸了...", ephemeral=True
            )
        amount *= currency
        # TODO: Make this configurable
        if amount < 200:
            output = amount + 30
        elif 200 <= amount < 500:
            output = amount + 40
        elif 500 <= amount < 900:
            output = amount + 60
        elif 900 <= amount < 1200:
            output = amount + 70
        elif 1200 <= amount < 1500:
            output = amount + 80
        elif 1500 <= amount < 2500:
            output = amount + 100
        elif 2500 <= amount < 3000:
            output = amount + 130
        elif amount >= 3000:
            output = amount + 200
        eph = True
        output = int(round(output))
        if show_result_public.lower() == "y":
            eph = False
        elif show_result_public.lower() == "n":
            eph = True
        else:
            return await interaction.response.send_message(
                "請輸入y或n！", ephemeral=True
            )
        await interaction.response.send_message(content=f"NTD ${output}", ephemeral=eph)

    @app_commands.command(name="ping", description="Is the bot alive? Pings the bot.")
    async def ping(self, interaction: Interaction):
        await interaction.response.send_message(
            content=f"{round((interaction.client.latency) * 1000)}ms"
        )

    @app_commands.command(name="say", description="Say a message")
    @is_me_app_command()
    async def say(
        self,
        interaction: Interaction,
        message: str,
        channel: Optional[GuildChannel],
        channel_id: Optional[str],
    ):
        if (
            not channel and not interaction.channel and not channel_id
        ) or not interaction.channel:
            return await interaction.response.send_message(
                "Provide a channel or use this command in a channel.", ephemeral=True
            )
        try:
            if isinstance(channel, Messageable):
                await channel.send(content=message)
            elif channel_id:
                if (
                    channel := await try_get_channel_by_bot(
                        bot=interaction.client, channel_id=int(channel_id)
                    )
                ) and isinstance(channel, Messageable):
                    await channel.send(content=message)
                else:
                    return await interaction.response.send_message(
                        content="That channel is not messageable!", ephemeral=True
                    )
            elif isinstance(interaction.channel, Messageable):
                await interaction.channel.send(content=message)
            else:
                return await interaction.response.send_message(
                    content="That channel is not messageable!", ephemeral=True
                )
        except ValueError:
            return await interaction.response.send_message(
                "channel id should be an integer", ephemeral=True
            )
        await interaction.response.send_message("Done.", ephemeral=True)

    @commands.command(name="sync_app_cmds", aliases=["sync_app"])
    @is_me_command()
    async def sync_app_cmds(self, ctx: Context, where="every"):
        msg = await ctx.reply(mention_author=False, content="Loading...")
        if where == "every":
            for guilds in self.bot.guilds:
                await self.bot.tree.sync(guild=guilds)

        elif where == "here":
            if not ctx.guild:
                return await ctx.send("This command can only be used in guilds.")
            self.bot.tree.copy_global_to(guild=ctx.guild)
            await self.bot.tree.sync(guild=ctx.guild)
        return await msg.edit(content="Done")

    @sync_app_cmds.error
    async def sync_app_cmds_err(self, ctx: Context, error: CommandError):
        if isinstance(error, IsNotDev):
            await ctx.send(error.message)

    @say.error
    async def say_err(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, IsNotDev):
            await interaction.response.send_message(error.message)


async def setup(client: DragonBot):
    await client.add_cog(
        misc(
            bot=client,
            ticket_manager=client.ticket_manager,
            keyword_manager=client.keyword_manager,
            currency_manager=client.currency_manager,
        )
    )
