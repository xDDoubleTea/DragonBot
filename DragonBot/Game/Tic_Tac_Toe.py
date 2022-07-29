from typing import List
import discord
from discord.ext import commands
from discord.ui import Modal, Button, View, Select, button, select

class TicTacToe:
    class gamedata:
        def __init__(self, players:list,now_game:list,now_player:int, game_win:int):
            self.players = players
            self.now_game = now_game
            self.now_player = now_player
            self.game_win = game_win
            #game_win is the state of the game, 0 for no winner, 1 for circle win, 2 for cross win
    
    def __init__(self, message:discord.Message, client:discord.Client, players:list):
        self.message = message
        self.client = client
        self.now_player = 0
        self.players = players
        self.now_game:List[self.gamedata] = [[0 for j in range(3)] for i in range(3)]
        self.game_win = 0

class tic_tac_toe_buttons(View):
    def __init__(self, main:TicTacToe):
        super().__init__(timeout=None)
        self.main = main

    async def to_embed(self, msg: discord.Message):
        raw_embed = discord.Embed.to_dict(msg.embeds[0])
        emoji = ' '
        if self.main.now_player == 0:
            emoji = '⭕'
        else:
            emoji = '❎'
        raw_embed['title'] = f'遊戲結束!'
        raw_embed['description'] = f'獲勝玩家:({emoji}){self.main.players[self.main.now_player]}'
        raw_embed['color'] = discord.Colour.green().value
        return discord.Embed.from_dict(raw_embed)

    async def if_win(self, msg:discord.Message):
        ng = self.main.now_game
        won = False
        draw = False
        # 橫向
        if (ng[0][0] != 0 and ng[0][1] != 0 and ng[0][2] != 0):
            if (ng[0][0] == ng[0][1] and ng[0][1] == ng[0][2]):
                won = True
        elif (ng[1][0] != 0 and ng[1][1] != 0 and ng[1][2] != 0):
            if (ng[1][0] == ng[1][1] and ng[1][1] == ng[1][2]):
                won = True
        elif (ng[2][0] != 0 and ng[2][1] != 0 and ng[2][2] != 0):
            if (ng[2][0] == ng[2][1] and ng[2][1] == ng[2][2]):
                won = True

        # 縱向
        if (ng[0][0] != 0 and ng[1][0] != 0 and ng[2][0] != 0):
            if (ng[0][0] == ng[1][0] and ng[1][0] == ng[2][0]):
                won = True
        elif (ng[0][1] != 0 and ng[1][1] != 0 and ng[2][1] != 0):
            if (ng[0][1] == ng[1][1] and ng[1][1] == ng[2][1]):
                won = True
        elif (ng[0][2] != 0 and ng[1][2] != 0 and ng[2][2] != 0):
            if (ng[0][2] == ng[1][2] and ng[1][2] == ng[2][2]):
                won = True

        # 斜角
        if (ng[0][0] != 0 and ng[1][1] != 0 and ng[2][2] != 0):
            if (ng[0][0] == ng[1][1] and ng[1][1] == ng[2][2]):
                won = True
        elif (ng[0][2] != 0 and ng[1][1] != 0 and ng[2][0] != 0):
            if (ng[0][2] == ng[1][1] and ng[1][1] == ng[2][0]):
                won = True
        if not won:
            # 是否平手
            all_true = []
            for i in range(3):
                for j in range(3):
                    if (not won) and ng[i][j]!=0:
                        all_true.append(1)
                    else:
                        all_true.append(0)

            won = True
            draw = True
            for i in all_true:
                if i == 0:
                    won = False
                    draw = False
            

        if won:
            if not draw:
                if self.main.now_player == 0:
                    who_won = 1
                elif self.main.now_player == 1:
                    who_won = 2
            else:
                who_won = 3
            self.now_game = [[0 for j in range(3)] for i in range(3)]
            for i in self.children:
                i.disabled = True
            await msg.edit(view = self)
            return who_won

    async def displaying(self, msg:discord.Message, button:Button):
        #0 for circle player, 1 for cross player
        row = int(button.custom_id.split(', ')[0])
        col = int(button.custom_id.split(', ')[1])
        button.disabled = True
        if self.main.now_player == 0:
            button.emoji = '⭕'
            button.style = discord.ButtonStyle.green
            self.main.now_game[row][col] = 1

        else:
            button.emoji = '❎'
            button.style = discord.ButtonStyle.red
            self.main.now_game[row][col] = 2
        
        return await msg.edit(view = self)

    async def whose_turn_embed(self, msg:discord.Message):
        raw_embed = discord.Embed.to_dict(msg.embeds[0])
        emoji = ' '
        if self.main.now_player == 0:
            emoji = '⭕'
        else:
            emoji = '❎'
        raw_embed['title'] = f'{emoji} | 現在是{self.main.players[self.main.now_player].name}的回合'
        return discord.Embed.from_dict(raw_embed)

    async def all_callback(self, interaction, button:Button):
        if interaction.user == self.main.players[self.main.now_player]:
            await self.displaying(interaction.message, button)
            if await self.if_win(msg = interaction.message) == 1 or await self.if_win(msg = interaction.message) == 2:
                return await interaction.response.send_message(embed = await self.to_embed(msg = interaction.message))
            elif await self.if_win(msg = interaction.message) == 3:
                raw_embed = discord.Embed.to_dict(interaction.message.embeds[0])
                raw_embed['title'] = '遊戲結束!'
                raw_embed['description'] = f'平手!'
                raw_embed['color'] = discord.Colour.yellow().value
                embed = discord.Embed.from_dict(raw_embed)
                return await interaction.response.send_message(embed = embed)
            else:
                if self.main.now_player == 0:
                    self.main.now_player = 1
                else:
                    self.main.now_player = 0
                return await interaction.response.edit_message(embed = await self.whose_turn_embed(msg = interaction.message),view = self)
        else:
            return await interaction.response.send_message('現在不是你的回合', ephemeral=True)

    def has_user(self, interaction:discord.Interaction):
        has_user = False
        for user in self.main.players:
            if interaction.user == user:
                has_user = True
                break
        return has_user

    @button(label = None, emoji = '⏹️', style = discord.ButtonStyle.gray, disabled = False, custom_id = '0, 0', row = 0)
    async def zero_zero_callback(self, interaction, button:Button):
        if self.has_user(interaction = interaction):
            return await self.all_callback(interaction, button)
        else:
            return await interaction.response.send_message('你不在遊戲內!', ephemeral=True)

    @button(label = None, emoji = '⏹️', style = discord.ButtonStyle.gray, disabled = False, custom_id = '0, 1', row = 0)
    async def zero_one_callback(self, interaction, button:Button):
        if self.has_user(interaction = interaction):
            return await self.all_callback(interaction, button)
        else:
            return await interaction.response.send_message('你不在遊戲內!', ephemeral=True)

    @button(label = None, emoji = '⏹️', style = discord.ButtonStyle.gray, disabled = False, custom_id = '0, 2', row = 0)
    async def zero_two_callback(self, interaction, button:Button):
        if self.has_user(interaction = interaction):
            return await self.all_callback(interaction, button)
        else:
            return await interaction.response.send_message('你不在遊戲內!', ephemeral=True)

    @button(label = None, emoji = '⏹️', style = discord.ButtonStyle.gray, disabled = False, custom_id = '1, 0', row = 1)
    async def one_zero_callback(self, interaction, button:Button):
        if self.has_user(interaction = interaction):
            return await self.all_callback(interaction, button)
        else:
            return await interaction.response.send_message('你不在遊戲內!', ephemeral=True)

    @button(label = None, emoji = '⏹️', style = discord.ButtonStyle.gray, disabled = False, custom_id = '1, 1', row = 1)
    async def one_one_callback(self, interaction, button:Button):
        if self.has_user(interaction = interaction):
            return await self.all_callback(interaction, button)
        else:
            return await interaction.response.send_message('你不在遊戲內!', ephemeral=True)
    @button(label = None, emoji = '⏹️', style = discord.ButtonStyle.gray, disabled = False, custom_id = '1, 2', row = 1)
    async def one_two_callback(self, interaction, button:Button):
        if self.has_user(interaction = interaction):
            return await self.all_callback(interaction, button)
        else:
            return await interaction.response.send_message('你不在遊戲內!', ephemeral=True)

    @button(label = None, emoji = '⏹️', style = discord.ButtonStyle.gray, disabled = False, custom_id = '2, 0', row = 2)
    async def two_zero_callback(self, interaction, button:Button):
        if self.has_user(interaction = interaction):
            return await self.all_callback(interaction, button)
        else:
            return await interaction.response.send_message('你不在遊戲內!', ephemeral=True)

    @button(label = None, emoji = '⏹️', style = discord.ButtonStyle.gray, disabled = False, custom_id = '2, 1', row = 2)
    async def two_one_callback(self, interaction, button:Button):
        if self.has_user(interaction = interaction):
            return await self.all_callback(interaction, button)
        else:
            return await interaction.response.send_message('你不在遊戲內!', ephemeral=True)

    @button(label = None, emoji = '⏹️', style = discord.ButtonStyle.gray, disabled = False, custom_id = '2, 2', row = 2)
    async def two_two_callback(self, interaction, button:Button):
        if self.has_user(interaction = interaction):
            return await self.all_callback(interaction, button)
        else:
            return await interaction.response.send_message('你不在遊戲內!', ephemeral=True)

    #@button(label = '⛔結束遊戲', style = discord.ButtonStyle.red, disabled = False, row = 3, disabled = True)
    #async def end_callback(self, interaction, button:Button):
    #    has_user = False
    #    for user in self.main.players:
    #        if interaction.user == user:
    #            has_user = True
    #            break
    #    
    #    if has_user:
    #        await interaction.message.edit(view = None)
    #        return await interaction.response.send_message(f'{interaction.user}強制結束了遊戲!')
    #    else:
    #        return await interaction.response.send_message(f'你不在遊戲中!', ephemeral= True)
