import regex as re

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

from goodwill.base import strpdeltatime, calculateShipping, baseMakeRequest

# Category classes 
@dataclass(frozen=True, order=True)
class Category():
    categoryId: int
    categoryName: str

    parentId: Optional[int] = -1
    levelNumber: int = 1
    subCount: int = 0
    children: Optional[str] = None

    def getChildren(self) -> tuple['Category'] | None: # Defined in dby.py to avoid circular import
        '''
        Returns a tuple containing all child categories or None if the Category has none
        '''
        pass

    def getParentCat(self) -> tuple['Category']:
        '''
        Returns tuple containing all parent categories or parent category if there is only one
        '''
        pass

    def getCategoryIds(self) -> str:
        '''
        Returns a str containing all category ids for api request\n
        Ex. -1,456,789 (-1 will be in place of None)
        '''
        pass


@dataclass(frozen=True, order=True)
class SimpleCategory():
    '''
    Category dataclass for use in Listing dataclass.
    '''
    categoryId: int
    categoryParentList: str
    categoryName: str


# Listing classes 
@dataclass(frozen=True, order=True)  
class Listing():
    itemId: int
    categoryData: SimpleCategory 
    sellerId: int

    title: str
    description: str
    remainingTime: timedelta | str
    endTime: datetime

    url: str

    currentPrice: int 
    numBids: int
    minimumBid: int
    buyNowPrice: int # If 0 buyNow is not applicable 
    recentBid: dict = None
    
    quantity: int = 1

    imageServer: str = "https://shopgoodwillimages.azureedge.net/production/"
    imageUrlString: str = None # Used with detailed request

    imageUrl: str = None # Used with non detailed request

    detailed: bool = False

    @staticmethod
    def fromDict(json_data:dict, req_type:int) -> 'Listing':
        '''
        Used for creating listing object and adapting from both forms of the json data.\n
        req_type 0 uses Search/ItemListingData or Search/ItemListing Non-detailed\n
        req_type 1 uses ItemDetail/GetItemDetailModelByItemId/ Detailed
        '''
        # Get the image params
        if req_type == 0:
            image_params = {"imageUrl":json_data["imageURL"]} 
            quantity = json_data["itemQuantity"]
        else:
            image_params = {"imageServer":json_data["imageServer"], "imageUrlString":json_data["imageUrlString"]}
            quantity = json_data["quantity"]

        numBids = json_data["numBids"] if req_type == 0 else json_data["numberOfBids"]

        # Get most recent bid if detailed request
        if req_type == 0:
            recentBid = None
        else:
            recentBid = json_data["bidHistory"]["bidSummary"]
            recentBid = None if len(recentBid) == 0 else recentBid[0]

        catParentList = json_data["catFullName"] if req_type == 0 else " > ".join(re.findall(r"(?<=\|)[^0-9][a-zA-Z &]*", json_data["categoryParentList"]))
        categoryName = json_data["categoryName"] if req_type == 0 else json_data["categoryParentList"].split("|")[-1]
        
        categoryData = SimpleCategory(json_data["categoryId"], catParentList, categoryName)

        try:
            remainingTime = strpdeltatime(json_data["remainingTime"])
        
        except ValueError:
            remainingTime = json_data["remainingTime"]

        listing = Listing(
            itemId = json_data["itemId"], #
            categoryData = categoryData,
            sellerId = json_data["sellerId"],

            title = json_data["title"], #
            description = json_data["description"],  #
            url = f"https://shopgoodwill.com/item/{json_data['itemId']}",

            remainingTime = remainingTime,
            endTime = datetime.fromisoformat(json_data["endTime"]).strftime("%b, %d, %I:%M"),

            currentPrice = json_data["currentPrice"], #
            buyNowPrice = json_data["buyNowPrice"] if json_data["buyNowPrice"] != 0 else -1,
            quantity = quantity,
            recentBid = recentBid,
            numBids = numBids,
            minimumBid = json_data["minimumBid"], #

            detailed = False if req_type == 0 else True,

            **image_params,
        )

        return listing

    async def calculateShipping(self, zipCode: str, quantity: int = 1):
        return await calculateShipping(self.itemId, zipCode, quantity)


