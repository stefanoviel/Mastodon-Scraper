import json
import time
import requests
import threading
from tqdm import tqdm

# get most popular user from instance 
# the api only shows the follower and following from that specific instance, UI shows me also the ones from other instances. 
# start a bfs from each of them save in link and outlink (specify a max depth)

# keep going up util a certain depth
# find a way to make requests to different instances about the same account

class UserList: 
    def __init__(self) -> None:
        self.userspath = 'data/users.json'

        f = open(self.instances_path)
        self.archive = json.load(f)
        f.close()


# header = {'min_id': '110036844381252163'}
# r = requests.get('https://mastodon.social/api/v1/accounts/1/followers/')
# print(r.links)
# for i in r.json(): 
#     print(i['username'])
# https://masto.ai/api/v2/search/?q=Gargron@mastodon.social

# https://front-end.social/@leaverou/following

# https://front-end.social/api/v2/search/?q=leaverou




url = 'https://mastodon.social/api/v1/accounts/1/followers/'
while url is not None: 
    r = requests.get(url)
    print(r.json()[0]['url'])
    for i in r.json(): 
        print(i['url'])    
    url = r.links['next']['url']







# TODO: try with library, can i get all the followers of a certain user even from other instances?