import unittest
import asyncio
import aiohttp
import mock


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


    @mock.patch(FetchInstanceInfo.info_queue, 'get')
    async def test_fetch_all_elements_info_queue(self, mocked_queue): 
        res = [False] * 9 + [True]
        print(res)
        mocked_queue.empty.return_value = False
        # empty.side_effects = [False] * 9 + [True]

        await self.fetch_instance_info.loop_get_from_info_queue_and_fetch()

        # self.assertEqual(len(mocked_get.call_args_list), 10)



if __name__ == '__main__':
    unittest.main()
