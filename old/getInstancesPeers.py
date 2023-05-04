from instances.manageDB import ManageDB
import concurrent.futures
import requests
import random
import aiohttp
import asyncio
import logging
from queue import Queue
import gc
import time

class getInstancesPeers(): 
    def __init__(self, manageDB, params) -> None:
        self.logger = logging.getLogger('my_logger')
        self.logger.setLevel(logging.INFO)

        self.manageDb = manageDB
        self.queue = Queue()

        self.MAX_CONNECTIONS = params.get('MAX_CONNECTIONS')
        self.TIMEOUT = params.get('TIMEOUT')
        self.CHUNK_SIZE = 500


    def get_instances_peers_from_to_scan(self) -> None: 
        """
            Iterate all the instances in to_scan and scrape the peers
        """
        while self.manageDb.size_to_scan() > 0 : 
            print( self.manageDb.size_to_scan())
            # with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
            chunk_to_scan = min(self.CHUNK_SIZE, self.manageDb.size_to_scan())
            for i in range(chunk_to_scan): 
                self.logger.info(i)
                self.logger.info('Instances still to scan {0}'.format(self.manageDb.size_to_scan()))

                instance, depth = self.manageDb.get_next_instance_to_scan()
                self.logger.debug(instance)

                # get the known peers of the instance
                if not self.manageDb.is_in_archive(instance) or not self.manageDb.instance_has_error(instance): 
                    # executor.submit(self.get_instances_peers, instance, depth)
                    self.get_instances_peers(instance, depth)

            self.logger.debug('network', self.manageDb.get_network_size())

        # self.manageData.save_archive_network_to_scan()
        self.logger.info('len network {0}'.format(self.manageDb.get_network_size()))


    def worker():
        while True:
            item = q.get()
            do_work(item)
            q.task_done()

    
    for i in range(num_worker_threads):
        t = Thread(target=worker)
        t.daemon = True
        t.start()

    for item in source():
        q.put(item)

    q.join()

    def get_instance_peers1(self): 
        while True: 
            instance, depth = self.queue.get()
            self.get_instances_peers(instance, depth)
            self.queue.task_done()

    async def get_request(self, url):
        try: 
            params = {'limit': 100}
            session_timeout =   aiohttp.ClientTimeout(total=None,sock_connect=self.TIMEOUT,sock_read=self.TIMEOUT)
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async with session.get(url, params = params) as resp:
                    return (await resp.text())

        except Exception as e: 
            self.logger.debug(e)

    def get_instances_peers(self, instance_name, depth): 

        try: 
            
            # session = requests.session()
            # params = {'limit': 100}
            # response = session.get('https://' + instance_name + '/api/v1/instance/peers', params=params, timeout=3)
            # res = eval(response.content)
            # response.close()
            # session.close()

            asyncio.run(self.get_request('https://' + instance_name + '/api/v1/instance/peers')) 

            self.manageDb.add_instance_to_network(instance_name, res, depth)

            # self.manageDb.add_instance_to_network(instance_name, res, depth)
 
        except Exception as e : 
            self.logger.debug('peer error {0}'.format(e))

        gc.collect()
 



if "__main__" == __name__: 
    manageDB = ManageDB()
    manageDB.reset_collections()
    manageDB.init_to_test()

    getpeers = getInstancesPeers(manageDB, {"MAX_CONNECTIONS": 100, "TIMEOUT" : 3})
    getpeers.get_instances_peers_from_to_scan()

    # res = asyncio.run(getpeers.get_request('https://' + 'mastodon.social' + '/api/v1/instance/peers')) 
    # print(res)

