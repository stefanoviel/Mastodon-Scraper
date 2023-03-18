import concurrent.futures
import json
import requests
import time

out = []
CONNECTIONS = 100
TIMEOUT = 5

def get_instance_peers( instance_name) -> list[str]: 
    params = {'limit': 100}
    r = requests.get('https://' + instance_name + '/api/v1/instance/peers', params=params, timeout=3)
    return eval(r.content)


urls = []
peers = get_instance_peers('mastodon.social')
for i in peers : 
    urls.append('https://' + i + '/api/v1/instance')

def load_url(url, timeout):
    ans = requests.get(url, timeout=timeout)
    return ans.content

with concurrent.futures.ThreadPoolExecutor(max_workers=CONNECTIONS) as executor:
    future_to_url = (executor.submit(load_url, url, TIMEOUT) for url in urls[:100])
    time1 = time.time()
    for future in concurrent.futures.as_completed(future_to_url):
        try:
            data = future.result()
            data = json.loads(data)
        except Exception as exc:
            data = str(type(exc))
        finally:
            out.append(data)

            print(str(len(out)),end="\r")

    time2 = time.time()

for i in out: 
    print(i)
print(f'Took {time2-time1:.2f} s')

