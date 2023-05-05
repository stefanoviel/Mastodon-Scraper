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
        self.get_info_queue = None
        self.get_peers_queue = None

        self.MAX_DEPTH = 2

        logging.basicConfig(level=logging.DEBUG)

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


    async def fetch_info(self, name, session, depth):
        try:
            url = 'https://{}/api/v1/instance'.format(name) 
            async with session.get(url, timeout=5) as response:
                return await response.json(), depth
        except (SyntaxError, aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.ContentTypeError, asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.TooManyRedirects, UnicodeError, ValueError) as e:
            return {"error": e}, True
        
    async def fetch_peers(self, name, session, depth):
        try:
            url = 'https://{}/api/v1/instance/peers'.format(name) 
            async with session.get(url, timeout=5) as response:
                return name, eval(await response.text()), depth
        except (SyntaxError, aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.ContentTypeError, asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.TooManyRedirects, UnicodeError, ValueError) as e:
            return name, {"error": e}, depth

    async def bound_fetch(self, fetching_fun, sem, url, session, depth):
        # Getter function with semaphore.
        async with sem:
            return await fetching_fun(url, session, depth)

    async def query_peers(self, num_query):

        sem = asyncio.Semaphore(50)

        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            tasks = []

            max_query = min(num_query, self.get_peers_queue.qsize())  # if there are less than num_query elements in the queue and query_info
            # doesn't have anything to add, the for would wait forever, thus we take min
            if max_query == 0: 
                max_query = 1

            logging.debug('peers - iterations {}'.format(max_query))
            i = 0
            while True:
                if max_query == 0: 
                    max_query = 1
                i += 1
                
                logging.debug('peers - waiting') 
                name, depth = await self.get_peers_queue.get()
                logging.debug('peers - {} {}'.format(i, name)) 
                tasks.append(asyncio.create_task(self.bound_fetch(self.fetch_peers, sem, name, session, depth)))

                if i == max_query: 
                    max_query = min(num_query, self.get_peers_queue.qsize()) 
                    logging.debug('peers - iterations {}'.format(max_query))
                    i = 0

                    results = await asyncio.gather(*tasks)

                    tasks.clear()
                    
                    for name, peers, depth in results:
                        if peers is not None and 'error' not in peers:
                            self.manageDb.insert_one_instance_to_network(name, peers, depth)
                            
                            logging.debug('peers - adding to queue peers of {}'.format(name))
                            for p in peers: 
                                await self.get_info_queue.put((p, depth + 1))

                    results.clear()
                    gc.collect()
                    logging.debug('peers - done')


    async def query_info(self, num_query):

        sem = asyncio.Semaphore(100)

        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            tasks = []

            save_every = min(num_query, self.get_info_queue.qsize())  # if there are less than num_query elements in the queue and query_peers
            # doesn't have anything to add, the for would wait forever, thus we take min
            
            logging.debug('info - iterations {}'.format(save_every))
            i = 0 
            while True:
                if save_every == 0: 
                    save_every = 1
                i += 1

                logging.debug('info - waiting') 
                name, depth = await self.get_info_queue.get()

                logging.debug('info - {} {} {}'.format(i, name, depth)) 
                tasks.append(asyncio.create_task(self.bound_fetch(self.fetch_info, sem, name, session, int(depth))))

                # logging.debug('i n {} {}'.format(i, max_quer))
                if i == save_every: 
                    
                    save_every = min(num_query, self.get_info_queue.qsize())  
                    logging.debug('info - iterations {} {}'.format(num_query, self.get_info_queue.qsize()))
                    i = 0 

                    results = await asyncio.gather(*tasks)
                    tasks.clear()
                    
                    for res, depth in results: 
                        if res is not None and 'error' not in res and 'uri' in res: 
                            self.manageDb.insert_one_to_archive(res["uri"], res) 

                            if depth < self.MAX_DEPTH: 
                                logging.debug('info - adding to queue {}'.format(res['uri']))
                                await self.get_peers_queue.put((res["uri"], depth)) # add instances get_peers queue
                            
                    results.clear()
                    gc.collect()
                    logging.debug('info - done')


    async def batch(self): 
        self.get_info_queue = asyncio.Queue(20000)
        self.get_peers_queue = asyncio.Queue()

        await self.load_queues()


        if self.get_info_queue.empty(): 
            await self.get_info_queue.put(("mastodon.social", 0))

            # logging.debug('starting coroutines, queue sizes {} - {}'.format(self.get_info_queue.qsize(), self.get_peers_queue.qsize()))
        await asyncio.gather(self.query_info(10000), self.query_peers(100))

    def main(self): 
        asyncio.run(self.batch())
            # await self.query_peers(1000)


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
