import discord
from discord.ext import commands
from discord.ui import Modal, Button, View, Select, button, select
from Game.BlackJack import *
import asyncio
from Game.Tic_Tac_Toe import tic_tac_toe_buttons
from Game.Tic_Tac_Toe import TicTacToe

class GameSelect(View):
    def __init__(self, client, players:list):
        super().__init__(timeout = None)
        self.players = players
        self.client = client


    @select(
        placeholder ='選擇遊戲', 
        options = [
            discord.SelectOption(label = 'Tic Tac Toe', description = '圈圈叉叉', emoji = '⭕',value = '⭕Tic Tac Toe'),
            discord.SelectOption(label = 'Black Jack', description = '21點', emoji = '♦️',value = '♦️Black Jack'),
        ],
        custom_id='game_selection',
        min_values=1,
        max_values=1
    )
    async def game_callback(self, interaction, select:Select):
        if select.custom_id == 'game_selection':
            await interaction.response.defer()
            new_select = select.view.children[0]
            new_select.disabled = True
            await interaction.message.edit(view = self)
            desc = f'玩家列表:\n還沒有玩家加入!'
            for i in self.players:
                desc += i

            embed = discord.Embed(
                title = f'遊戲{select.values[0]}',
                description = desc,
                color=discord.Colour.dark_red()
            )
            msg = await interaction.channel.send(embed = embed)
            joinGame_view = joinGame(selection = self, game = select.values[0], msg = msg)
            await msg.edit(view = joinGame_view)
    

class joinGame(View):
    def __init__(self, selection:GameSelect, game:str, msg:discord.Message):
        super().__init__(timeout = None)
        self.selection = selection
        self.game = game
        self.msg = msg

    async def to_embed(self, msg:discord.Message):
        embed_raw = msg.embeds[0].to_dict()
        embed_raw['description'] = '玩家列表:'
        for player in self.selection.players:
            embed_raw['description'] += f'\n{player.name}'
        if len(self.selection.players) == 0:
            embed_raw['description'] += '\n還沒有玩家加入!'
            embed_raw['color'] = discord.Colour.dark_red().value
        else:
            embed_raw['color'] = discord.Colour.blue().value
        return discord.Embed.from_dict(embed_raw)

    async def start_game(self, interaction:discord.Interaction):
        msg:discord.Message = interaction.message
        if self.game == '⭕Tic Tac Toe':
            if len(self.selection.players) == 2:
                await msg.delete()
                raw_embed = discord.Embed.to_dict(msg.embeds[0])
                raw_embed['title'] = f'⭕ | 現在是{self.selection.players[0].name}的回合'
                embed = discord.Embed.from_dict(raw_embed)
                return await msg.channel.send(
                    embed = embed, 
                    view = tic_tac_toe_buttons(
                        main = TicTacToe(
                            message=msg, 
                            client = self.selection.client, 
                            players = self.selection.players
                        )
                    )
                )
            elif len(self.selection.players) > 2:
                return await interaction.response.send_message('太多人了!', ephemeral= True)
            elif len(self.selection.players) < 2:
                return await interaction.response.send_message('太少人了!', ephemeral= True)
        elif self.game == '♦️Black Jack':
            return await interaction.response.send_message('此遊戲還在開發中!請耐心等候!', ephemeral= True)


    async def has_user(self, interaction):
        has_user = False
        for i in self.selection.players:
            if i == interaction.user:
                has_user = True
                break
        return has_user


    @button(label = '✔️加入遊戲', style = discord.ButtonStyle.green, disabled = False)
    async def join_callback(self, interaction, button:Button):
        if not await self.has_user(interaction = interaction):
            self.selection.players.append(interaction.user)
            return await interaction.response.edit_message(embed = await self.to_embed(msg = interaction.message), view = self)
        else:
            return await interaction.response.send_message(content = '你已經在遊戲中!', ephemeral= True)


    @button(label = '🔄️退出遊戲', style = discord.ButtonStyle.red, disabled = False)
    async def leave_callback(self, interaction, button:Button):
        if await self.has_user(interaction = interaction):
            self.selection.players.remove(interaction.user)
            return await interaction.response.edit_message(embed = await self.to_embed(msg = interaction.message), view = self)
        else:
            return await interaction.response.send_message(content = '你不在遊戲中!', ephemeral= True)


    @button(label = '✅開始遊戲', style = discord.ButtonStyle.green, disabled = False)
    async def start_callback(self, interaction, button:Button):
        if await self.has_user(interaction = interaction):
            return await self.start_game(interaction = interaction)
        else:
            return await interaction.response.send_message('你不在遊戲內!', ephemeral= True)


    @button(label = '⛔結束遊戲', style = discord.ButtonStyle.red, disabled = False)
    async def end_callback(self, interaction, button:Button):
        if await self.has_user(interaction = interaction):
            await interaction.message.edit(view = None)
            return await interaction.response.send_message(f'{interaction.user}強制結束了遊戲!')
        else:
            return await interaction.response.send_message(f'你不在遊戲中!', ephemeral= True)


class games(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(name = 'game')
    async def game(self, ctx):
        return await ctx.send(view = GameSelect(client=self.client, players=[]))

async def setup(client):
    await client.add_cog(games(client))