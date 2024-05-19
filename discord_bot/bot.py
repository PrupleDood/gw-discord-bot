from discord.ext import commands
from discord_bot.cogs import GoodwillCommands

import discord
import os

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default() #TODO figure out how intents works
        
        super().__init__(command_prefix = '!', intents = intents)
        
        #self.tree = app_commands.CommandTree(self)
    
    async def on_ready(self):

        print(f'We have logged in as {self.user} (ID : {self.user.id})')
    
    async def setup_hook(self):
        
        await self.add_cog(GoodwillCommands(bot))

        await self.tree.sync()
        #return 


bot = Bot()

@bot.command()
async def terminate(ctx: commands.Context): 
    '''Terminates the process'''
    await ctx.send('Terminating program...')
    await ctx.channel.purge(limit=2)
    
    await bot.close()
    
    exit(0)


def run():
    TOKEN = os.environ["DISCORDTOKEN"]
    bot.run(TOKEN)