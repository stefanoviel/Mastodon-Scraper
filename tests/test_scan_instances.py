import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(sys.path[0], os.pardir)))  # not the cleanest way
import unittest
import asyncio
import aiohttp
import mock

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

    # async def test_save_queue(self): 
    #     queue = asyncio.Queue()
    #     await self.scan.load_queue(queue, self.info_queue_path)
    #     size = queue.qsize()
    #     await self.scan.save_queue(queue, self.info_queue_path)
    #     self.assertEqual(queue.qsize(), size)

    #     file = open(self.info_queue_path)
    #     lines = file.read().splitlines()
    #     self.assertEqual(len(lines), queue.qsize())

    #     file.close()

    # async def test_fetch_info(self): 
    #     depth = 1
    #     async with aiohttp.ClientSession(trust_env=True) as session:
    #         res, new_depth = await self.scan.fetch_info('mastodon.social', session, depth)

    #     self.assertEqual(depth, new_depth)

    # async def test_save_info_results(self): 
    #     n_elements = 40
    #     results = []
    #     for i in range(n_elements): 
    #         results.append(({'uri': str(i), 'info' : 'abc'}, i))
    #     await self.scan.save_info_results(results)

    #     for num, elem in enumerate(self.scan.manageDb.archive.find({})): 
    #         self.assertEqual(str(num), elem['_id'])
    #         self.assertEqual(str(num), elem['uri'])

    #     # only elements with depth < than MAX_DEPTH will be added to peers queue
    #     self.assertEqual(self.scan.peers_queue.qsize(), n_elements - self.scan.MAX_DEPTH) 

    # async def test_save_peers_results(self): 
    #     n_elements = 40
    #     results = []
    #     for i in range(n_elements): 
    #         results.append(({'uri': str(i), 'info' : 'abc'}, i))
    #     await self.scan.save_info_results(results)


    #     n_peers = 50
    #     results = []
    #     for i in range(n_elements): 
    #         results.append((str(i), [j for j in range(n_peers)],  i))

    #     await self.scan.save_peers_results(results)

    #     for num, elem in enumerate(self.scan.manageDb.archive.find({})): 
    #         self.assertEqual(n_peers, len(elem['peers']))
    #         self.assertEqual(str(num), elem['uri'])

    #     self.assertEqual(self.scan.info_queue.qsize(), n_elements * n_peers)


    @mock.patch.object(ManageDB, 'has_peers')
    @mock.patch.object(ScanInstances, 'save_peers_results')
    @mock.patch.object(ScanInstances, 'bound_fetch')
    async def test_query_peers(self, bound_fetch_mock, save_peers, has_peers): 
        
        bound_fetch_return = ['abs_{}'.format(i) for i in range(20)]
        bound_fetch_mock.return_value = bound_fetch_return

        has_peers.return_value = False

        n_elements = 40
        for i in range(n_elements): 
            await self.scan.peers_queue.put(('mastodon.social_{}'.format(i), i))

        await self.scan.query_peers(10)

        
        call_args = []
        for i in save_peers.call_args_list: 
            call_args  = call_args  + i[0][0]

        self.assertEqual(bound_fetch_mock.call_count, n_elements) # each element fetched
        self.assertEqual(len(call_args), n_elements) # all saved
        self.assertEqual(self.scan.peers_queue.qsize(), 0) # nothing on the queue



    @mock.patch.object(ScanInstances, 'save_info_results')
    @mock.patch.object(ScanInstances, 'bound_fetch')
    async def test_query_peers(self, bound_fetch_mock, save_peers): 
        
        bound_fetch_return = {'uri': 'mastodon.social', 'info' : 'abc'}
        bound_fetch_mock.return_value = bound_fetch_return

        n_elements = 40
        for i in range(n_elements): 
            await self.scan.info_queue.put(('mastodon.social_{}'.format(i), i))

        await self.scan.query_info(10)

        call_args = []
        for i in save_peers.call_args_list: 
            call_args  = call_args  + i[0][0]

        self.assertEqual(bound_fetch_mock.call_count, n_elements) # each element fetched
        self.assertEqual(len(call_args), n_elements) # all saved
        self.assertEqual(self.scan.peers_queue.qsize(), 0) # nothing on the queue


    # @mock.patch.object(ScanInstances, 'fetch_peers')
    # @mock.patch.object(ScanInstances, 'fetch_info')
    # async def test_batch(self, fetch_info, fetch_peers): 
    #     fetch_info_return = {'uri': 'mastodon.social', 'info' : 'abc'}
    #     fetch_info.return_value = fetch_info_return

    #     fetch_peers_return = ['abs_{}'.format(i) for i in range(20)]
    #     fetch_peers.return_value = fetch_peers_return

    #     n_elements = 40
    #     for i in range(n_elements): 
    #         await self.scan.info_queue.put(('mastodon.social_{}'.format(i), i))

    #     await self.scan.batch(100, 10, 10)
        



if __name__ == "__main__": 
    unittest.main()



