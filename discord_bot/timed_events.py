from discord import Webhook, ForumChannel
import discord
from goodwill.dataclasses import SimpleListing
from discord_bot.base import getWebhook, listingEmbed

from datetime import timedelta
import asyncio
import aiohttp

# URL https://buyerapi.shopgoodwill.com/api/ItemDetail/GetItemDetailModelByItemId/

async def requestListing(itemId: int):
    URL = "https://buyerapi.shopgoodwill.com/api/ItemDetail/GetItemDetailModelByItemId/"

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{URL}{itemId}") as response:
            json_data = await response.json()

            return SimpleListing.fromDict(json_data)


async def checkListing(prev_listing: SimpleListing):
    cur_listing = await requestListing(prev_listing.itemId)

    if cur_listing.currentPrice != prev_listing.currentPrice:
        return True, cur_listing

    return False, cur_listing


def adjustInterval(listing: SimpleListing):
    
    one_day = timedelta(days = 1)
    half_day = timedelta(hours = 12)
    one_hour = timedelta(hours = 1)
    thirty_mins = timedelta(minutes = 30)
    fifteen_mins = timedelta(minutes = 15)
    five_mins = timedelta(minutes = 5)

    if listing.remainingTime > one_day:
        return 7200 # 2 hours in secs
    elif listing.remainingTime > half_day:
        return 3600 # 1 hour in secs
    elif listing.remainingTime > one_hour:
        return 1800 # 30 mins in secs
    elif listing.remainingTime > thirty_mins:
        return 900 # 15 mins in secs
    elif listing.remainingTime > fifteen_mins:
        return 60 # 1  min in secs
    elif listing.remainingTime > five_mins:
        return 30 # 30 secs

    return 10


async def updateWatchListing( 
        listing: SimpleListing, 
        thread: discord.Thread, 
        guild: discord.Guild
    ): 
    webhook, session = await getWebhook(guild)

    embed = listingEmbed(listing = listing)

    await webhook.send(embed= embed, thread = thread)

    await session.close()


async def terminateWatchListing(
        listing: SimpleListing,
        thread: discord.Thread,
        guild: discord.Guild
    ):
    webhook, session = await getWebhook(guild)

    embed = listingEmbed(listing = listing)

    await webhook.send(embed= embed, thread = thread)
    await webhook.send(content = f"Listing has ended, winning bid is: {listing.currentPrice}")

    await session.close()


async def watchListingPrice(
        listing_id: int, 
        thread: ForumChannel, guild: discord.Guild
    ) -> None:
    '''
    Watches listing for change in price and will make calls to webhook to send update\n
    TODO make it check "recent_bids" for useid and have it ignore if specified by requesting user
    '''
    listing = await requestListing(listing_id)
    polling_interval = adjustInterval(listing)

    await updateWatchListing(listing, thread, guild) # Initial post

    while True:
        changed, listing = await checkListing(listing)

        if listing.remainingTime == timedelta(seconds = 0):
            await terminateWatchListing(listing, thread, guild)
            break

        if changed:
            await updateWatchListing(listing, thread, guild)

        polling_interval = adjustInterval(listing)

        await asyncio.sleep(polling_interval)



