from discord.ext import commands
import discord
from discord import app_commands, Embed
from math import ceil

from goodwill.dataclasses import IdSearch, KeywordSearch, LoginParams, Login, PlaceBidParams, PlaceBid
from goodwill.db import getQuery

from discord_bot import TEMPUSERDATA
from discord_bot import Embeds
from discord_bot.base import isAdmin, addGuildData, getWebhook
from discord_bot.views import KeywordResults
from discord_bot.reminders import WatchListing

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

    @search_group.command(name = "all", description = "Search all listings using selected category")
    async def searchall(self, interaction: discord.Interaction, keywords: str):
        userdata = TEMPUSERDATA.getUser(interaction.user)

        category = userdata.category if userdata else None

        if category:
            category = getQuery(cat_id = category)

            searchParams = KeywordSearch.initParams(
                paramType = 1,
                catIds = category.getCategoryIds(),
                categoryId = category.categoryId,
                categoryLevel = category.levelNumber,
                categoryLevelNo = str(category.levelNumber),
                searchText = "", # Functionaly the same but searches for everything 
            )

        else:
            searchParams = KeywordSearch.initParams(paramType = 1, st = "")

        searchObject = KeywordSearch(params = searchParams)

        res, total_listings = await searchObject.makeRequest()

        embed = Embeds.page(
            keywords = keywords,
            category = category.categoryName,
            listings =  res[:20],
            page = 1,
            total_pages = ceil(total_listings/40) # 40 listing per page
        )

    @search_group.command(name = "keyword", description='Search by Keyword') # TODO check if keywords is allowed to be default None
    async def searchkey(self, interaction: discord.Interaction, keywords: str = ""):
        userdata = TEMPUSERDATA.getUser(interaction.user)

        category = userdata.category if userdata else None

        if category:
            category = getQuery(cat_id = category)
            categoryName = category.categoryName

            searchParams = KeywordSearch.initParams(
                paramType = 1,
                catIds = category.getCategoryIds(),
                categoryId = category.categoryId,
                categoryLevel = category.levelNumber,
                categoryLevelNo = str(category.levelNumber),
                searchText = keywords,
            )

        else:
            searchParams = KeywordSearch.initParams(paramType = 0, st = keywords)
            categoryName = "None"
        
        searchObject = KeywordSearch(params = searchParams)

        res, total_listings = await searchObject.makeRequest()
        
        embed = Embeds.page(
            keywords = keywords,
            category = categoryName,
            listings =  res[:20],
            page = 1,
            total_pages = ceil(total_listings/40) # 40 listing per page
        )

        return await interaction.response.send_message(
            embed = embed, 
            view = KeywordResults(
                search_object = searchObject, 
                category = categoryName,
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
            embeds.append(Embeds.listing(listing))

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

        listing = await WatchListing.requestListing(itemId = id)

        TEMPUSERDATA.addWatchListing(user = interaction.user, listing = listing)

        await interaction.response.send_message(f'Create a webhook to send reminders for {id}', ephemeral = True)

    @app_commands.command(name="stopwatchlisting", description = "Stop watchlisting")
    async def stopwatch(self, interaction: discord.Interaction, id: str):
        
        watchListing = TEMPUSERDATA.removeWatchListing(interaction.user, listingId = id)

        await interaction.response.send_message(f"Removed watchlisting for listing: {watchListing.listing.itemId}", ephemeral = True)


    @app_commands.command(name = "select-category", description = "Set categories to search") 
    async def add(self, interaction: discord.Interaction, category_id: str):
        category = getQuery(cat_id = category_id)

        if not category:
            await interaction.response.send_message(f"Category not found for id: {category_id}", delete_after = 10)

        userData = TEMPUSERDATA.getUser(interaction.user) 
        
        if userData:
            userData.category = category.categoryId

        else:
            TEMPUSERDATA.addUser(interaction.user, category.categoryId)

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
    @app_commands.command(name = "place-bid", description = "Places max bid on listing using given credentials, credentials are NOT stored.")
    async def placeBid(self, interaction: discord.Interaction, maxbid: int, itemid:int, username: str, password: str):
        loginParams = LoginParams(username = username, password = password)

        res = await Login(params = loginParams).makeRequest()

        access_token = res.accessToken

        listing = await IdSearch(itemId = itemid).makeRequest()

        placeBidParams = PlaceBidParams(bidAmount = str(maxbid), itemId = itemid, sellerId = listing.sellerId, accessToken = access_token)

        response = await PlaceBid(params = placeBidParams).makeRequest()

        return await interaction.response.send_message(embed = await Embeds.bid_response(response.getResult(), listing))


    @isAdmin()
    @app_commands.command(name = "purge", description = "purge messages")
    async def purge(self, interaction: discord.Interaction, num_msgs:int):
        await interaction.channel.purge(limit = num_msgs)
        await interaction.response.send_message(f"Purged {num_msgs} messages", delete_after = 5.0)