@dataclass(frozen=True, order=True) 
class SimpleListing():
    title: str

    itemId: int
    categoryData: SimpleCategory

    remainingTime: timedelta
    endTime: datetime

    url: str

    currentPrice: int
    recentBid: dict = None

    @staticmethod
    def getCategoryName(data: dict):
        pass # Defined in db.py to avoid circular import

    @staticmethod
    def fromDict(json_data: dict):
        catParentList = " > ".join(re.findall(r"(?<=\|)[^0-9][a-zA-Z &]*", json_data["categoryParentList"]))

        categoryData = SimpleCategory(
            json_data["categoryId"], 
            catParentList, 
            SimpleListing.getCategoryName(json_data) # Used to avoid key error
        )

        recentBid = json_data["bidHistory"]["bidSummary"]
        recentBid = None if len(recentBid) == 0 else recentBid[0]

        return SimpleListing(
            title = json_data["title"],
            itemId = json_data["itemId"],
            categoryData = categoryData,
            remainingTime = strpdeltatime(json_data["remainingTime"]),
            endTime = datetime.fromisoformat(json_data["endTime"]).strftime("%b, %d, %I:%M"),
            currentPrice = json_data["currentPrice"],
            recentBid = recentBid,
            url = f"https://shopgoodwill.com/item/{json_data['itemId']}"
        )


    @staticmethod
    def fromListing(listing: Listing):
        return SimpleListing(
            title = listing.title,  
            itemId = listing.itemId,
            categoryData = listing.categoryData, 
            remainingTime = listing.remainingTime,
            currentPrice = listing.currentPrice,
            recentBid = listing.recentBid,
            url = listing.url
        )


    async def calculateShipping(self, zipCode: str, quantity: int = 1):
        return await calculateShipping(self.itemId, zipCode, quantity)

# Listing api classes
@dataclass(order=True)
class ItemListingParams():
    '''
    Parameters used for requesting pages of listings
    Only parameters that matter are
    catIds, categoryId, categoryLevel, categoryLevelNo = str(categoryLevel), searchText
    '''

    catIds: str
    categoryId: int
    categoryLevel: int
    categoryLevelNo: str 
    page: str = "1"
    closedAuctionDaysBack: str = "7"
    closedAuctionEndingDate: str = datetime.date(datetime.now()) # datetime of current date
    highPrice: str = "999999"
    isFromHeaderMenuTab: bool = False
    isFromHomePage: bool = False
    isMultipleCategoryIds: bool = False
    isSize: bool = False
    isWeddingCatagory: str = "false"
    layout: str = "grid"
    lowPrice: str = "0"
    pageSize: str =  "40"
    partNumber: str = ""
    savedSearchId: int = 0
    searchBuyNowOnly: str = "0" # Requests only auction items
    searchCanadaShipping: str = "false"
    searchClosedAuctions: str = "false"
    searchDescriptions: str = "false"
    searchInternationalShippingOnly: str = "false"
    searchNoPickupOnly: str = "false"
    searchOneCentShippingOnly: str = "false"
    searchPickupOnly: str = "false"
    searchText: str = ""
    searchUSOnlyShipping: str = "false"
    selectedCategoryIds: str = "7"
    selectedGroup: str = ""
    selectedSellerIds: str = ""
    sortColumn: str = "1" # Sorts results "1" time, "3" bids, "4" 
    sortDescending: str = "false"
    useBuyerPrefs: str = "true"

    def toJson(self) -> dict:
        '''
        Converts obj into a json format.
        '''

        obj = {
            "catIds": self.catIds,
            "categoryId": self.categoryId,
            "categoryLevel": self.categoryLevel,
            "categoryLevelNo": self.categoryLevelNo,
            "page": self.page,
            "closedAuctionDaysBack": self.closedAuctionDaysBack,
            "closedAuctionEndingDate": str(self.closedAuctionEndingDate),
            "highPrice": self.highPrice,
            "isFromHeaderMenuTab": self.isFromHeaderMenuTab,
            "isFromHomePage": self.isFromHomePage,
            "isMultipleCategoryIds": self.isMultipleCategoryIds,
            "isSize":self.isSize,
            "isWeddingCatagory": self.isWeddingCatagory,
            "layout": self.layout,
            "lowPrice": self.lowPrice,
            "pageSize": self.pageSize,
            "partNumber":self.partNumber,
            "savedSearchId": self.savedSearchId,
            "searchBuyNowOnly": self.searchBuyNowOnly,
            "searchCanadaShipping": self.searchCanadaShipping,
            "searchClosedAuctions": self.searchClosedAuctions,
            "searchDescriptions": self.searchDescriptions,
            "searchInternationalShippingOnly": self.searchInternationalShippingOnly,
            "searchNoPickupOnly": self.searchNoPickupOnly,
            "searchOneCentShippingOnly": self.searchOneCentShippingOnly,
            "searchPickupOnly": self.searchPickupOnly,
            "searchText": self.searchText,
            "searchUSOnlyShipping": self.searchUSOnlyShipping,
            "selectedCategoryIds": self.selectedCategoryIds,
            "selectedGroup": self.selectedGroup,
            "selectedSellerIds": self.selectedSellerIds,
            "sortColumn": self.sortColumn,
            "sortDescending": self.sortDescending,
            "useBuyerPrefs": self.useBuyerPrefs
        }

        return obj
    
