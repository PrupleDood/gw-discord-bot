from discord import Interaction, User
from discord.ui import Modal, TextInput, Select
from discord.utils import MISSING

from discord_bot.views import KeywordResults
from discord_bot.base import pageEmbed
from discord_bot import TEMPUSERDATA

from goodwill.dataclasses import IdSearch, KeywordSearch, ItemListingDataParams, ItemListing, ItemListingParams, Category

class KeywordSearchModal(Modal, title="Keyword Search"):
    
    keywords = TextInput(
        label = "Keywords",
        placeholder = "Keywords here...",
        required = True,
    )

    def __init__(self, user: User) -> None:
        userdata = TEMPUSERDATA.getUser(user)

        self.category = userdata.category if userdata else None

        super().__init__(custom_id = "KeywordSearch")

    async def on_submit(self, interaction: Interaction) -> None:
        value = self.keywords.value

        if self.category:
            searchParams = ItemListingParams(
                catIds = self.category.getCategoryIds(),
                categoryId = self.category.categoryId,
                categoryLevel = self.category.levelNumber,
                categoryLevelNo = str(self.category.levelNumber),
                searchText = value,
                pageSize = "23"
            )

        else:
            searchParams = ItemListingDataParams(st = value)

        searchObject = KeywordSearch(params = searchParams)

        res = await searchObject.makeRequest()

        embed = pageEmbed(
            keywords = value,
            category = self.category.categoryName,
            listings =  res[:20],
            page = 1
        )

        return await interaction.response.send_message(
            embed = embed, 
            view = KeywordResults(
                search_object = searchObject, 
                category = self.category.categoryName,
                listings = res
            ),
        )






