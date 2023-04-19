import aiohttp
import asyncio
import requests
import time

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://httpbin.org/get') as resp:
            print(resp.status)

            return await resp.json()



s = time.time()
print(asyncio.run(main()))
print(time.time() - s )

s = time.time()
r = requests.get('http://httpbin.org/get')
print(time.time() - s )

