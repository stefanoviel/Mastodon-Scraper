import unittest
import asyncio
import aiohttp
import mock

from unittest.mock import Mock, AsyncMock


from src.instances_scanner.fetch_instances_info import FetchInstanceInfo


class TestInstanceScanner(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.info_queue = asyncio.Queue()
        self.peers_queue = asyncio.Queue()
        self.tasks = []
        self.fetch_instance_info = FetchInstanceInfo(self.info_queue, self.peers_queue, self.tasks)

    @mock.patch('aiohttp.ClientSession.get')
    async def test_fetch_info(self, mocked_get): 
        instance_name = 'mastodon.social'
        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            info = await self.fetch_instance_info.fetch_info(session, instance_name)

        mocked_get.assert_called_once_with('https://mastodon.social/api/v1/instance')


    @mock.patch('aiohttp.ClientSession.get')
    async def test_fetch_raise_exception(self, mocked_get): 
        mocked_get.side_effect = ValueError

        instance_name = 'mastodon.social'
        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            info = await self.fetch_instance_info.fetch_info(session, instance_name)

        self.assertEqual(info, {'uri':instance_name, 'error': ''})



    async def test_fetch_elements_until_info_queue_is_empty(self): 

        self.fetch_instance_info.info_queue.empty = Mock(side_effect=[False] * 9 + [True])
        self.fetch_instance_info.info_queue.get = AsyncMock(return_value=('mastodon.social', 1))

        await self.fetch_instance_info.loop_get_from_info_queue_and_fetch()

        self.assertEqual(len(self.fetch_instance_info.info_queue.get.call_args_list), 9) # just 9 because last iteratio is False

    
    async def test_fetch_elements_until_peers_queue_is_empty(self): 

        self.fetch_instance_info.info_queue.empty = Mock(side_effect=[False] * 10 + [True] * 5)
        self.fetch_instance_info.peers_queue.empty = Mock(side_effect=[False] * 4 + [True])  # 5 because of lazy evaluation
        self.fetch_instance_info.info_queue.get = AsyncMock(return_value=('mastodon.social', 1))

        await self.fetch_instance_info.loop_get_from_info_queue_and_fetch()

        self.assertEqual(len(self.fetch_instance_info.info_queue.get.call_args_list), 14)


    async def test_fetch_elements_until_peers_queue_is_empty(self): 

        self.fetch_instance_info.info_queue.empty = Mock(side_effect=[False] * 10 + [True] * 5)
        self.fetch_instance_info.peers_queue.empty = Mock(side_effect=[False] * 4 + [True])  # 5 because of lazy evaluation
        self.fetch_instance_info.info_queue.get = AsyncMock(return_value=('mastodon.social', 1))

        await self.fetch_instance_info.loop_get_from_info_queue_and_fetch()

        self.assertEqual(len(self.fetch_instance_info.info_queue.get.call_args_list), 14)

if __name__ == '__main__':
    unittest.main()
