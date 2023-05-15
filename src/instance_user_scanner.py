import asyncio
import aiohttp
import logging
from src.manageDB import ManageDB

class InstanceScanner: 

    def __init__(self, instance_name:str, id_queue: asyncio.Queue,  sort_queue: asyncio.Queue, manageDB : ManageDB, request_every_five = 280) -> None:
        self.instance_name = instance_name
        self.id_queue = id_queue
        self.sort_queue = sort_queue
        self.follower_queue = asyncio.Queue()
        self.following_queue = asyncio.Queue()
        self.manageDB = manageDB

        self.request_every_five_min = request_every_five
        
        logging.basicConfig(level=logging.INFO)

    async def add_id_following_follower_queue(self, user_id): 
        await self.follower_queue.put('https://{}/api/v1/accounts/{}/followers/'.format(self.instance_name, user_id))
        await self.following_queue.put('https://{}/api/v1/accounts/{}/following/'.format(self.instance_name, user_id))


    async def get_id_from_url(self, session, username) -> None:
        """get id of users from username, put them in following follower queue and save user info"""
        url = 'https://{}/api/v2/search/?q={}'.format(self.instance_name, username) 

        async with session.get(url, timeout=5) as response:
            res = await response.json()
        if len(res['accounts']) > 0: 
            await self.add_id_following_follower_queue(res['accounts'][0]['id'])
            await self.save_users([res['accounts'][0]])


    async def get_following_followers(self, session: aiohttp.ClientSession, url: str) -> None:
        """get element from following follower queue and query some pages save results in sort queue"""

        params = {'limit': 80}
        try: 
            async with session.get(url, params = params, timeout=5) as response:
                res = await response.json() # list of followers and followings and their info

                if 'next' in response.links.keys():
                    new_url = str(response.links['next']['url'])
                    logging.debug('adding {} to queue '.format(new_url))
                                
                    if 'followers' in new_url: 
                        await self.follower_queue.put(new_url)
                    elif 'following' in new_url: 
                        await self.following_queue.put(new_url)

            if len(res) > 0: 
                await self.save_users(res)
                await self.sort_new_users(res)

        except asyncio.exceptions.TimeoutError: 
            logging.debug('Timeout error')

            
    async def sort_new_users(self, user_list): 
        for user in user_list: 
            if self.instance_name in user['url']:                 
                await self.add_id_following_follower_queue(user['id'])
            else: 
                await self.sort_queue.put(user['url'])

    async def save_users(self, user_list:list[dict]): 
        posts = []
        for r in user_list: 
            r["_id"] = r["url"].replace("https://", '')
            if not self.manageDB.is_in_archive(r['_id']): 
                posts.append(r)

        self.manageDB.insert_many_to_archive(posts)

    async def request_ids(self, tasks: list, session: aiohttp.ClientSession, n_request:int) -> int: 
        """Gets id of the users from the id queue, add saves corresponding urls to followers and following queue"""
        for completed_requests in range(n_request): 
            if not self.id_queue.empty(): 
                name = await self.id_queue.get()
                tasks.append(asyncio.create_task(self.get_id_from_url(session, name)))
            else: 
                break

        return round((self.request_every_five_min - completed_requests)/2)  # use remaining requests for followers and following



    async def request_follower_following(self, tasks: list, session: aiohttp.ClientSession, n_request: int) -> None: 
        """gets urls from follower and following queue, gets next page and saves new users in db"""
        followers_request_completed = False
        while n_request > 0:  
            logging.debug(n_request)
            if not self.follower_queue.empty(): 
                url = await self.follower_queue.get()
                tasks.append(asyncio.create_task(self.get_following_followers(session, url)))
            else: 
                n_request += 1 # one more query
                followers_request_completed = True

            if not self.following_queue.empty(): 
                url = await self.following_queue.get()
                tasks.append(asyncio.create_task(self.get_following_followers(session, url)))
            else: 
                n_request += 1
                if followers_request_completed: 
                    break

            n_request -= 2


    async def main(self): 
        """makes both request for id and follower following then waits 5 mins to not finish max requests"""
        async with aiohttp.ClientSession(trust_env=True) as session:
            while not self.follower_queue.empty() or not self.id_queue.empty or not self.following_queue.empty(): 
                
                tasks = []
                n_request = 240
                n_request = await self.request_ids(tasks, session, n_request)
                await self.request_follower_following(tasks, session, n_request)
                await asyncio.gather(*tasks)

                await asyncio.sleep(310)


if __name__ == "__main__": 
    pass
