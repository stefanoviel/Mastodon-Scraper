import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(sys.path[0], os.pardir)))  # not the cleanest way
import unittest
import asyncio
import aiohttp
from src.manageDB import ManageDB

from src.instance_user_scanner import InstanceScanner

class TestInstanceScanner(unittest.IsolatedAsyncioTestCase): 

    async def asyncSetUp(self): 
        self.instance_name = 'mastodon.social'  # tests are specific for mastodon.social
        self.request_every_five = 280
        self.id_queue = asyncio.Queue()
        self.sort_queue = asyncio.Queue()
        
        self.manageDB = ManageDB('test')
        self.manageDB.reset_collections()

        self.scan = InstanceScanner(self.instance_name, self.id_queue, self.sort_queue, self.manageDB, self.request_every_five)

        with open('tests/data/usernames.txt') as f:
            self.users = f.read().splitlines()

    
    async def test_req_fol_fol_async(self): 
        # get test much bc answer from api is uknown

        await self.scan.follower_queue.put(('https://mastodon.social/@Gargron', 'https://mastodon.social/api/v1/accounts/1/followers/'))
        await self.scan.following_queue.put(('https://mastodon.social/@Gargron', 'https://mastodon.social/api/v1/accounts/1/following/'))

        n_run = 2
        async with aiohttp.ClientSession(trust_env=True) as session:
            for run in range(n_run): 
                user_url, follower_url = await self.scan.follower_queue.get()
                await self.scan.get_following_followers(session, follower_url, user_url)

                if run == 0: # can test only with followers because it is the first being run 
                    # this call will put elements in following queue so it won't be possible to do the same test
                    gargron_followers, user_url = await self.scan.follower_queue.get()
                    print('followers', gargron_followers)
                    self.assertTrue('https://mastodon.social/api/v1/accounts/1/followers?limit=80&max_id' in gargron_followers)
                    self.assertEqual('https://mastodon.social/@Gargron', user_url)

                user_url, following_url = await self.scan.following_queue.get()
                await self.scan.get_following_followers(session, following_url, user_url)


        # each request fetch a URL from the queue and puts a new one in the queue
        self.assertGreater(self.scan.follower_queue.qsize(), 1)
        self.assertGreater(self.scan.following_queue.qsize(), 1)

        # only user from the same instance will go in follower following queue
        self.assertLessEqual(self.scan.follower_queue.qsize(), (80+80)*n_run +1)
        self.assertLessEqual(self.scan.following_queue.qsize(), (80+80)*n_run +1)

        # check all element in db have expected fields
        for user in self.scan.manageDB.archive.find({}): 
            self.assertTrue('id' in user)
            self.assertTrue('username' in user)
    
    async def test_sort_new_user(self): 

        user_list = [{'url': u, 'id':1} for u in self.users]
        await self.scan.sort_new_users(user_list)

        current_instance_n_users = sum(1 for user in self.users if self.instance_name in  user)
        self.assertEqual(self.scan.follower_queue.qsize(), current_instance_n_users)  # user of same instance
        self.assertEqual(self.scan.following_queue.qsize(), current_instance_n_users)
        self.assertEqual(self.scan.sort_queue.qsize(), len(self.users) - current_instance_n_users)


    async def test_get_id_from_url(self): 

        num_requests = 10

        users = [user.replace(self.instance_name + '/', '') for user in self.users if self.instance_name in user][:num_requests]

        if self.instance_name == 'mastodon.social': 
            users.insert(0, '@Gargron')
        num_requests += 1

        async with aiohttp.ClientSession(trust_env=True) as session:
            for user in users: 
                await self.scan.get_id_from_url(session, user)

        # can't test too much because I don't know the answer from the api
        self.assertLessEqual(self.scan.following_queue.qsize(), num_requests)
        self.assertLessEqual(self.scan.follower_queue.qsize(), num_requests)

        if self.instance_name == 'mastodon.social': 
            url, user_url = await self.scan.follower_queue.get()
            self.assertEqual(url, 'https://{}/api/v1/accounts/{}/followers/'.format(self.instance_name, 1))

            url, user_url = await self.scan.following_queue.get()
            self.assertEqual(url, 'https://{}/api/v1/accounts/{}/following/'.format(self.instance_name, 1))



    async def test_request_ids(self): 
        num_requests = 10

        # populating id_queue with usernames
        for user in self.users[:num_requests]: 
            if self.instance_name in user: 
                await self.scan.id_queue.put(user.replace('{}/'.format(self.instance_name), ''))

        tasks = []
        num_id_requested = self.scan.id_queue.qsize()
        async with aiohttp.ClientSession(trust_env=True) as session:
            remaining_requeusts = await self.scan.request_ids(tasks, session, num_requests)

            await asyncio.gather(*tasks)

        self.assertEqual(round(self.request_every_five - num_id_requested), remaining_requeusts)


    async def test_save_network(self): 
        
        with open('tests/data/gargron_followers.txt') as f: 
            follower = json.load(f)        

        with open('tests/data/gargron_following.txt') as f: 
            following = json.load(f)
        
        user_url = 'https://mastodon.social/@Gargron'
        self.scan.save_users([{'url': user_url, 'id':1, 'followers': [], 'following': []}])


        self.scan.save_network(user_url, 'https://mastodon.social/api/v1/accounts/1/followers/', follower)
        self.scan.save_network(user_url, 'https://mastodon.social/api/v1/accounts/1/following/', following)


        user = self.manageDB.archive.find_one({'_id': 'mastodon.social/@Gargron'})
        self.assertEqual(len(user['followers']), len(follower))
        self.assertEqual(len(user['following']), len(following))
        for follower, following in zip(user['followers'], user['following']): 
            self.assertTrue(type(follower) is str)
            self.assertTrue(type(following) is str)


    async def test_main(self): 
        await self.id_queue.put('https://mastodon.social/@Gargron')
        await self.scan.main()

        self.assertEqual(self.id_queue.qsize(), 0)
        self.assertEqual(self.scan.follower_queue.qsize(), 0)
        self.assertEqual(self.scan.following_queue.qsize(), 0)
    

if __name__ == "__main__": 

    unittest.main()