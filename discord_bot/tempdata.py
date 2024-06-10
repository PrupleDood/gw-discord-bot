import asyncio
from datetime import datetime, timedelta

from discord import User

from goodwill.dataclasses import Category

class UserData():
    
    expiration: datetime
    category: Category | None
    id: int
    datalist: list

    def __init__(self, category: Category, id: int, datalist: list) -> None:
        self.category = category
        self.id = id

        self.datalist = datalist # Used to delete itself when expired

        # Set expiration date to 10 mins from now
        self.expiration = datetime.now() + timedelta(minutes = 10.0)

        self.task = self._checkExpiration() # TODO double check that this works

    def _checkExpiration(self):
        '''
        Loop which waits for expiration of data and then deletes itself.
        '''
        
        async def taskExpiration(expiration, obj: UserData):
            while True:
                if datetime.now() > expiration:
                    break

                await asyncio.sleep(60)

            obj.delete() 

        return asyncio.create_task(taskExpiration(self.expiration, self))

    def _resetExpiration(self):
        self.expiration = datetime.now() + timedelta(minutes = 10.0)
    
    def __eq__(self, __value: 'UserData') -> bool:
        return isinstance(__value, (UserData, User)) and self.id == __value.id

    def delete(self):
        del self.datalist[self.datalist.index(self)]

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"UserData: {self.id}, {str(self.expiration - datetime.now())}, {self.category}"


class TempDataList():

    def __init__(self) -> None:
        self.datalist : list[UserData] = []        

    def addUser(self, user: User, category: Category | None = None):
        Udata = UserData(
            category = category,
            id = user.id,
            datalist = self.datalist
        )

        if Udata in self.datalist:
            index = [i for i in range(len(self.datalist)) if self.datalist[i].id == user.id][0]
            self.datalist[index] = Udata
            return

        self.datalist.append(Udata)

    def getUser(self, user: User) -> UserData:
        index = self._getUserIndex(user)
        
        if index == None:
            return None
        
        return self.datalist[index]
        
    def _getUserIndex(self, user: User) -> int | None:
        '''
        Used for getting index using a discord.User obj rather than UserData
        '''
        i = [i for i in range(len(self.datalist)) if self.datalist[i].id == user.id]

        if len(i) == 0:
            return None
        
        return i[0]