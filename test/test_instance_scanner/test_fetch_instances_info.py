import unittest
import asyncio
import aiohttp
import mock

from unittest.mock import Mock, AsyncMock
from src.manage_db.manage_mongo_db import ManageDB

from src.instances_scanner.fetch_instances_info import FetchInstanceInfo

class MockQueue:
    def __init__(self, items_list):
        self.items = items_list
        self.remaining_elements = 0
        self.number_get_calls = 0

    async def put(self, item):
        pass

    async def get(self):
        self.number_get_calls += 1
        if self.remaining_elements < len(self.items):
            item = self.items[self.remaining_elements]
            self.remaining_elements += 1
            return item
        return None

    def empty(self):
        return self.remaining_elements >= len(self.items)


class TestInstanceScanner(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.info_queue = asyncio.Queue()
        self.peers_queue = asyncio.Queue()
        self.manageDB = ManageDB('test')
        self.max_depth = 2

        self.fetch_instance_info = FetchInstanceInfo(
            self.info_queue, self.peers_queue, self.manageDB, self.max_depth)

    @mock.patch('aiohttp.ClientSession.get')
    async def test_fetch_info(self, mocked_get):
        instance_name = 'mastodon.social'
        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            info, depth = await self.fetch_instance_info.fetch_info(session, instance_name, 0)

        mocked_get.assert_called_once_with(
            'https://mastodon.social/api/v1/instance')
        self.assertEqual(depth, 0)

    @mock.patch('aiohttp.ClientSession.get')
    async def test_fetch_raise_exception(self, mocked_get):
        mocked_get.side_effect = ValueError

        instance_name = 'mastodon.social'
        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            info, depth = await self.fetch_instance_info.fetch_info(session, instance_name, 0)

        self.assertEqual(info, {'uri': instance_name, 'error': ''})

    async def test_fetch_elements_until_info_queue_is_empty(self):
        
        items = [('mastodon.social', 0)] * 10
        mock_queue = MockQueue(items)
        self.info_queue = Mock(spec=mock_queue)

        self.fetch_instance_info.info_queue.empty = Mock(return_value=True)

        await self.fetch_instance_info.loop_through_info_queue_and_fetch(10)

        # just 9 because last iteratio is False
        self.assertEqual(mock_queue.remaining_elements, 0)

    async def test_fetch_elements_until_peers_queue_is_empty(self):

        items = [('mastodon.social', 0)] * 10
        mock_queue = MockQueue(items)
        self.info_queue = Mock(spec=mock_queue)

        self.peers_queue.empty = Mock(side_effect=[False] * 2*2 + [True])  # 5 because of lazy evaluation

        await self.fetch_instance_info.loop_through_info_queue_and_fetch(50)

        self.assertEqual(mock_queue.number_get_calls, 12)

    # async def test_save_all_results_to_db(self):

    #     self.manageDB.is_present_in_archive = Mock(return_value=False)
    #     self.manageDB.save_element_to_archive = Mock()

    #     results = [({'uri': 'mastodon.social'}, 0)] * 20

    #     await self.fetch_instance_info.save_info_results_add_to_peers_queue(results)

    #     # one for every result
    #     self.assertEqual(self.manageDB.is_present_in_archive.call_count, 20)
    #     for save_element in self.manageDB.save_element_to_archive.call_args_list:
    #         self.assertEqual(save_element.args, ('mastodon.social', {
    #                          'uri': 'mastodon.social', 'depth': 0}))

    # async def test_more_max_depth_and_error_not_added_to_peers_queue(self):

    #     self.manageDB.is_present_in_archive = Mock(return_value=False)
    #     self.manageDB.save_element_to_archive = Mock()
    #     self.peers_queue.put = AsyncMock()

    #     results = [({'uri': 'mastodon.social'}, 0)] * 10 + [({'uri': 'mastodon.social'}, self.max_depth + 1)
    #                                                         ] * 10 + [({"uri": 'mastodon.social', "error": 'er'}, 0)] * 10

    #     await self.fetch_instance_info.save_info_results_add_to_peers_queue(results)

    #     self.assertEqual(self.peers_queue.put.call_count, 10)


    # async def test_all_instances_info_get_fetched(self):

    #     self.fetch_instance_info.info_queue.empty = Mock(side_effect=[False] * 10 + [True])
    #     self.fetch_instance_info.peers_queue.empty = Mock(return_value= 0)
    #     self.fetch_instance_info.fetch_info = AsyncMock(return_value=({'instance_info'}, 1))

    #     await self.fetch_instance_info.loop_through_info_queue_and_fetch(50)

    #     self.assertEqual(len(self.fetch_instance_info.info_queue.get.call_args_list), 10)


if __name__ == '__main__':
    unittest.main()
