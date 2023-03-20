import json
import time
import requests
import threading
import concurrent.futures
from tqdm import tqdm
import re


# get most popular user from instance 
# the api only shows the follower and following from that specific instance, UI shows me also the ones from other instances. 
# start a bfs from each of them save in link and outlink (specify a max depth)

# keep going up util a certain depth
# find a way to make requests to different instances about the same account

class UserList: 
    def __init__(self) -> None:
        self.users_path = 'data/users.json'

        f = open(self.users_path)
        self.archive = json.load(f)
        f.close()

        self.to_scan['https://mastodon.social/'] = {'users':[{'user_url': 'https://mastodon.social/@Gargron', 'depth': -1, 'time_query': []}] }
        self.priority_queue = ['https://mastodon.social/']
        self.max_depth = 0

        self.query_per_time = 10
        self.CONNECTIONS = 100
        self.TIMEOUT = 3
        self.lock = threading.Lock()

    def save_archive(self) -> None:
        s = time.time()
        with open(self.users_path, 'w') as f:
                json.dump(self.archive, f, indent=4)
        print('saved in', round(time.time() - s, 2), 'seconds')

    def get_domain_id_from_url(self, user_url) -> str: 
        print(user_url)
        domain = re.search(r'^.+?(?=@)', user_url)
        username = re.search(r'https?://[^/]+/@(\w+)', user_url)

        if domain and username:
            domain = domain.group(0)
            username = username.group(1)
        else:
            print("No match")

        url =  domain + '/api/v2/search/?q=' + username
        r = requests.get(url, timeout=self.TIMEOUT)

        print(r.json()['accounts'][0]['id'])

        return domain, r.json()['accounts'][0]['id']
        
    def get_followers_following(self, user_url):  #-> tuple(list[str], list[str]): 
        
        domain, id = self.get_domain_id_from_url(user_url)

        followers = requests.get(domain + 'api/v1/accounts/' + str(id) + '/followers/' ,  timeout=self.TIMEOUT)
        following = requests.get(domain + 'api/v1/accounts/' + str(id) + '/following/' ,  timeout=self.TIMEOUT)

        return followers, following

    def at_most_n_query(self, instance):
        # if there are still elements to be scanned in the instnace add them to the queue 
        pass

    def deep_scan(self) -> None: 
        """
            with a BFS scan all users up to self.max_depth
        """ 
        s = time.time()

        with self.lock: 
            still_to_scan = len(self.to_scan)

        while still_to_scan > 0: 
            with self.lock: 
                # get next user to scan
                if len(self.to_scan) > 0:
                    instance = self.priority_queue.pop(0)
                else: 
                    break            
            
            out = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.CONNECTIONS) as executor:
                future_to_url = (executor.submit(self.scan_peer, url, depth+1) for url in peers)
                for future in concurrent.futures.as_completed(future_to_url):
                    pass
            
            # add all new individual that don't exceed the maximum depth to the respective instance to be scanned
     
                
        self.save_archive()
        print('finished in', round(time.time() - s, 2), 'seconds - ', self.i, 'instances retrieved')




    




# header = {'min_id': '110036844381252163'}
# r = requests.get('https://mastodon.social/api/v1/accounts/1/followers/')
# print(r.links)
# for i in r.json(): 
#     print(i['username'])
# https://masto.ai/api/v2/search/?q=Gargron@mastodon.social

# https://front-end.social/@leaverou/following

# https://front-end.social/api/v2/search/?q=leaverou

# https://mastodon.social/api/v1/accounts/110055463297024710/followers/

# url = 'https://mastodon.social/api/v1/accounts/1/followers/'
# while url is not None: 
#     r = requests.get(url)
#     print(r.json()[0]['url'])
#     for i in r.json(): 
#         print(i['url'])    
#     url = r.links['next']['url']



if __name__ == "__main__": 
    u = UserList()
    print(u.get_followers_following('https://mastodon.social/@bradleymackey'))
