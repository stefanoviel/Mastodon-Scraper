import asyncio
import aiohttp
import gc
import time


async def fetch(url, session):
    try:
        async with session.get(url, timeout=5) as response:
            return await response.json()
    except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.ContentTypeError, asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.TooManyRedirects) as e:
        # print(e)
        pass


async def bound_fetch(sem, url, session):
    # Getter function with semaphore.
    async with sem:
        return await fetch(url, session)

async def by_aiohttp_concurrency(urls):
    # use aiohttp
    sem = asyncio.Semaphore(50)

    connector = aiohttp.TCPConnector(force_close=True, limit=50)
    async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
        tasks = []
        # url = "https://google.com"
        for n, url in enumerate(urls):
            # print(n, end='\r')
            tasks.append(asyncio.create_task(bound_fetch(sem, url, session)))
            # tasks.append(asyncio.create_task(fetch(url, session)))

        original_result = await asyncio.gather(*tasks)
        # print(len(original_result))
        tasks.clear()
        i = 0
        for res in original_result:
            if res is not None:
                i += 1
                # print(res)
            # original_result.remove(res)
        original_result.clear()
        gc.collect()
        print(i)


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    try:
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
    except TypeError as tp:
        return []


if __name__ == "__main__":
    total = 10000

    start_time = time.time()
    tlds = open('data/peers.txt').read().splitlines()
    urls = ['https://{}/api/v1/instance/peers'.format(x) for x in tlds[:50000]]
    # urls = ['https://google.com'] * 1000
    
    # need to be divided otherwise too much memory in the list that saves all task
    for url in chunks(urls, 1000):
        asyncio.run(by_aiohttp_concurrency(url.copy()))

    print("--- It took %s seconds ---" % (time.time() - start_time))
