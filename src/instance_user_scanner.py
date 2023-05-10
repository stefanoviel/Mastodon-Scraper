# instance class
    # followers following queue 
    # id queue

    # 280 query every 5 min test

    # save info and network
    # send followers to sorter

import asyncio
import aiohttp
import manageDB

class InstanceScanner: 

    def __init__(self, instance_name:str, id_queue: asyncio.Queue,  sort_queue: asyncio.Queue, manageDB: manageDB) -> None:
        self.instance_name = instance_name
        self.id_queue = id_queue
        self.follower_queue = asyncio.Queue
        self.following_queue = asyncio.Queue
        self.sort_queue = sort_queue
        self.manageDB = manageDB


    async def get_id_from_url(self, session, username) -> None:
        # get element from id_queue and insert results follower folling queue
        url = 'https://{}/api/v2/search/?q={}'.format(self.instance_name, username) 

        # when anwer add this to follower following queue
        # url = 'https://{}/api/v1/accounts/{}/followers/'.format(self.instance_name, account_id) 

    async def get_followers(self, session: aiohttp.ClientSession, url: str) -> None:
        # get element from following follower queue and query some pages save results in sort queue

        params = {'limit': 80}
        async with session.get(url, params = params, timeout=5) as response:
            res = await response.json()

        if 'next' in res.links.keys():
            await self.follower_queue.put(res.links['next']['url'])s
        
        self.manageDB.insert_many_to_archive(ids, info)


    async def get_following(self, session: aiohttp.ClientSession, account_id: str) -> None: 
        # following = instance_name + 'api/v1/accounts/' + \
        #     str(account_id) + '/following/'
        pass

    async def request_manager(self): 
        # execute 280 requests 240 for ids 40 for followers 
        # dynamically set parameters ??? 
        
        async with aiohttp.ClientSession(trust_env=True) as session:
            while not self.following_follower_queue.empty() and not self.id_queue.empty: 
                
                tasks = []

                i = 0
                tot = 20
                while i < tot:  
                    if not self.following_queue.empty(): 
                        id = await self.following_queue.get()
                        tasks.append(asyncio.create_task(self.get_following_urls(session, name)))
                    else: 
                        i -= 1 # one more query

                    if not self.following_queue.empty(): 
                        id = await self.following_queue.get()
                        tasks.append(asyncio.create_task(self.get_following_urls(session, name)))
                    else: 
                        i -= 1

                    i += 2

                for i in range(240): 
                    if not self.id_queue.empty(): 
                        name = await self.id_queue.get()
                        tasks.append(asyncio.create_task(self.get_id_from_url(session, name)))

                await asyncio.sleep(310)



if __name__ == "__main__": 

    tot = 3
    for i in range(tot): 
        if i == 2: 
            tot = 5
        print(i)