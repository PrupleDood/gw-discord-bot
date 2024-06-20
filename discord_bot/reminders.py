from dataclasses import dataclass
from datetime import timedelta, datetime

import aiohttp, asyncio
from discord import Thread, User, Guild

from discord_bot import Embeds
from discord_bot.base import getWebhook

from goodwill.dataclasses import SimpleListing

class WatchListing():

    def __init__(self, listing: SimpleListing) -> None:
        self.listing = listing
        self.remainingTime = listing.remainingTime
        self.pollingInterval = self.getInterval()


    async def updateWatchListing(self, guild, thread): 
        webhook, session = await getWebhook(guild)

        embed = Embeds.listing(listing = self.listing)

        await webhook.send(embed= embed, thread = thread)

        await session.close()


    async def terminateWatchListing(self):
        print("Terminating watchlisting")


    async def terminateWatchListing(self, guild, thread):
        webhook, session = await getWebhook(guild)

        embed = Embeds.listing(listing = self.listing)

        await webhook.send(embed= embed, thread = thread)
        await webhook.send(content = f"Listing has ended, winning bid is: {self.listing.currentPrice}")

        await session.close()
    

    def getInterval(self) -> int:
        """
        Calculates an interval for checking a listing based on its remaining time.
        """
        # Define a dictionary mapping time ranges (in seconds) to corresponding intervals
        time_ranges = {
            86400: 7200,  # One day: 2 hours in seconds
            43200: 3600,  # Half day: 1 hour in seconds
            3600: 1800,  # One hour: 30 minutes in seconds
            1800: 900,    # Thirty minutes: 15 minutes in seconds
            900: 60,     # Fifteen minutes: 1 minute in seconds
            0: 30         # Five minutes or less: 30 seconds
        }

        # Ensure remaining time is non-negative (handle negative values if necessary)
        remaining_time = max(0, self.listing.remainingTime.total_seconds())

        # Find the first time range in the dictionary that matches or exceeds the remaining time
        matching_range = next((r for r, interval in time_ranges.items() if remaining_time >= r), 0)

        # Return the corresponding interval
        return time_ranges[matching_range]

    
    async def checkListing(self) -> bool:
        '''
        Checks if the listing has changed.
        '''
        cur_listing = await self.requestListing(self.listing.itemId)

        self.listing = cur_listing
        self.prevPoll, self.remainingTime = datetime.now(), self.listing.remainingTime

        return cur_listing.currentPrice != self.listing.currentPrice


    def checkPoll(self) -> bool:
        '''
        Checks whether or not the polling time has passed returns a bool
        '''
        return self.prevPoll + timedelta(seconds = self.pollingInterval) <= datetime.now()


    def __hash__(self) -> int:
        return self.listing.itemId


    def __eq__(self, value: object) -> bool:
        if not isinstance(value, (WatchListing, int)):
            return False
        
        elif isinstance(value, int):
            return self.listing.itemId == value

        return self.listing.itemId == value.listing.itemId


    @staticmethod
    async def requestListing(itemId):
        URL = "https://buyerapi.shopgoodwill.com/api/ItemDetail/GetItemDetailModelByItemId/"

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{URL}{itemId}") as response:
                json_data = await response.json()

                return SimpleListing.fromDict(json_data)

    
