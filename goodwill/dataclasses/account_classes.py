from dataclasses import dataclass
from goodwill.base import baseMakeRequest
from goodwill._encryption import _encrypt_model_value


@dataclass(frozen=True, order=True)
class LoginParams():
    username: str
    password: str
    appVersion: str = "290762033a59e067"
    browser: str = "chrome"
    remember: bool = False

    def toJson(self) -> dict:
        '''
        Converts self into dict obj and returns obj
        '''
        obj = {
            "appVersion": self.appVersion,
            "browser": self.browser,
            "userName": _encrypt_model_value(self.username),
            "password": _encrypt_model_value(self.password),
            "remember": self.remember
        }

        return obj

# Will not be used but exists in case of use
@dataclass(frozen=True, order=True)
class Buyer():
    buyerId: str
    country: str
    email: str
    firstName: str
    lastLoginDate: str
    lastName: str
    login: str
    middleInitial: str


@dataclass(frozen=True, order=True)
class RefreshToken():
    created: str
    createdByIp: str
    expires: str
    token: str


@dataclass(frozen=True, order=True)
class LoginResponse():
    accessToken: str
    isUnconfirmedBuyer: bool
    message: str
    status: bool
    buyer: Buyer = None
    refreshToken: RefreshToken = None


@dataclass(frozen=True, order=True)
class Login():
    params: LoginParams
    BASEURL: str = "https://buyerapi.shopgoodwill.com/api/SignIn/Login"

    async def makeRequest(self):
        json_data = await baseMakeRequest(url=self.BASEURL, json_params = self.params.toJson())

        return LoginResponse(**json_data)


@dataclass(frozen=True, order=True)
class PlaceBidParams():
    bidAmount: str
    itemId: int
    sellerId: int
    accessToken: str
    quantity: int = 1

    def toJson(self) -> dict:
        '''
        Converts self into dict obj and returns obj
        '''
        obj = {
            "bidAmount": self.bidAmount,
            "itemId": self.itemId,
            "quantity": self.quantity,
            "sellerId": self.sellerId,
        }

        return obj


    def getHeader(self):
        return {
            'Authorization': f'Bearer {self.accessToken}',
            'Content-Type': 'application/json'
        }


@dataclass(frozen=True, order=True)
class PlaceBidResponse():
    itemId: int
    message: str 
    result: int
    pastDueMessage = None
    bidIncrement = None
    currentPrice = None
    numBids = None
    status: bool = True
    isUnauthorized: bool = False

    def getResult(self) -> bool:
        '''
        Returns True if you are currently the highest bidder false otherwise.
        '''
        if "outbid" in self.message:
            return False
        
        return True


@dataclass(frozen=True, order=True)
class PlaceBid():
    params: PlaceBidParams
    BASEURL: str = "https://buyerapi.shopgoodwill.com/api/ItemBid/PlaceBid"

    async def makeRequest(self) -> PlaceBidResponse:
        json_data = await baseMakeRequest(
            url=self.BASEURL, 
            json_params = self.params.toJson(),
            headers = self.params.getHeader()
        )

        return PlaceBidResponse(**json_data)

