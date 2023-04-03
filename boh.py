import asyncio
import aiohttp
import time


async def gather_with_concurrency(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


async def get_async(url, session, results):
    async with session.get(url) as response:
        i = url.split('/')[-1]
        obj = await response.text()
        results[i] = obj


async def main():
    conn = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
    session = aiohttp.ClientSession(connector=conn)
    results = {}
      users = ["https://mastodon.social/@pizzaghost",
            "https://mastodon.social/@christianbishop",
            "https://mastodon.social/@kpazgan",
            "https://mastodon.world/@lazysoundsystem",
            "https://mastodon.social/@wardsology",
            "https://mastodon.social/@nkt407",
            "https://infosec.exchange/@_t0",
            "https://mastodon.social/@whatjustin",
            "https://social.cologne/@rogertyler44",
            "https://mastodon.social/@J01001101",
            "https://mastodon.online/@MagicianDavid",
            "https://mastodon.social/@fangfei",
            "https://mstdn.social/@Magiciandavid",
            "https://mastodon.social/@HawkeyeCoffee",
            "https://pol.social/@piotrsikora",
            "https://mstdn.ca/@idoclosecuts", 
            "https://mastodon.social/@davidklapheck",
            "https://mstdn.jp/@inadvertently00",
            "https://mastodon.social/@dgrpnar",
            "https://mastodon.social/@Eurybis",
            "https://mastodon.social/@warrenhoward",
            "https://literatur.social/@moranaga",
            "https://mastodon.social/@brookburris",
            "https://toot.cryolog.in/@fReNe7iK",
            "https://mastodon.social/@nicklyons",
            "https://mastodon.social/@Caohim",
            "https://mastodon.online/@momo345",
            "https://mastodon.social/@briankernohan",
            "https://mastodon.social/@huynnn301",
            "https://mastodon.social/@Hukson",
            "https://mastodon.social/@Danteguyy",
            "https://mastodon.com.tr/@FloydianDM",
            "https://mastodon.world/@tinoomi",
            "https://toot.wales/@fkamiah17",
            "https://mastodon.social/@krati05",
            "https://mastodon.social/@Kennydev",
            "https://mastodon.online/@HollyKinnamon",
            "https://mastodon.online/@kggn",]
    

    # s = time.time()
    # for user in users: 
    #     print(u.get_id_from_url(user))

    # print('time', time.time() - s)



    # rs = (grequests.get(u) for u in users)
    # print(grequests.map(rs))


    instances = [u.get_instance_from_url(user_url) for user_url in users]
    usernames = [u.get_username_from_url(user_url) for user_url in users]

    urls = []
    for instance, username in zip(instances, usernames): 
        if instance is not None and username is not None: 

            urls.append(instance + '/api/v2/search/?q=' + username)

    conc_req = 40
    now = time.time()
    await gather_with_concurrency(conc_req, *[get_async(i, session, results) for i in urls])
    time_taken = time.time() - now

    print(time_taken)
    print(results)
    await session.close()


asyncio.run(main())