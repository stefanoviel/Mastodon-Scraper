import sys
import os
sys.path.append(os.path.abspath(os.path.join(sys.path[0], os.pardir)))  # not the cleanest way
import unittest
import asyncio
import aiohttp

from src.user_sorter import UserSorter

class TestInstanceScanner(unittest.TestCase): 

    def setUp(self) -> None:
        self.id_queue = asyncio.Queue()
        self.sort_queue = asyncio.Queue()
        self.u_sorter = UserSorter(self.id_queue, self.sort_queue)


    def test_extract_instance_name(self): 
        instance = self.u_sorter.extract_instance_name('https://mastodon.cloud/@Brenda45465')
        self.assertEqual('mastodon.cloud', instance)

        instance = self.u_sorter.extract_instance_name('https://mastodon.social/@firstfemalepope')
        self.assertEqual('mastodon.social', instance)

        instance = self.u_sorter.extract_instance_name('http://ioc.exchange/@mourninggnu')
        self.assertEqual('ioc.exchange', instance)


if __name__ == "__main__": 
    unittest.main()