import unittest
import asyncio
import aiohttp
import mock


from src.instances_scanner.fetch_instances_info import FetchInstanceInfo


class TestInstanceScanner(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.fetch_instance_info = FetchInstanceInfo()

    @mock.patch('aiohttp.ClientSession.get')
    async def test_fetch_info(self, mocked_get): 

        instance_name = 'mastodon.social'
        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            info = await self.fetch_instance_info.fetch_info(session, instance_name)

        mocked_get.assert_called_once_with('https://mastodon.social/api/v1/instance')



if __name__ == '__main__':
    unittest.main()
