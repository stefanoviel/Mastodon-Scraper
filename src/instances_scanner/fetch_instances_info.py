# until both queue are empty    
    # gets instances info queueu fetch values save results 
    # add working instances peers queue

import aiohttp 

class FetchInstanceInfo: 

    def __init__(self) -> None:
        pass


    async def fetch_info(self, session, name): 
        url = 'https://{}/api/v1/instance'.format(name)
        async with session.get(url) as response:
            return await response.json()