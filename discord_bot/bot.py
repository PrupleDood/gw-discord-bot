from discord.ext import commands
from discord_bot.cogs import GoodwillCommands

import logging
import logging.handlers
import discord
import os

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default() #TODO figure out how intents works

        super().__init__(command_prefix = '!', intents = intents)
    
    async def on_ready(self):

        print(f'We have logged in as {self.user} (ID : {self.user.id})')
    
    async def setup_hook(self):
        
        await self.add_cog(GoodwillCommands(bot))

        await self.tree.sync()


bot = Bot()


def run():
    TOKEN = os.environ["DISCORDTOKEN"]

    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )

    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    bot.run(TOKEN)