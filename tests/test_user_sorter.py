import sys
import os
sys.path.append(os.path.abspath(os.path.join(sys.path[0], os.pardir)))  # not the cleanest way
import unittest
import asyncio
import aiohttp

from src.manageDB import ManageDB
from src.user_sorter import UserSorter

class TestInstanceScanner(unittest.IsolatedAsyncioTestCase): 

    def setUp(self) -> None:
        self.id_queue = asyncio.Queue()
        self.sort_queue = asyncio.Queue()
        self.manageDB = ManageDB('test')
        self.u_sorter = UserSorter(self.id_queue, self.sort_queue, self.manageDB)


    def test_extract_instance_name(self): 
        instance = self.u_sorter.extract_instance_name('https://mastodon.cloud/@Brenda45465')
        self.assertEqual('mastodon.cloud', instance)

        instance = self.u_sorter.extract_instance_name('https://mastodon.social/@firstfemalepope')
        self.assertEqual('mastodon.social', instance)

        instance = self.u_sorter.extract_instance_name('http://ioc.exchange/@mourninggnu')
        self.assertEqual('ioc.exchange', instance)


    def test_extract_instance_name(self): 
        instance = self.u_sorter.extract_username('https://mastodon.cloud/@Brenda45465')
        self.assertEqual('@Brenda45465', instance)

        instance = self.u_sorter.extract_username('https://mastodon.social/@firstfemalepope')
        self.assertEqual('@firstfemalepope', instance)

        instance = self.u_sorter.extract_username('http://ioc.exchange/@mourninggnu')
        self.assertEqual('@mourninggnu', instance)

    

if __name__ == "__main__": 
    unittest.main()