class UserData():
    def __init__(self, uid: int, category: int = None, 
                 watchListings: list[WatchListing] = None, 
                 thread: Thread = None, guild: Guild = None
                ) -> None:

        self.uid = uid
        self.category = category
        self.watchListings = watchListings if watchListings else list()
        self._event = asyncio.Event()
        self.task = None
        self._curPollingInterval = None
        self.thread = thread
        self.guild = guild


    def addWatchListing(self, newListing: SimpleListing) -> None:
        '''
        Should be run if adding a watchListing after initialization to properly alert the checker.
        '''
        watchListing = WatchListing(newListing)
        self.watchListings.append(watchListing)

        if self._curPollingInterval == None:
            self._curPollingInterval = watchListing.getInterval()

        if self.task != None:
            self._event.set()

        else:
            self.startWatchListings()


    async def _waitForUpdateOrTimeout(self, event: asyncio.Event, timeout: float) -> None:
        try:
            # Wait for the event to be set or for the timeout to elapse
            await asyncio.wait_for(event.wait(), timeout=timeout)
            event.clear()

        except asyncio.TimeoutError:
            return


    def getPollingInterval(self) -> int:
        '''
        Creates a set containing waiting intervals from all watchListings and returns min value.
        '''
        pollingIntervals = set([])

        for watchListing in self.watchListings:
            pollingIntervals.add(watchListing.getInterval())

        return min(pollingIntervals)


    def startWatchListings(self):
        '''
        Starts checkListings loop using asyncio.create_task and assigns the returned value to self.task
        '''
        self.task = asyncio.create_task(self.checkListings())


    async def checkListings(self):
        cur_polling_interval = self.getPollingInterval()

        while len(self.watchListings) > 0:
            # list of indexes of watchlistings which have expired
            expired: list[int] = []

            for i in range(len(self.watchListings)):
                watchListing = self.watchListings[i]

                # Skip if polling intreval is less than the watchlistings interval
                if watchListing.pollingInterval < cur_polling_interval and not watchListing.checkPoll():
                    continue

                # Update listing with most recent data
                changed = await watchListing.checkListing()

                if watchListing.remainingTime == timedelta(seconds = 0):
                    await watchListing.terminateWatchListing()
                    expired.append(i)
                    continue


                if changed:
                    await watchListing.updateWatchListing()

            # Removes all expired watchlistings
            [self.watchListings.pop(i) for i in expired[::-1]]

            await self._waitForUpdateOrTimeout(event= self._event, timeout = self.getPollingInterval())

        # Remove variables used for wathlistings
        self._curPollingInterval = None
        self._event = None


    def __hash__(self) -> str:
        return f'{self.uid}'
    

@dataclass()
class TempDataList():
    datalist : list[UserData]
    _setdata : set = None

    def initList(self):
        self._setdata = set([user.uid for user in self.datalist])


    def addUser(self, user: User, category: int = None, watchListings: list[WatchListing] = None):
        
        if user in self._setdata:
            raise ValueError("User already has data added")

        self._setdata.add(user.id)

        userData = UserData(
            uid = user.id, 
            category = category,
            watchListings = watchListings
        )

        if watchListings and len(watchListings) > 0:
            userData.startWatchListings()

        self.datalist.append(userData)

        return self.datalist[-1]


    def _getUserIndex(self, user: int) -> int:
        '''
        Used for getting index using a discord.User obj rather than UserData
        '''
        if user not in self._setdata:
            raise ValueError("User has not been added to datalist or has expired")

        i = [i for i in range(len(self.datalist)) if self.datalist[i].uid == user]

        if len(i) == 0:
            return None
        
        return i[0]


    def getUser(self, user: User):
        return self.datalist[self._getUserIndex(user.id)]


    def addWatchListing(self, user: User, listing: SimpleListing) -> None:
        if user in self._setdata:
            userData = self.getUser(user)
        
        else:
            userData = self.addUser(user = user)

        userData.addWatchListing(listing)


    def removeWatchListing(self, user: User, listingId: int) -> WatchListing:
        '''
        Removes watchlisting from userdata list and returns removed watchlisting
        '''
        if user not in self._setdata:
            raise ValueError("User has not been added to datalist or has expired")

        userData = self.getUser(user)

        if listingId not in set(userData.watchListings):
            raise ValueError("Listing was not being watched")

        else:
            watchListingIndex = userData.watchListings.index(listingId)

            return userData.watchListings.pop(watchListingIndex)


    def setCategory(self, user, categoryId: int):
        if user not in self._setdata:
            raise ValueError("User has not been added to datalist or has expired")

        userData = self.getUser(user)

        userData.category = categoryId
