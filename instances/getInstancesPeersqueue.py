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
# it seems a problem at the core of request, or wathever package is used in python, even with other packages I still encounter the same problem
# 


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

        self.http = urllib3.PoolManager()

    def main(self):
        for i in range(self.MAX_CONNECTIONS):
            t = Thread(target=self.get_instances_peers)
            t.daemon = True
            t.start()

        for num, item in enumerate(self.manageDB.get_next_instance_to_scan()):
            self.logger.info(num)
            self.queue.put(item)

        self.queue.join()

    def get_request(self, url):
        try: 
            r = requests.get(url, timeout=self.TIMEOUT)
            return eval(r.content)
        except (requests.exceptions.ConnectionError, SyntaxError, requests.exceptions.ReadTimeout) as e: 
            self.logger.debug(e)

    def get_instances_peers(self):

        results_list = []
        while True:

            item = self.queue.get()
            instance_name = item.get("_id")
            depth = item.get("depth")
            res = self.get_request('https://' + instance_name + '/api/v1/instance/peers')


            if res is not None: 
                print(len(res)) 

                self.manageDB.add_one_instance_to_network(instance_name, res, depth)
                self.logger.info("got results %s queue len %d", instance_name, self.queue.qsize())


            self.queue.task_done()


if "__main__" == __name__:
    manageDB = ManageDB()
    manageDB.reset_collections()
    manageDB.init_to_test()

    getpeers = getInstancesPeers(
        manageDB, {"MAX_CONNECTIONS": 1, "TIMEOUT": 3})
    getpeers.main()
