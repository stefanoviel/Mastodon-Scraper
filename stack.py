import concurrent.futures
from sys import getsizeof
import requests
import time

working_url = []
CONNECTIONS = 100
TIMEOUT = 5

tlds = open('data/peers.txt').read().splitlines()
urls = ['http://{}/api/v1/instance/peers'.format(x) for x in tlds[:10]]
urls = urls * 1000


def load_url_head(url, timeout):
    url = 'https://google.com'
    ans = requests.head(url, timeout=timeout)
    return ans.status_code, url

def load_url(url, timeout):
    url = 'https://google.com'
    ans = requests.get(url, timeout=timeout)
    return ans.status_code, url

with concurrent.futures.ThreadPoolExecutor(max_workers=CONNECTIONS) as executor:
    future_to_url = (executor.submit(load_url_head, url, TIMEOUT) for url in urls)
    time1 = time.time()
    for num, future in enumerate(concurrent.futures.as_completed(future_to_url)):
        try:
            code, url = future.result()
            if code == 200: 
                working_url.append(url)
        except Exception as exc:
            data = str(type(exc))

            print(f'{str(len(working_url))} out of {num}',end="\r")

    time2 = time.time()

print(f'Collecting working urls {time2-time1:.2f} s')


final = []
with concurrent.futures.ThreadPoolExecutor(max_workers=CONNECTIONS) as executor:
    future_to_url = (executor.submit(load_url, url, TIMEOUT) for url in working_url)
    time1 = time.time()
    for future in concurrent.futures.as_completed(future_to_url):
        try:
            peers_list = future.result()
            final.append(eval(peers_list))
        except Exception as exc:
            data = str(type(exc))

    time2 = time.time()

print(f'Took {time2-time1:.2f} s')
print(len(final))