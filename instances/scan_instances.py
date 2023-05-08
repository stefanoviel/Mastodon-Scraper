from manageDB import ManageDB
import logging
import asyncio
import aiohttp
import gc
import time
import idna


class Instances:

    def __init__(self) -> None:
        self.manageDb = ManageDB()
        self.info_queue = None
        self.peers_queue = None

        self.MAX_DEPTH = 2

        logging.basicConfig(level=logging.INFO)

    async def save_queues(self):
        logging.debug('saving queue')
        with open('data/instances/get_info_queue.txt', 'w') as f:
            while not self.info_queue.empty():
                elem = await self.info_queue.get()
                f.write(str(elem[0]) + ',' + str(elem[1]) + '\n')

        with open('data/instances/get_peers_queue.txt', 'w') as f:
            while not self.peers_queue.empty():
                elem = await self.peers_queue.get()
                f.write(str(elem[0]) + ',' + str(elem[1]) + '\n')

    async def load_queues(self):
        for elem in open('data/instances/get_info_queue.txt').read().splitlines():
            elem = elem.split(',')
            await self.info_queue.put((elem[0], elem[1]))

        for elem in open('data/instances/get_peers_queue.txt').read().splitlines():
            elem = elem.split(',')
            await self.peers_queue.put((elem[0], elem[1]))

    async def fetch_info(self, name, session, depth):
        """Fetch function to get info of instance"""
        try:
            url = 'https://{}/api/v1/instance'.format(name)
            async with session.get(url, timeout=5) as response:
                return await response.json(), depth
        except (SyntaxError, aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.ContentTypeError, asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.TooManyRedirects, UnicodeError, ValueError) as e:
            return {"error": e}, True

    async def fetch_peers(self, name, session, depth):
        """Fetch function to get peers of instance"""
        try:
            url = 'https://{}/api/v1/instance/peers'.format(name)
            async with session.get(url, timeout=5) as response:
                return name, eval(await response.text()), depth
        except (SyntaxError, aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.ContentTypeError, asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.TooManyRedirects, UnicodeError, ValueError) as e:
            return name, {"error": e}, depth

    async def bound_fetch(self, fetching_fun, sem, url, session, depth):
        """Getter function with semaphore, to limit number of simultaneous requests"""
        async with sem:
            return await fetching_fun(url, session, depth)

    async def query_peers(self, save_result_every_n):
        """Loop to continuosly query peers, it add the peers to the info_queue"""
        sem = asyncio.Semaphore(50)

        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            tasks = []

            # if len(info_queue) == 0 and only one elem in peers_queue it would loop forever
            # take min to save sooner
            save_every = min(save_result_every_n, self.peers_queue.qsize())

            logging.debug('peers - iterations {}'.format(save_every))

            first = True
            i = 0
            while True:
                if save_every == 0:
                    save_every = 1
                elif self.info_queue.qsize() < 1000 and not first:  # in first iteration info_queue is empty
                    save_every = 1000

                i += 1

                logging.debug('peers - waiting')
                name, depth = await self.peers_queue.get()
                logging.debug('peers - {} {}'.format(i, name))

                if not self.manageDb.is_in_network(name):
                    tasks.append(asyncio.create_task(self.bound_fetch(
                        self.fetch_peers, sem, name, session, depth)))

                if i == save_every:
                    logging.info('query executed with {}'.format(save_every))
                    save_every = min(save_result_every_n,
                                     self.peers_queue.qsize())
                    logging.debug('peers - iterations {}'.format(save_every))
                    i = 0

                    results = await asyncio.gather(*tasks)
                    tasks.clear()

                    for name, peers, depth in results:

                        if peers is not None and 'error' not in peers:
                            self.manageDb.insert_one_instance_to_network(
                                name, peers, depth)

                            logging.info(
                                'peers - adding to queue the peers of {}'.format(name))
                            for p in peers:
                                # logging.debug('adding peer {} to info_queue if not in archive: {}'.format(p,self.manageDb.is_in_archive(p)))
                                if not self.manageDb.is_in_archive(p):
                                    await self.info_queue.put((p, int(depth) + 1))

                    results.clear()
                    gc.collect()
                    logging.debug('peers - done')
                    # await self.save_queues()

    async def query_info(self, save_result_every_n):
        """Loop to continuosly query info of instances, it add the peers to the peers_queue"""

        sem = asyncio.Semaphore(100)

        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            tasks = []

            # if len(info_queue) == 0 and only one elem in peers_queue it would loop forever
            # take min to save sooner
            save_every = min(save_result_every_n, self.info_queue.qsize())

            logging.debug('info - iterations {}'.format(save_every))
            i = 0
            while True:
                if save_every == 0:
                    save_every = 1
                i += 1

                logging.debug('info - waiting')
                name, depth = await self.info_queue.get()
                logging.debug('info - {} {} {}'.format(i, name, depth))

                tasks.append(asyncio.create_task(self.bound_fetch(
                    self.fetch_info, sem, name, session, int(depth))))

                if i == save_every:

                    save_every = min(save_result_every_n,
                                     self.info_queue.qsize())
                    logging.debug(
                        'info - iterations {} {}'.format(save_result_every_n, self.info_queue.qsize()))
                    i = 0

                    results = await asyncio.gather(*tasks)
                    tasks.clear()

                    for res, depth in results:
                        if res is not None and 'error' not in res and 'uri' in res:
                            self.manageDb.insert_one_to_archive(
                                res["uri"], res)

                            if depth < self.MAX_DEPTH:
                                logging.debug(
                                    'info - adding to peers_queue {} {}'.format(res['uri'], depth))
                                # add instances get_peers queue
                                await self.peers_queue.put((res["uri"], depth))

                    logging.info('infoQ has length {} peersQ has length {}'.format(
                        self.info_queue.qsize(), self.peers_queue.qsize()))
                    results.clear()
                    gc.collect()
                    # await self.save_queues()

    async def batch(self):

        # only way it can explode is if get_peers queue becomes too big
        # to fix just save those in memory
        self.info_queue = asyncio.Queue(20000)
        self.peers_queue = asyncio.Queue()

        await self.load_queues()

        if self.info_queue.empty():
            await self.info_queue.put(("mastodon.social", 0))

        await asyncio.gather(self.query_info(save_result_every_n=10000), self.query_peers(save_result_every_n=100))

    def main(self):
        asyncio.run(self.batch())

    def chunks(self, lst, n):
        """Yield successive n-sized chunks from lst."""
        try:
            for i in range(0, len(lst), n):
                yield lst[i:i + n]
        except TypeError as tp:
            return []


if __name__ == "__main__":
    instances = Instances()
    instances.manageDb.reset_collections()
    instances.main()
