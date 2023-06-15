# until both queue are empty
# gets instances info queueu fetch values save results
# add working instances peers queue

import aiohttp
import asyncio

from src.manage_db.manage_mongo_db import ManageDB


class FetchInstanceInfo:

    def __init__(self, info_queue: asyncio.Queue, peers_queue: asyncio.Queue, manageDB: ManageDB, max_depth: int) -> None:
        self.info_queue = info_queue
        self.peers_queue = peers_queue
        self.manageDB = manageDB

        self.MAX_DEPTH = max_depth

    async def fetch_info(self, session, instance_name, depth):
        """Fetch info of instance given name"""

        try:
            url = 'https://{}/api/v1/instance'.format(instance_name)
            async with session.get(url) as response:
                return await response.json(), depth

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

            return {"uri": instance_name, "error": str(e)}, depth

    async def save_info_results_add_to_peers_queue(self, results):

        for instance_info, depth in results:

            # save even if there was an error in fetching from API
            if instance_info is not None and 'uri' in instance_info and not self.manageDB.is_present_in_archive(instance_info["uri"]):
                instance_info['depth'] = depth
                self.manageDB.save_element_to_archive(
                    instance_info["uri"], instance_info)

                if depth < self.MAX_DEPTH and 'error' not in instance_info:
                    await self.peers_queue.put((instance_info["uri"], depth))

    async def loop_through_info_queue_and_fetch(self, save_every_n):

        tasks = []
        save_every_countdown = save_every_n

        # limits number of simultaneous connectios to 50, close every connection after recieving response
        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:

            while not self.info_queue.empty() or not self.peers_queue.empty():
                # save_every_countdown -= 1
                print(self.info_queue.empty(), self.peers_queue.empty())
                instance_name, depth = await self.info_queue.get()

                print('after get')
                tasks.append(asyncio.create_task(self.fetch_info(session, instance_name, depth)))

                # if both peers and info queue we'll wait forever in the info_queue.get(), so we save results and add to peers queue
                if save_every_countdown == 0 or (self.peers_queue.empty() and self.info_queue.empty()): 
                    results = await asyncio.gather(*tasks)
                    save_every_countdown = save_every_n
                #     # self.save_info_results_add_to_peers_queue(results)

