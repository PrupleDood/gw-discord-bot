from typing import Any, Callable
import re

import traceback

import discord  
from discord import SelectOption, Interaction, Thread, ThreadMember, ForumChannel, PartialEmoji
from discord.ui import View, button, Button, Select
from discord.ui.item import Item

from goodwill.db import getAllCategories, getCategoriesByPar, hasChildren, getQuery
from goodwill.dataclasses import Category, KeywordSearch, Listing

from discord_bot.base import pageEmbed


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



class KeywordResults(View):
    
    def __init__(self, search_object: KeywordSearch, category: str, listings: list[Listing], timeout: float | None = 180):
        super().__init__(timeout=timeout)

        self.add_item(LeftButton())
        self.add_item(RightButton())

        self.search_object = search_object
        self.category = category
        self.listings = listings

        self.get_listings = lambda l : l[:20] if self.page_half % 2 != 0 else l[20:]
        
        self.page_half = 1
        self.page = 1


    async def getPage(self, interaction: discord.Interaction):

        if self.search_object.params.page != str(self.page):
            self.search_object.params.page = str(self.page)

            try:
                response = await self.search_object.makeRequest()

            except ValueError as e:
                return await interaction.response.send_message(f"Error: {e}")

            if len(response) == 0:
                return await interaction.response.send_message("No more pages", ephemeral = True)
            
            self.listings = response

        return await interaction.response.edit_message(
            embed = pageEmbed(
                keywords = self.search_object.params.searchText,
                category = self.category,
                listings = self.get_listings(self.listings),
                page = self.page 
            ), 
            view = self
        )


    async def on_error(interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)    