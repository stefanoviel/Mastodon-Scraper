import asyncio
import gc
import logging
import time

import aiohttp
import idna

from src.manageDB import ManageDB
from src.manageJSON import ManageJSON


class ScanInstances:
    def __init__(
        self,
        manageDB: ManageDB,
        info_queue_path: str = "data/info_queue.txt",
        peers_queue_path: str = "data/peers_queue.txt",
    ) -> None:
        self.manageDb = manageDB
        self.info_queue = None
        self.peers_queue = None

        self.MAX_DEPTH = 2

        self.info_queue_path = info_queue_path
        self.peers_queue_path = peers_queue_path

        logging.basicConfig(level=logging.INFO)

    async def load_queue(self, queue: asyncio.Queue, queue_name: str) -> None:
        """load a queue from txt file"""
        file = open(queue_name)
        for elem in file.read().splitlines():
            elem = elem.split(",")
            await queue.put((elem[0], elem[1]))

        file.close()

    async def load_info_peers_queue(self):
        """load the info and the peers queue from file"""
        await self.load_queue(self.info_queue, self.info_queue_path)
        await self.load_queue(self.peers_queue, self.peers_queue_path)

    async def save_queue(self, queue: asyncio.Queue, queue_name: str) -> None:
        """save a queue to txt file"""
        tot = queue.qsize()
        with open(queue_name, "w") as f:
            for _ in range(tot):
                elem = await queue.get()
                f.write(str(elem[0]) + "," + str(elem[1]) + "\n")
                await queue.put(elem)

    async def save_info_peers_queue(self) -> None:
        """save the info and the peers queue to file"""
        logging.debug("saving queue")
        await self.save_queue(self.info_queue, self.info_queue_path)
        await self.save_queue(self.peers_queue, self.peers_queue_path)

    async def fetch_info(
        self, name: str, session: aiohttp.ClientSession, depth: int
    ) -> tuple[dict, int]:
        """Fetch info of instance given name"""
        try:
            url = "https://{}/api/v1/instance".format(name)
            async with session.get(url, timeout=5) as response:
                return await response.json(), depth
        except (
            SyntaxError,
            aiohttp.client_exceptions.ClientPayloadError,
            aiohttp.client_exceptions.ClientResponseError,
            aiohttp.client_exceptions.ContentTypeError,
            asyncio.exceptions.TimeoutError,
            aiohttp.client_exceptions.ClientConnectorError,
            aiohttp.client_exceptions.ServerDisconnectedError,
            aiohttp.client_exceptions.ClientOSError,
            aiohttp.client_exceptions.TooManyRedirects,
            UnicodeError,
            ValueError,
        ) as e:
            return {"uri": name, "error": str(e)}, depth

    async def fetch_peers(self, name, session, depth):
        """Fetch peers of instance"""
        try:
            url = "https://{}/api/v1/instance/peers".format(name)
            async with session.get(url, timeout=5) as response:
                # TODO not the safest thing maybe enough to call response.json() ???
                return name, await response.json(), depth
        except (
            SyntaxError,
            aiohttp.client_exceptions.ClientPayloadError,
            aiohttp.client_exceptions.ClientResponseError,
            aiohttp.client_exceptions.ContentTypeError,
            asyncio.exceptions.TimeoutError,
            aiohttp.client_exceptions.ClientConnectorError,
            aiohttp.client_exceptions.ServerDisconnectedError,
            aiohttp.client_exceptions.ClientOSError,
            aiohttp.client_exceptions.TooManyRedirects,
            UnicodeError,
            ValueError,
        ) as e:
            return name, {"uri": name, "error": str(e)}, depth

    async def bound_fetch(self, fetching_fun, sem, url, session, depth):
        """Getter function with semaphore, to limit number of simultaneous requests"""
        async with sem:
            return await fetching_fun(url, session, depth)

    async def save_peers_results(self, results: dict):
        """put the new peers into the info queue in order to retrieve the info"""
        for name, peers, depth in results:
            if peers is not None and "error" not in peers:
                self.manageDb.add_peers_instance(name, peers)
                # logging.info('peers - adding to queue the peers of {}'.format(name))

                for p in peers:
                    if not self.manageDb.is_in_archive(p):
                        await self.info_queue.put((p, int(depth) + 1))

    async def save_info_results(self, results: list[dict]) -> None:
        """save the info of the peers that have been scraped"""
        for res, depth in results:
            # save even if there is an error
            if (
                res is not None
                and "uri" in res
                and not self.manageDb.is_in_archive(res["uri"])
            ):
                res["_id"] = res["uri"]
                res["depth"] = depth
                self.manageDb.insert_one_to_archive(res)

                if depth < self.MAX_DEPTH and "error" not in res:
                    logging.debug(
                        "info - adding to peers_queue {} {}".format(res["uri"], depth)
                    )
                    await self.peers_queue.put((res["uri"], depth))

    async def save_results_reset_loop(
        self, tasks, queue_saver, save_result_every_n, queue_size
    ):
        """save info queues and reset save every"""

        # take min to save last elements
        save_every = min(save_result_every_n, queue_size)
        if save_every == 0:
            save_every = 1

        results = await asyncio.gather(*tasks)
        tasks.clear()

        await queue_saver(results)
        await self.save_info_peers_queue()

        # results.clear() removed for testing
        gc.collect()
        return save_every

    async def loop_query_peers(self, session, sem, save_result_every_n):
        """loop and query the instances in peers queue"""

        tasks = []
        save_every = 1  # first iteration we save immediately
        iterations = 0
        first = True

        while self.peers_queue.qsize() != 0 or self.info_queue.qsize() != 0 or first:
            iterations += 1

            name, depth = await self.peers_queue.get()
            first = False

            has_peers = self.manageDb.has_peers(name)
            if (
                has_peers is not None and not has_peers
            ):  # check that we haven't already queried the peers of this instance
                logging.info("getting peers {}".format(name))
                tasks.append(
                    asyncio.create_task(
                        self.bound_fetch(self.fetch_peers, sem, name, session, depth)
                    )
                )

            if iterations == save_every:
                iterations = 0
                save_every = await self.save_results_reset_loop(
                    tasks,
                    self.save_peers_results,
                    save_result_every_n,
                    self.info_queue.qsize(),
                )

    async def query_peers(self, save_result_every_n):
        """Loop to continuosly query peers, it add the peers to the info_queue"""

        sem = asyncio.Semaphore(50)

        connector = aiohttp.TCPConnector(force_close=True, limit=50)
        async with aiohttp.ClientSession(
            connector=connector, trust_env=True
        ) as session:
            await self.loop_query_peers(session, sem, save_result_every_n)

    async def query_info(self, save_result_every_n):
        """Loop to continuosly query info of instances, it add the peers to the peers_queue"""

        sem = asyncio.Semaphore(100)

        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(
            connector=connector, trust_env=True
        ) as session:
            await self.loop_query_info(session, sem, save_result_every_n)

    async def loop_query_info(self, session, sem, save_result_every_n):
        """loop and query the instances in the info queue"""

        tasks = []
        save_every = 1  # first iteration we save immediately
        iterations = 0

        while self.peers_queue.qsize() != 0 or self.info_queue.qsize() != 0:
            iterations += 1  # second iteration doesn't save anything

            name, depth = await self.info_queue.get()
            logging.info("getting info {}".format(name))
            tasks.append(
                asyncio.create_task(
                    self.bound_fetch(self.fetch_info, sem, name, session, int(depth))
                )
            )

            if iterations == save_every:
                iterations = 0

                save_every = await self.save_results_reset_loop(
                    tasks,
                    self.save_info_results,
                    save_result_every_n,
                    self.info_queue.qsize(),
                )

    async def batch(
        self, info_queue_size, frequency_saving_info, frequency_saving_peers
    ):
        """start both info query and peers query togheter (one feeds the other and vice versa)"""

        # only way it can explode is if get_peers queue becomes too big
        # to fix just save those in memory
        # queues keep two elements name and depth (distance from original one)
        self.info_queue = asyncio.Queue(info_queue_size)
        self.peers_queue = asyncio.Queue()

        await self.load_info_peers_queue()

        if self.info_queue.empty():
            await self.info_queue.put(("mastodon.social", 0))

        await asyncio.gather(
            self.query_info(frequency_saving_info),
            self.query_peers(frequency_saving_peers),
        )

    def main(self):
        asyncio.run(self.batch(20000, 10000, 100))

    def reset_queue(self):
        """reset queues for testing purposes"""
        open(self.info_queue_path, "w").close()
        open(self.peers_queue_path, "w").close()


if __name__ == "__main__":
    manageDB = ManageJSON("instances")
    instances = ScanInstances(manageDB)

    # for testing purposes use the below two
    # instances.manageDb.reset_collections()
    # instances.reset_queue()

    instances.main()
