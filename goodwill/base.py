import aiohttp
from aiohttp import ClientResponse

from datetime import timedelta
import regex as re  

# For api response error handeling
def checkResponse(response: ClientResponse):
    if response.status == 200:
        return response, f"Success: 200"

    else:
        print('Error:', response.status) # TODO change this to logging    
        return None, f"Error: {response.status}"
    

# Request Shipping function
async def calculateShipping(itemId, zipCode: str, quantity: int = 1):
    URL = "https://buyerapi.shopgoodwill.com/api/ItemDetail/CalculateShipping"

    json_params = {
        "itemId": itemId,
        "country": "US",
        "province": None, # Only used if shipping to puerto rico
        "zipCode": zipCode,
        "quantity": quantity,
        "clientIP": ""
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url = URL, json = json_params) as response:
            response, message = checkResponse(response)

            # TODO log message here

            if not response:
                raise ValueError(f"Request failed please try again later: {message}")
            
            data = await response.text()

    # Get rid of opening <> and remove dupe spaces
    res_str = re.sub(r"<[^/>]+>", "", data)
    res_str = re.sub(r" {2,4}", "", res_str)

    # Replace closing </> with \n and remove duplicates
    res_str = re.sub(r"<[^>]+>|<[^>]+> ", "\n", res_str)[33:]
    res_str = re.sub(r"\n{2,3}", "\n", res_str)

    # Remove leading whitespace
    res_str = re.sub(r"^ ", "", res_str, flags = re.MULTILINE)

    # Fix address
    adress_index = res_str.index("Address")
    res_str = f"{res_str[:adress_index]}\n{res_str[adress_index:adress_index+8]} {res_str[adress_index+8:]}"

    return res_str


def strpdeltatime(timestr: str):
    if timestr == "Auction Ended":
        return timedelta(days = 0, hours = 0, minutes = 0)

    timelist = [int(time) for time in re.findall( r"[0-9]+(?=[a-zA-Z])", timestr)]

    if len(timelist) == 0: # For buy now listings which return an empty str for this attirbute
        return timedelta(days = 0, hours = 0, minutes = 0)

    if "d" in timestr:
        days, hours = timelist
        return timedelta(days = days, hours = hours)

    if "m" in timestr and "s" not in timestr:
        hours, mins = timelist
        return timedelta(hours = hours, minutes = mins)

    if "m" in timestr and "s" in timestr:
        mins, seconds = timelist
        return timedelta(minutes=mins, seconds = seconds)    

    seconds = timelist[0]

    return timedelta(seconds = seconds)    


async def baseMakeRequest(url: str, json_params: dict = None, req_type: int = 0, headers: dict = None):
    '''
    Used to make requests and returns json response.\n
    Raises ValueError if request failed.\n
    req_type = 0 for post = 1 for get.
    '''
    async with aiohttp.ClientSession() as session:
        session_request = session.post(url, json = json_params) if req_type == 0 else session.get(url)

        async with session_request as response:
            response, message = checkResponse(response)

            # TODO Log message here

            # TODO make it so it returns error
            if not response:
                raise ValueError(f"Request failed please try again later: {message}")
                
            json_data = await response.json()

    return json_data