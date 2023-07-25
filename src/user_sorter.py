import asyncio
import logging
import re

import aiohttp

from src.instance_user_scanner import InstanceScanner
from src.manageDB import ManageDB
from src.manageJSON import ManageJSON


class UserSorter:
    def __init__(
        self, id_queue: asyncio.Queue, sort_queue: asyncio.Queue, manageDB: ManageDB
    ) -> None:
        self.sort_queue = sort_queue
        self.all_instances = {}
        self.manageDB = manageDB
        self.tasks = []

        logging.basicConfig(level=logging.INFO)

    def extract_instance_name(self, url):
        pattern = r"(?<=//)(.*?)(?=/)"

        result = re.search(pattern, url)
        if result:
            return result.group(1)

    def extract_username(self, url):
        username = re.search(r"@(.+)", url)
        if username:
            return username.group(0)
        else:
            return username

    def remove_done_instances(self):
        for instance_name, instance in list(self.all_instances.items()):
            if instance.done:
                del self.all_instances[instance_name]

    def check_done(self):
        for instance_name, instance in list(self.all_instances.items()):
            if not instance.done:
                return False
        return True

    async def create_instance_scanner(self, instance_name):
        instance = InstanceScanner(
            instance_name, asyncio.Queue(), self.sort_queue, self.manageDB
        )
        self.all_instances[instance_name] = instance
        return instance

    async def sort(self):
        connector = aiohttp.TCPConnector(force_close=True,limit=500, limit_per_host=50)
        async with aiohttp.ClientSession(connector=connector,trust_env=True) as session:
            while True:
                if self.sort_queue.empty() and self.check_done():
                    print("All user scraped :)")
                    break

                user_url = await self.sort_queue.get()
                instance_name = self.extract_instance_name(user_url)
                instance = self.all_instances.get(instance_name)
                username = self.extract_username(user_url)

                if username is None:
                    continue

                if instance is None:
                    # logging.debug('adding instance {}'.format(instance_name))
                    self.remove_done_instances()

                    instance = await self.create_instance_scanner(instance_name)

                    await instance.id_queue.put(user_url)

                    loop = asyncio.get_event_loop()
                    loop.create_task(instance.main(session=session))

                    # logging.info('number of instances currently being scraped {}'.format(len(self.all_instances)))

                else:
                    await instance.id_queue.put(user_url)

    async def start_with_Gargron(self):
        await self.sort_queue.put("https://mastodon.social/@Gargron")
        await self.sort()


async def main():
    mdb = ManageJSON("users")
    mdb.reset_collections()
    u = UserSorter(asyncio.Queue(), asyncio.Queue(), mdb)
    await u.start_with_Gargron()


if __name__ == "__main__":
    asyncio.run(main())
    # mdb = ManageDB('users')
    # us= mdb.archive.find_one({'_id': 'mastodon.social/@Gargron'})
    # print(us['followers'])
