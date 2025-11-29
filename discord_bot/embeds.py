import discord
from discord import Embed
from goodwill.dataclasses import Listing, IdSearch


async def bid_response(response: bool, listing: Listing):

    embed = Embed(title = f"Bid for {listing.title}", colour=discord.Color.blue())

    listing_update = await IdSearch(itemId = listing.itemId).makeRequest()

    desc = f"You are currently the highest bidder!" if response else "You have already been outbid."

    embed.add_field(name = "Product Id", value = listing.itemId)
    embed.add_field(name = "Current Price", value = listing_update.currentPrice)
    embed.add_field(name = desc, value = "")

    return embed


def page(
        keywords, category, listings: list[Listing], 
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


def listing(listing: Listing) -> Embed: 
    embed = Embed(title = listing.title, description = listing.description, colour=discord.Colour.blue())
    
    embed.add_field(name = 'Current Price', value = listing.currentPrice, inline = True)
    embed.add_field(name = "Remainging Time", value = listing.remainingTime)
    embed.add_field(name = "Ending", value = listing.endTime) 

    embed.set_footer(text = listing.url)

    if isinstance(listing, Listing):
        url = f"https://shopgoodwillimages.azureedge.net/production/{listing.imageUrlString.split(';')[0]}"
        embed.set_image(url = url) 
    
    return embed
