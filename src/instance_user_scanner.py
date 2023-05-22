import asyncio
import math
import aiohttp
import re
import logging

from src.manageDB import ManageDB


class InstanceScanner:

    def __init__(self, instance_name: str, id_queue: asyncio.Queue,  sort_queue: asyncio.Queue, manageDB: ManageDB, request_every_five=300) -> None:
        self.instance_name = instance_name
        self.id_queue = id_queue
        self.sort_queue = sort_queue
        self.follower_queue = asyncio.Queue()
        self.following_queue = asyncio.Queue()
        self.manageDB = manageDB
        self.manageDB.archive.create_index('instance')
        self.done = False

        self.request_every_five_min = request_every_five

        logging.basicConfig(level=logging.INFO)


    async def add_id_following_follower_queue(self, user_id, user_url):
        await self.follower_queue.put(('https://{}/api/v1/accounts/{}/followers/'.format(self.instance_name, user_id), user_url))
        await self.following_queue.put(('https://{}/api/v1/accounts/{}/following/'.format(self.instance_name, user_id), user_url))

    def extract_username(self, url):
        username = re.search(r'@(.+)', url)
        if username: 
            return username.group(0)
        else: 
            return username

    async def get_id_from_url(self, session, user_url) -> None:
        """get id of users from username, put them in following follower queue and save user info"""

        name = self.extract_username(user_url)
        url = 'https://{}/api/v2/search/?q={}'.format(
            self.instance_name, name)

        try:
            async with session.get(url, timeout=5) as response:
                res = await response.json()

            if 'accounts' in res and len(res['accounts']) > 0:
                await self.add_id_following_follower_queue(res['accounts'][0]['id'], user_url)
                self.save_users([res['accounts'][0]])
        except (asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ContentTypeError, aiohttp.client_exceptions.ClientConnectorCertificateError, aiohttp.client_exceptions.ServerDisconnectedError) as e:
            logging.debug('TIMEOUT')

    async def get_following_followers(self, session: aiohttp.ClientSession, url: str, user_url: str) -> None:
        """get element from following follower queue and query some pages save results in sort queue"""

        params = {'limit': 80}
        try:
            async with session.get(url, params=params, timeout=5) as response:
                res = await response.json()  # list of followers and followings and their info

                if 'next' in response.links.keys():
                    new_url = str(response.links['next']['url'])
                    logging.debug('adding {} to queue '.format(new_url))

                    if 'followers' in new_url:
                        logging.debug('adding {} to queue '.format(new_url))
                        await self.follower_queue.put((new_url, user_url))
                    elif 'following' in new_url:
                        logging.debug('adding {} to queue '.format(new_url))
                        await self.following_queue.put((new_url, user_url))

            if len(res) > 0 and 'error' not in res:  # check there is no too many error
                self.save_users(res)
                self.save_network(user_url, url, res)
                await self.sort_new_users(res)


        except (asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ContentTypeError, aiohttp.client_exceptions.ServerDisconnectedError) as e:
            logging.debug('Timeout error')

    async def sort_new_users(self, user_list):
        for user in user_list:
            if self.instance_name in user['url']:
                await self.add_id_following_follower_queue(user['id'], user['url'])
            else:
                await self.sort_queue.put(user['url'])

    def mongo_id_from_url(self, url: str):
        return url.replace("https://", '')

    def save_users(self, user_list: list[dict]):
        posts = []

        for r in user_list:
            r["_id"] = self.mongo_id_from_url(r["url"])
            r['instance'] = self.instance_name
            r['followers'] = []
            r['following'] = []
            if not self.manageDB.is_in_archive(r['_id']):
                posts.append(r)

        if len(posts) > 0:
            self.manageDB.insert_many_to_archive(posts)

    def save_network(self, user_url: str, url: str,  user_list: list[dict]):
        id = self.mongo_id_from_url(user_url)
        main_user = self.manageDB.get_from_archive(id)

        peers_id = [self.mongo_id_from_url(
            user.get('url')) for user in user_list]
        peers_id = list(filter(lambda item: item is not None, peers_id))

        if main_user:
            if 'followers' in url:
                main_user['followers'].extend(peers_id)
                self.manageDB.update_archive(main_user, True)
            elif 'following' in url:
                main_user['following'].extend(peers_id)
                self.manageDB.update_archive(main_user, False)

    async def request_ids(self, tasks: list, session: aiohttp.ClientSession, n_request: int) -> int:
        """Gets id of the users' name from the id queue, add saves corresponding urls to followers and following queue"""
        for completed_requests in range(n_request):
            if completed_requests < 250 and  not self.id_queue.empty(): 
                user_url = await self.id_queue.get()
                tasks.append(asyncio.create_task(
                    self.get_id_from_url(session, user_url)))
            else:
                break

        # use remaining requests for followers and following
        return math.floor(self.request_every_five_min - completed_requests)

    async def request_follower_following(self, tasks: list, session: aiohttp.ClientSession, n_request: int) -> None:
        """gets urls from follower and following queue, gets next page and saves new users in db"""
        followers_request_completed = False
        while n_request > 0:
            logging.debug(n_request)
            if not self.follower_queue.empty():
                url, user_url = await self.follower_queue.get()

                tasks.append(asyncio.create_task(
                    self.get_following_followers(session, url, user_url)))
                n_request -= 1
            else:
                followers_request_completed = True

            if not self.following_queue.empty():
                url, user_url = await self.following_queue.get()
                tasks.append(asyncio.create_task(
                    self.get_following_followers(session, url, user_url)))
                n_request -= 1
            else:
                if followers_request_completed:
                    break

        return n_request
    
    async def request_id_and_url(self, n_request, session): 

        logging.debug(
            'starting collecting for {}'.format(self.instance_name))
        tasks = []

        if n_request <= 0:
            if self.instance_name == 'mastodon.social': 
                logging.info('{} sleeping 5 minutes..'.format(self.instance_name))
            await asyncio.sleep(310)
            n_request = 300

        n_request = await self.request_ids(tasks, session, n_request)
        await asyncio.gather(*tasks)

        n_request = await self.request_follower_following(tasks, session, n_request)
        await asyncio.gather(*tasks)

        if self.instance_name == 'mastodon.social': 
            logging.info('follower {} following {} id {}'.format(self.follower_queue.qsize(), self.following_queue.qsize(), self.id_queue.qsize()))
            logging.info('collected data for {}, remaining requests {}'.format(self.instance_name, n_request))

        return n_request

    async def main(self):
        """makes both request for id and follower following then waits 5 mins to not finish max requests"""

        n_request = 300

        async with aiohttp.ClientSession(trust_env=True) as session:
            while not self.follower_queue.empty() or not self.id_queue.empty() or not self.following_queue.empty():
                n_request = await self.request_id_and_url(n_request, session)

            self.done = True


if __name__ == "__main__": 
    pass

# TODO first user doesn't get scraped