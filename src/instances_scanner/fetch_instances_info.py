# until both queue are empty    
    # gets instances info queueu fetch values save results 
    # add working instances peers queue

import aiohttp 
import asyncio

class FetchInstanceInfo: 

    def __init__(self, info_queue: asyncio.Queue, peers_queue: asyncio.Queue, peers_task) -> None:
        self.info_queue = info_queue
        self.peers_queue = peers_queue

        self.tasks = []
        self.peers_tasks = peers_task


    async def fetch_info(self, session, name): 
        """Fetch info of instance given name"""
        try:
            url = 'https://{}/api/v1/instance'.format(name)
            async with session.get(url) as response:
                return await response.json()
            
        except (aiohttp.client_exceptions.ClientPayloadError,
                aiohttp.client_exceptions.ClientResponseError,
                aiohttp.client_exceptions.ContentTypeError,
                aiohttp.client_exceptions.ClientConnectorError,
                aiohttp.client_exceptions.ServerDisconnectedError, 
                aiohttp.client_exceptions.ClientOSError, 
                aiohttp.client_exceptions.TooManyRedirects, 
                asyncio.exceptions.TimeoutError,
                UnicodeError, 
                SyntaxError,
                ValueError) as e:

            return {"uri": name, "error": str(e)}
        
    
    async def loop_get_from_info_queue_and_fetch(self): 
        
        while not self.info_queue.empty() or not self.peers_queue.empty(): 
            elem, depth = await self.info_queue.get()  


