from typing import Any

from math import ceil
import traceback

import random


import discord  
from discord import Interaction
from discord.ui import View, Button 

from goodwill.dataclasses import KeywordSearch, Listing, ItemListingDataParams, ItemListingParams

from discord_bot import Embeds


class LeftButton(Button):

    def __init__(self):
        self.view : KeywordResults

        super().__init__(emoji = u"\u2B05")

    async def callback(self, interaction: Interaction) -> Any:

        self.view.page_half -= 1

        if self.view.page_half == 0:
            if self.view.page == 1:
                self.view.page_half = 1
                return await interaction.response.send_message("Cannot go any further!", ephemeral = True)
            
            self.view.page_half = 2
            self.view.page -= 1

        return await self.view.getPage(interaction = interaction)


class RightButton(Button):

    def __init__(self):
        self.view : KeywordResults

        super().__init__(emoji = u"\u27A1")

    async def callback(self, interaction: Interaction) -> Any:
        
        self.view.page_half += 1

        if self.view.page_half == 3:
            
            self.view.page_half = 1
            self.view.page += 1

        return await self.view.getPage(interaction = interaction)

class FilterSelect(discord.ui.Select):

    def __init__(self, placeholder: str, options: list[discord.SelectOption]):
        
        super().__init__(placeholder = placeholder, options = options)


    async def callback(self, interaction: Interaction) -> Any:
        self.view : KeywordResults

        values = self.values[0].split("|")      
        
        if self.view.filter != self.values[0]:
            self.view.filter = self.values[0]

            self.placeholder = self.view.filterDict[self.view.filter]

            search_obj = self.view.search_object

            if isinstance(search_obj.params, ItemListingParams):
                self.view.search_object.params.sortColumn = values[0]
                self.view.search_object.params.sortDescending = values[1]

            else:
                self.view.search_object.params.sc = values[0]
                self.view.search_object.params.sd = values[1]
            
            self.view.search_object.params.page = "1" # Rest page number 

            await self.view.updateListings(interaction) # Update listings 
            return await self.view.getPage(interaction) # Update message

        else:
            # If there are no changes use default callback to avoid error message
            return await super().callback(interaction)
        


class FilterButton(Button):

    def __init__(self, filterDict: dict, curFilter: str):
        self.view : KeywordResults

        self.active = False

        self.selectObj = FilterSelect(
            placeholder = filterDict[curFilter],
            options = [
                discord.SelectOption(label = label, value = value) 
                for value, label in filterDict.items()
            ]
        )

        super().__init__(label = "Filter")


    async def callback(self, interaction: Interaction) -> Any:

        self.active = not self.active

        if self.active:
            self.view.add_item(self.selectObj)

        else:
            self.view.remove_item(self.selectObj)

        return await interaction.response.edit_message(
            embeds = interaction.message.embeds,
            view = self.view
        )

    
class KeywordResults(View):
    
    def __init__(self, search_object: KeywordSearch, category: str, listing_data: tuple[list[Listing], int], timeout: float | None = 180):
        super().__init__(timeout=timeout)

        self.add_item(LeftButton())
        self.add_item(RightButton())

        listings, total_listings = listing_data

        self.search_object = search_object
        self.category = category
        self.listings = listings
        self.total_listings = total_listings

        self.get_listings = lambda l : l[:20] if self.page_half % 2 != 0 else l[20:]
        
        self.page_half = 1
        self.page = 1

        self.filter = "1|false"
        self.filterDict = {
            "1|false": "Time: Ending Soonest",
            "1|true": "Time: Newly Listed",
            "3|true": "Bids: Most First", # For whatever reason most bids is reversed instead of least
            "3|false": "Bids: Least First",
            "4|false": "Price: Lowest First",
            "4|true": "Price: Highest First",
        }
        
        self.add_item(FilterButton(self.filterDict, self.filter))


    async def getPage(self, interaction: discord.Interaction):

        if self.search_object.params.page != str(self.page):
            self.search_object.params.page = str(self.page)

            await self.updateListings(interaction)

        if isinstance(self.search_object.params, ItemListingParams):    
            searchText = self.search_object.params.searchText
        
        else:
            searchText = self.search_object.params.st

        return await interaction.response.edit_message(
            embed = Embeds.page(
                keywords = searchText,
                category = self.category,
                listings = self.get_listings(self.listings),
                page = self.page,
                total_pages = ceil(self.total_listings / 40)
            ), 
            view = self
        )


    async def updateListings(self, interaction: discord.Interaction):
        try:
            response, total_listings = await self.search_object.makeRequest()

        except ValueError as e:
            return await interaction.response.send_message(f"Error: {e}", ephemeral = True)

        if len(response) == 0:
            return await interaction.response.send_message("No more pages", ephemeral = True)
            
        self.listings = response
        self.total_listings = total_listings



    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)    