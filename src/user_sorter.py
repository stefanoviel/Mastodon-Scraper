# sorter
    # list of all instances
    # get user send it to instance
    # when new instance create class


import re
import asyncio
import aiohttp
import logging
from src.instance_user_scanner import InstanceScanner
from src.manageDB import ManageDB

class UserSorter: 

    def __init__(self, id_queue: asyncio.Queue,  sort_queue: asyncio.Queue, manageDB: ManageDB) -> None:
        self.sort_queue = sort_queue
        self.current_instances = {}
        self.manageDB = manageDB
        self.tasks = []

        logging.basicConfig(level=logging.DEBUG)

    def extract_instance_name(self, url): 
        pattern = r"(?<=//)(.*?)(?=/)"

        result = re.search(pattern, url)
        if result:
            return result.group(1)
        
    def extract_username(self, url):
        username = re.search(r'@(.+)', url).group(0)
        return username
    
    def check_all_done(self): 
        for instance_name, instance in self.current_instances.items():
            if not instance.done:
                return False
            
        return True
    

    async def create_instance_scanner(self, instance_name): 

        instance = InstanceScanner(instance_name, asyncio.Queue(), self.sort_queue, self.manageDB)
        self.current_instances[instance_name] = instance_name
        return instance

    async def sort(self): 
        
        # TODO: decide how to make the loop stop
        while True:
            user_url  = await self.sort_queue.get()

            instance_name = self.extract_instance_name(user_url)
            instance = self.current_instances.get(instance_name)

            if instance is None:
                logging.debug('adding instance {}'.format(instance_name))
                instance = await self.create_instance_scanner(instance_name)
                loop = asyncio.get_event_loop()
                loop.create_task(instance.main())

            username = self.extract_username(user_url)
            await instance.id_queue.put(username)

    async def start_with_Gargron(self): 
        await self.sort_queue.put('https://mastodon.social/@Gargron')
        await self.sort()

if __name__ == "__main__": 
    u = UserSorter(asyncio.Queue(), asyncio.Queue(), ManageDB('users'))
    asyncio.run(u.start_with_Gargron())