@dataclass(order=True) 
class ItemListing():
    '''Used for requesting pages of listings'''
    params: ItemListingParams 
    BASEURL: str = "https://buyerapi.shopgoodwill.com/api/Search/ItemListing"

    async def makeRequest(self):

        json_data = await baseMakeRequest(url = self.BASEURL, json_params = self.params.toJson())

        items = json_data["searchResults"]["items"]
        num_total : int = json_data["searchResults"]["itemCount"]

        listings = [Listing.fromDict(item, 0) for item in items]

        return listings, num_total
    
@dataclass(order=True)
class ItemListingDataParams():
    '''
    Used for searching from home page with no category selected.    
    '''
    pn: int = 4
    cl: int = 1
    cids: str = None
    scids: str = None
    p: int = 1
    sc: int = 1
    sd: bool = False
    cid: int = 0
    sg: str = "Keyword"
    st: str = ""

    @staticmethod
    def _fixParamItem(item):
        if isinstance(item, bool):
            return str(item).lower()
        
        if item is None:
            return ""
        
        return item

    def toUrl(self):
        url_params = ""
        
        for key, item in self.__dict__.items():
            url_params += f"{key}={self._fixParamItem(item)}&"

        return url_params[:-1]
  
    
@dataclass(order=True)
class ItemListingData():
    '''Used for requesting the first page of a search'''
    params: ItemListingDataParams
    BASEURL: str = "https://buyerapi.shopgoodwill.com/api/Search/ItemListingData"

    async def makeRequest(self):
        json_data = await baseMakeRequest(url = f"{self.BASEURL}?{self.params.toUrl()}", req_type = 1)

        items = json_data["searchResults"]["items"]
        listings = [Listing.fromDict(item, 0) for item in items]

        num_total : int = json_data["searchResults"]["itemCount"]

        return listings, num_total


# Search classes
@dataclass(order=True) 
class KeywordSearch():
    params: ItemListingDataParams | ItemListingParams
    requestObj: ItemListingData | ItemListing = None
    data: list[Listing] = None

    async def makeRequest(self) -> tuple[list[Listing], int]:
        searchType = ItemListingData if isinstance(self.params, ItemListingDataParams) else ItemListing

        self.requestObj = searchType(self.params)

        self.data = await self.requestObj.makeRequest()

        return self.data

    async def getNextPage(self): 
        if not isinstance(self.params, ItemListingParams):
            self.params = ItemListingParams(
                catIds = self.params.cids,
                categoryId = self.params.cid,
                categoryLevel = self.params.cl,
                categoryLevelNo = str(self.params.cl),
                pageNumber = self.pageNum,
                searchText = self.params.st 
            )

            self.requestObj = ItemListing(self.params)

        self.requestObj.params.pageNumber += 1

        self.data, self.num_total = await self.requestObj.makeRequest()

        return self.data

    @staticmethod
    def initParams(paramType: int = 0, **kwargs) -> (ItemListingDataParams | ItemListingParams):
        '''
        Used as an easier way to initialize parameters for Keyword Search.\n
        paramType: int 0 = ItemListingDataParams, 1 = ItemListingParams
        '''

        if paramType == 0:
            return ItemListingDataParams(**kwargs)
        
        else:
            return ItemListingParams(**kwargs)


@dataclass(frozen=True, order=True) 
class IdSearch():
    itemId: int
    BASEURL: str = "https://buyerapi.shopgoodwill.com/api/ItemDetail/GetItemDetailModelByItemId/" 
    
    async def makeRequest(self): 
        url = f"{self.BASEURL}{self.itemId}"

        json_data = await baseMakeRequest(url = url, req_type = 1)

        return Listing.fromDict(json_data, 1)