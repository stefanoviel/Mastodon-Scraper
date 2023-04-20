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

# problem is in the threadpool, aparently it queues too many threads all at once
# this causes memory to accumulate. I don't really know why, but if executed syncrnously
# it doesn't create problems, I want to implement a producer cosumer


class getInstancesPeers():
    def __init__(self, manageDB, params) -> None:
        self.logger = logging.getLogger('my_logger')
        self.logger.setLevel(logging.INFO)

        self.manageDb = manageDB
        self.queue = Queue()

        self.MAX_CONNECTIONS = params.get('MAX_CONNECTIONS')
        self.TIMEOUT = params.get('TIMEOUT')
        self.CHUNK_SIZE = 500

    def main(self):
        for i in range(self.MAX_CONNECTIONS):
            t = Thread(target=self.get_instances_peers)
            t.daemon = True
            t.start()

        for item in self.manageDb.get_next_instance_to_scan():
            self.queue.put(item)

        self.queue.join()

    async def get_request(self, url):
        try:
            params = {'limit': 100}
            session_timeout = aiohttp.ClientTimeout(
                total=None, sock_connect=self.TIMEOUT, sock_read=self.TIMEOUT)
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async with session.get(url, params=params) as resp:
                    return (await resp.text())

        except Exception as e:
            self.logger.debug(e)

    def get_instances_peers(self):
        while True:
            item = self.queue.get()
            instance_name = item["_id"]
            depth = item["depth"]

            try:
                res = asyncio.run(self.get_request(
                    'https://' + instance_name + '/api/v1/instance/peers'))
                self.manageDb.add_one_instance_to_network(
                    instance_name, eval(res), depth)
                self.logger.info("got results %s", instance_name)

            except Exception as e:
                self.logger.debug('peer error {0}'.format(e))

            self.queue.task_done()


if "__main__" == __name__:
    manageDB = ManageDB()
    manageDB.reset_collections()
    manageDB.init_to_test()

    getpeers = getInstancesPeers(
        manageDB, {"MAX_CONNECTIONS": 50, "TIMEOUT": 3})
    getpeers.main()

