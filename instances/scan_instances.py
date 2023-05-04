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
        self.get_info_queue = asyncio.Queue(5000)
        self.get_peers_queue = asyncio.Queue(5000)

        self.MAX_DEPTH = 2

        self.logger = logging.getLogger('scan_instances')
        self.logger.setLevel(logging.DEBUG)

        asyncio.run(self.load_queues())

        if self.get_info_queue.empty(): 
            asyncio.run(self.get_info_queue.put(("mastodon.social", 0)))


    async def save_queues(self): 
        with open('data/instances/get_info_queue.txt', 'w') as f:
            while not self.get_info_queue.empty(): 
                elem = await self.get_info_queue.get()
                f.write(str(elem[0]) + ',' + str(elem[1]))
        
        with open('data/instances/get_peers_queue.txt', 'w') as f:
            while not self.get_peers_queue.empty(): 
                elem = await self.get_peers_queue.get()
                f.write(str(elem[0]) + ',' + str(elem[1]))


    async def load_queues(self): 
        for elem in open('data/instances/get_info_queue.txt').read().splitlines(): 
            elem = elem.split(',')
            await self.get_info_queue.put((elem[0], elem[1]))
        
        for elem in open('data/instances/get_peers_queue.txt').read().splitlines(): 
            elem = elem.split(',')
            await self.get_peers_queue.put((elem[0], elem[1]))


    async def fetch_info(self, name, session, is_too_deep):
        try:
            url = 'https://{}/api/v1/instance'.format(name) 
            async with session.get(url, timeout=5) as response:
                return (await response.json(), is_too_deep) 
        except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.ContentTypeError, asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.TooManyRedirects, UnicodeError, ValueError) as e:
            return e, True
        
    async def fetch_peers(self, name, session, is_too_deep):
        try:
            url = 'https://{}/api/v1/instance/peers'.format(name) 
            async with session.get(url, timeout=5) as response:
                return name, eval(await response.json())
        except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.ContentTypeError, asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.TooManyRedirects, UnicodeError, ValueError) as e:
            return name, e

    async def bound_fetch(self, fetching_fun, sem, url, session, is_too_deep):
        # Getter function with semaphore.
        async with sem:
            return await fetching_fun(url, session, is_too_deep)

    async def query_peers(self, num_query):

        sem = asyncio.Semaphore(50)

        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            tasks = []

            for n in range(num_query):

                name = await self.get_peers_queue.get()
                self.logger.debug('peers {} {}'.format(n, name)) 
                tasks.append(asyncio.create_task(self.bound_fetch(self.fetch_peers, sem, name, session, True)))

            results = await asyncio.gather(*tasks)

            tasks.clear()
            
            for name, peers in results:
                if peers is not None:
                    self.manageDb.insert_one_instance_to_network(name, peers)
                    
                    for p in peers: 
                        await self.get_info_queue.put(p)

            results.clear()
            gc.collect()


    async def query_info(self, num_query):

        sem = asyncio.Semaphore(50)

        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            tasks = []
            for n in range(num_query):

                name, depth = await self.get_info_queue.get()
                is_too_deep =  (int(depth) >= self.MAX_DEPTH) 

                self.logger.debug('info {} {} {}'.format(n, name, is_too_deep)) 
                tasks.append(asyncio.create_task(self.bound_fetch(self.fetch_info, sem, name, session, is_too_deep)))

            results = await asyncio.gather(*tasks)
            tasks.clear()
            
            for res, is_too_deep in results: 
                self.manageDb.insert_one_to_archive(res["uri"], res) # save info in archive

                if not is_too_deep: 
                    await self.get_peers_queue.put(res["uri"]) # add instances get_peers queue
                    
            results.clear()
            gc.collect()


    async def main(self): 

        while True: 
            await self.query_info(1000)
            # await self.query_peers(1000)


    def chunks(self, lst, n):
        """Yield successive n-sized chunks from lst."""
        try:
            for i in range(0, len(lst), n):
                yield lst[i:i + n]
        except TypeError as tp:
            return []


if __name__ == "__main__":
    # total = 10000

    # start_time = time.time()
    # tlds = open('data/peers.txt').read().splitlines()
    # urls = ['https://{}/api/v1/instance/peers'.format(x) for x in tlds[31000:50000]]
    # # urls = ['https://google.com'] * 1000
    
    # # need to be divided otherwise too much memory in the list that saves all task
    # for url in chunks(urls, 1000):
    #     asyncio.run(by_aiohttp_concurrency(url.copy()))

    # print("--- It took %s seconds ---" % (time.time() - start_time))

    instances = Instances()
    asyncio.run(instances.main())



