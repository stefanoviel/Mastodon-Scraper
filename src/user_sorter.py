# sorter
    # list of all instances
    # get user send it to instance
    # when new instance create class


import re
import asyncio
import aiohttp
import logging
from src.manageDB import ManageDB

class UserSorter: 

    def __init__(self, id_queue: asyncio.Queue,  sort_queue: asyncio.Queue) -> None:
        self.sort_queue = sort_queue
        self.id_queue = id_queue
        self.current_instances = {}


    def extract_instance_name(self, url): 
        pattern = r"(?<=//)(.*?)(?=/)"

        result = re.search(pattern, url)
        if result:
            return result.group(1)
            

    async def sort(self): 
        user_url  = await self.sort_queue.get()



if __name__ == "__main__": 
    u = UserSorter(asyncio.Queue, asyncio.Queue)
    u.extract_instance_name('https://mastodon.cloud/@Brenda45465')

