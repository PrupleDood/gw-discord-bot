from discord.ext import commands
import discord
from discord import app_commands, Embed
import asyncio
from math import ceil

from goodwill.dataclasses import IdSearch, ItemListingParams, ItemListingDataParams, KeywordSearch
from goodwill.db import getQuery

from discord_bot import TEMPUSERDATA
from discord_bot.base import listingEmbed, isAdmin, addGuildData, getWebhook, pageEmbed
from discord_bot.views import KeywordResults
from discord_bot.timed_events import watchListingPrice

async def forum_channels(interaction: discord.Interaction, current: str):
    channels = interaction.guild.channels

    return [
        app_commands.Choice(name = channel.name, value = str(channel.id))
        for channel in channels if channel.type.name == 'forum' and current in current
    ]


class GoodwillCommands(commands.Cog):
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    search_group = app_commands.Group(name = "search", description = "Commands used to search goodwill")

    @search_group.command(name = "keyword", description='Search by Keyword')
    async def searchkey(self, interaction: discord.Interaction, keywords: str):
        userdata = TEMPUSERDATA.getUser(interaction.user)

        category = userdata.category if userdata else None

        if category:
            searchParams = ItemListingParams(
                catIds = category.getCategoryIds(),
                categoryId = category.categoryId,
                categoryLevel = category.levelNumber,
                categoryLevelNo = str(category.levelNumber),
                searchText = keywords,
            )

        else:
            searchParams = ItemListingDataParams(st = keywords)
        
        searchObject = KeywordSearch(params = searchParams)

        res, total_listings = await searchObject.makeRequest()

        embed = pageEmbed(
            keywords = keywords,
            category = category.categoryName,
            listings =  res[:20],
            page = 1,
            total_pages = ceil(total_listings/40) # 40 listing per page
        )

        return await interaction.response.send_message(
            embed = embed, 
            view = KeywordResults(
                search_object = searchObject, 
                category = category.categoryName,
                listing_data = (res, total_listings)
            ),
        )

    @search_group.command(name = "id", description='Search by listing IDs comma seperated')
    async def searchid(self, interaction: discord.Interaction, ids: str): #TODO add Id length checking
        if ',' in ids:
            valid_ids = [id.strip() for id in ids.split(",") if id.strip().isnumeric()]
            listings = [await IdSearch(itemId=validId).makeRequest() for validId in valid_ids]
            listings = [listing for listing in listings if listing] # Make sure listing is not none

            listings = listings if len(listings) > 0 else None

        else:
            listingId = ids
            listing = await IdSearch(listingId).makeRequest()

            listings = [listing] if listing else None # Make sure listing is not none

        if listings is None:
            raise ValueError("Invalid Ids or other error")

        embeds = []

        for listing in listings:
            embeds.append(listingEmbed(listing))

        await interaction.response.send_message(embeds = embeds)

        
    @isAdmin() 
    @app_commands.command(name = "setforum", description = "Set forum channel to be used")
    @app_commands.autocomplete(channel_name = forum_channels)
    async def setforumchannel(self, interaction: discord.Interaction, channel_name: str):
        if not channel_name.isnumeric(): 
            pass
        
        channel = interaction.guild.get_channel_or_thread(int(channel_name))

        webhook = await channel.create_webhook(name = "Goodwill Fourm", reason = "Goodwill bot setup")

        addGuildData(interaction.guild, webhook = webhook.url, forumchannel = channel.id)

        return await interaction.response.send_message(f"Set forum channel to {channel.name}", ephemeral = True)


    @app_commands.command(name = "watchlisting", description='Create a webhook to send reminders')
    async def watchlisting(self, interaction: discord.Interaction, id: str):

        webhook, session = await getWebhook(interaction.guild)

        forum_channel : discord.ForumChannel = await interaction.guild.fetch_channel(webhook.channel_id)

        existing_threads = [thread for thread in forum_channel.threads if thread.name == f"{interaction.user.name}'s Space"]

        if len(existing_threads) > 0:
            new_thread = existing_threads[0]

        else:
            new_thread, msg = await forum_channel.create_thread(
                name = f"{interaction.user.name}'s Space", 
                content = f"Thread created for {interaction.user.name}",
            )

        await new_thread.add_user(interaction.user)

        await session.close()

        asyncio.create_task(watchListingPrice(id, new_thread, interaction.guild)) 

        await interaction.response.send_message(f'Create a webhook to send reminders at {id}')


    @app_commands.command(name = "select-category", description = "Set categories to search") 
    async def add(self, interaction: discord.Interaction, category_id: str):
        category = getQuery(cat_id = category_id)

        if not category:
            await interaction.response.send_message(f"Category not found for id {category_id}", delete_after = 10)

        TEMPUSERDATA.addUser(interaction.user, category)

        await interaction.response.send_message(f"Category set to {category.categoryName}", delete_after = 10)

    @app_commands.command(name = "check-category", description = "View selected category")
    async def checkCategory(self, interaction: discord.Interaction):
        cur_category = TEMPUSERDATA.getUser(interaction.user).category

        if cur_category:
            return await interaction.response.send_message(f"Current category is set to {cur_category}.")

        return await interaction.response.send_message("No cateogry is currently selected.")

    @app_commands.command(name = "estimate-shipping", description = "Estimate shipping to zip code")
    async def estimate_shipping(self, interaction: discord.Interaction, id: int, zipcode: str):
        listing = await IdSearch(id).makeRequest()

        shipping_data = await listing.calculateShipping(zipcode)

        embed = Embed(title = "Estimated Shipping and Handling:", description = shipping_data)

        return await interaction.response.send_message(embed = embed, ephemeral = True)

    @isAdmin()
    @app_commands.command(name = "purge", description = "purge messages")
    async def purge(self, interaction: discord.Interaction, num_msgs:int):
        await interaction.channel.purge(limit = num_msgs)
        await interaction.response.send_message(f"Purged {num_msgs} messages", delete_after = 5.0)