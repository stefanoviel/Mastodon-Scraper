import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(sys.path[0], os.pardir)))  # not the cleanest way
import unittest
import asyncio
import aiohttp
from src.manageDB import ManageDB

from src.scan_instances import ScanInstances

class TestInstanceScanner(unittest.IsolatedAsyncioTestCase): 

    async def asyncSetUp(self): 
        self.info_queue_path = 'tests/data/info_queue.txt'
        self.peers_queue_path = 'tests/data/peers_queue.txt'

        self.manageDB = ManageDB('test')
        self.manageDB.reset_collections()

        self.scan = ScanInstances(self.manageDB, self.info_queue_path, self.peers_queue_path)

        self.scan.info_queue = asyncio.Queue(20000) 
        self.scan.peers_queue = asyncio.Queue()

        self.scan.MAX_DEPTH = 20

    async def test_load_queue(self): 
        queue = asyncio.Queue()
        await self.scan.load_queue(queue, self.info_queue_path)
        file = open(self.info_queue_path)
        lines = file.read().splitlines()

        for line in lines: 
            elem0, elem1 = await queue.get()
            elems = line.split(',')
            self.assertEqual(elems[0], elem0)
            self.assertEqual(elems[1], elem1)

        file.close()

    async def test_save_queue(self): 
        queue = asyncio.Queue()
        await self.scan.load_queue(queue, self.info_queue_path)
        size = queue.qsize()
        await self.scan.save_queue(queue, self.info_queue_path)
        self.assertEqual(queue.qsize(), size)

        file = open(self.info_queue_path)
        lines = file.read().splitlines()
        self.assertEqual(len(lines), queue.qsize())

        file.close()

    async def test_fetch_info(self): 
        depth = 1
        async with aiohttp.ClientSession(trust_env=True) as session:
            res, new_depth = await self.scan.fetch_info('mastodon.social', session, depth)

        self.assertEqual(depth, new_depth)

    async def test_save_info_results(self): 
        n_elements = 40
        results = []
        for i in range(n_elements): 
            results.append(({'uri': str(i), 'info' : 'abc'}, i))
        await self.scan.save_info_results(results)

        for num, elem in enumerate(self.scan.manageDb.archive.find({})): 
            self.assertEqual(str(num), elem['_id'])
            self.assertEqual(str(num), elem['uri'])

        # only elements with depth < than MAX_DEPTH will be added to peers queue
        self.assertEqual(self.scan.peers_queue.qsize(), n_elements - self.scan.MAX_DEPTH) 

    async def test_save_peers_results(self): 
        n_elements = 40
        results = []
        for i in range(n_elements): 
            results.append(({'uri': str(i), 'info' : 'abc'}, i))
        await self.scan.save_info_results(results)


        n_peers = 50
        results = []
        for i in range(n_elements): 
            results.append((str(i), [j for j in range(n_peers)],  i))

        await self.scan.save_peers_results(results)

        for num, elem in enumerate(self.scan.manageDb.archive.find({})): 
            self.assertEqual(n_peers, len(elem['peers']))
            self.assertEqual(str(num), elem['uri'])

        self.assertEqual(self.scan.info_queue.qsize(), n_elements * n_peers)

    async def test_set_up_new_run(self): 
        self.scan.set_up_new_run()


if __name__ == "__main__": 
    unittest.main()

