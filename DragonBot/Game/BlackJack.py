from typing import List
import discord
from discord.ext import commands
from discord.ui import Modal, Button, View, Select, button, select

class BlackJack:
    class gameOptions:
        def __init__(self, author:discord.User, client:discord.Client, players:list):
            self.author = author
            self.client = client
            self.players = players
    
    def __init__(self, cards:list, msg :discord.Message):
        self.cards = cards
        self.msg = msg

class BlackJack_buttons(View):
    def __init__(self, main:BlackJack):
        super().__init__(timeout = None)
        self.main = main
