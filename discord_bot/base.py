import aiohttp
import discord
import json

from discord import Embed, Webhook
from discord.ext import commands
from typing import List

from goodwill.dataclasses import Listing, IdSearch

def isAdmin():
    '''
    Wrapper used to verify user calling command is admin
    '''

    async def predicate(interaction: discord.Interaction):

        if interaction.guild is None:
            return False  # Command can't be used in DMs

        return interaction.user.guild_permissions.administrator

    return commands.check(predicate)


# Listing functions
def listingEmbed(listing: Listing) -> Embed: 
    embed = Embed(title = listing.title, description = "listing.description", colour=discord.Colour.blue())
    
    embed.add_field(name = 'Current Price', value = listing.currentPrice, inline = True)
    embed.add_field(name = "Remainging Time", value = listing.remainingTime)
    embed.add_field(name = "Ending", value = listing.endTime) 

    embed.set_footer(text = listing.url)

    if isinstance(listing, Listing):
        url = f"https://shopgoodwillimages.azureedge.net/production/{listing.imageUrlString.split(';')[0]}"
        embed.set_image(url = url) 
    
    return embed


def pageEmbed(
        keywords, category, listings: List[Listing], 
        page: int, total_pages: int, searchType: int = 0
    ) -> Embed:
    title_str = f'Keyword Search: "{keywords}"' if searchType == 0 else f'Id Search: {keywords}'

    embed = Embed(title = title_str, colour=discord.Color.blue())

    for listing in listings[:23]:
        embed.add_field(
            name = f"{listing.title}", 
            value = f"${listing.currentPrice} | {listing.remainingTime}\n{listing.url}", 
            inline = True
        )

    embed.set_footer(text = f"Page: {page}/{total_pages} | Category: {category}")

    return embed


# Webhook functions
async def getWebhook(guild: discord.Guild):
    guild_data = getGuildData(guild)

    webhook_url = guild_data["webhookurl"]

    webhook, session = await checkWebhook(webhook_url)

    return webhook, session


async def checkWebhook(webhookUrl) -> tuple[Webhook, aiohttp.ClientSession] | None:
    # Check if webhook is valid
    try:
        session = aiohttp.ClientSession()
        
        webhook : Webhook = Webhook.from_url(url = webhookUrl, session = session)
        webhook = await webhook.fetch()
        
        if not webhook:
            raise ValueError

        return webhook, session

    except ValueError as e:
        #add logging here
        print(f"INVALID URL: {e}")
        return


# Guild data functions (Used for setup of bot)
def getGuildData(guild: discord.Guild) -> dict | None:
    '''
    Returns webhook str or none if no data found.\n
    Keys should be "webhook" and "forumchannel".
    '''
    with open("discord_bot/bot_config.json") as config:
        json_config: dict = json.load(config)

        if str(guild.id) not in json_config["guilds"].keys():
            return None

        return json_config["guilds"][str(guild.id)]


def addGuildData(guild: discord.Guild, webhook: str = None, forumchannel: str = None ) -> None:
    '''
    Updates local file and returns updated dict.
    '''
    with open("discord_bot/bot_config.json", "r+") as config:
        json_config = json.load(config)

        cur_data = getGuildData(guild)

        # Make sure not to overwrite other entries
        new_forum = forumchannel if forumchannel else cur_data["forumid"]   
        new_webhook = webhook if webhook else cur_data["webhookurl"]

        data_obj = {
            "forumid": new_forum,
            "webhookurl": new_webhook
        }

        json_config["guilds"][str(guild.id)] = data_obj

    with open("discord_bot/bot_config.json", "w") as config:
        json.dump(json_config, config)


async def bidResponseEmbed(bidResponse: bool, listing: Listing):

    embed = Embed(title = f"Bid for {listing.title}", colour=discord.Color.blue())

    listing_update = await IdSearch(itemId = listing.itemId).makeRequest()

    desc = f"You are currently the highest bidder!" if bidResponse else "You have already been outbid."

    embed.add_field(name = "Product Id", value = listing.itemId)
    embed.add_field(name = "Current Price", value = listing_update.currentPrice)
    embed.add_field(name = desc, value = "")

    return embed
