from manageDB import ManageDB
import concurrent.futures
import requests
import random
import aiohttp
import asyncio
import logging
from queue import Queue
from threading import Thread
import gc
import time
import urllib3


# the problem is in the request, if I run it without the request but everything else it doesn't go out of memory
# it seems a problem at the core of request, or wathever package is used in python, even with other packages
# I still encounter the same problem
# it comes from the combination of requests with multithreading, running the same process sincronously doesn't create any trouble
# it's related to calling multiple different end-points, doing only one of them repeteatly doesn't raise the same issue.
# if i only get the header (head) memory is fine
# TODO: try to filter working URL with head, and use get with the working ones

# with the same url or either because it's the same or because error aren't generated it works ... 
# by only requesting head and closing seesion, requests and everything that can be closed it works better

# https://superfastpython.com/threading-in-python/


class getInstancesPeers():
    def __init__(self, manageDB: ManageDB, params) -> None:
        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning)

        self.logger = logging.getLogger('my_logger')
        self.logger.setLevel(logging.DEBUG)

        self.MAX_CONNECTIONS = params.get('MAX_CONNECTIONS')
        self.TIMEOUT = params.get('TIMEOUT')

        self.manageDB = manageDB
        self.queue = Queue(maxsize=self.MAX_CONNECTIONS)

        self.results_list = []
        self.counter = 0

        self.session = requests.session()


    def main(self):

        for i in range(self.MAX_CONNECTIONS):
            t = Thread(target=self.get_instances_peers, daemon=True)
            t.start()
            print(i)

        for num, item in enumerate(self.manageDB.get_next_instance_to_scan()):
                
            # print(item)
            self.queue.put(item)
            if num >= 5000: 
                break

        self.queue.join()   
        print('queue', self.queue.qsize())
        print(self.counter)


    # @profile
    def get_instances_peers(self):
        with requests.Session() as s:
            adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
            s.mount('https://', adapter)
            while True:
                # import requests
                item = self.queue.get()
                instance_name = item.get("_id")
                depth = item.get("depth")
                # print('requesting', instance_name)

                try: 
                    
                    url = 'https://' + instance_name + '/api/v1/instance/peers'
                    # url = 'https://google.com'
                    # r = s.get(url, timeout=3, headers = {'Connection': 'close'} )
                    
                    with s.get(url, timeout=3 ) as r:
                        # print(len(r.content))
                        r.connection.close()

                except (requests.exceptions.ConnectionError, SyntaxError, requests.exceptions.ReadTimeout, requests.exceptions.TooManyRedirects, NameError) as e: 
                    print(e)

                # time.sleep(1)
                self.queue.task_done()


if "__main__" == __name__:
    manageDB = ManageDB()
    manageDB.reset_collections()
    manageDB.init_to_test()
    print('ok')

    getpeers = getInstancesPeers(
        manageDB, {"MAX_CONNECTIONS": 100, "TIMEOUT": 3})
    s = time.time()
    getpeers.main()
    print('done ', time.time() - s)
