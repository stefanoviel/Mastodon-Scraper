import copy
import json
import time
import requests
import threading
import concurrent.futures
from tqdm import tqdm
import re


# TODO split in different files
# use login

class UserList:
    def __init__(self) -> None:
        self.users_path = 'data/users.json'
        self.network_path = 'data/users_network.json'
        self.to_scan_path = 'data/users_to_scan.json'
        self.MAX_DEPTH = 1
        self.MAX_QUERY_FIVE_MINUTES = 270
        self.MAX_ACCOUNTS_PER_TIME = 100
        self.MAX_CONNECTIONS = 200
        self.TIMEOUT = 3
        self.lock = threading.Lock()
        self.time = 0

        with open(self.users_path) as f:
            self.archive = json.load(f)

        with open(self.network_path) as f:
            self.network = json.load(f)

        with open(self.to_scan_path) as f:
            self.to_scan = json.load(f)

        self.lockers = {}

        # check if already initialize and initialize otherwise
        if not bool(self.archive):
            self.archive['https://mastodon.social/@Gargron'] = {"id": "1", "username": "Gargron", "acct": "Gargron", "display_name": "Eugen Rochko", "locked": False, "bot": False, "discoverable": True, "group": False, "created_at": "2016-03-16T00:00:00.000Z", "note": "\u003cp\u003eFounder, CEO and lead developer \u003cspan class=\"h-card\"\u003e\u003ca href=\"https://mastodon.social/@Mastodon\" class=\"u-url mention\"\u003e@\u003cspan\u003eMastodon\u003c/span\u003e\u003c/a\u003e\u003c/span\u003e, Germany.\u003c/p\u003e", "url": "https://mastodon.social/@Gargron", "avatar": "https://files.mastodon.social/accounts/avatars/000/000/001/original/dc4286ceb8fab734.jpg", "avatar_static": "https://files.mastodon.social/accounts/avatars/000/000/001/original/dc4286ceb8fab734.jpg", "header": "https://files.mastodon.social/accounts/headers/000/000/001/original/3b91c9965d00888b.jpeg", "header_static": "https://files.mastodon.social/accounts/headers/000/000/001/original/3b91c9965d00888b.jpeg",
                                                                "followers_count": 304814, "following_count": 388, "statuses_count": 73481, "last_status_at": "2023-03-30", "noindex": False, "emojis": [], "roles": [], "fields": [{"name": "Patreon", "value": "\u003ca href=\"https://www.patreon.com/mastodon\" target=\"_blank\" rel=\"nofollow noopener noreferrer me\"\u003e\u003cspan class=\"invisible\"\u003ehttps://www.\u003c/span\u003e\u003cspan class=\"\"\u003epatreon.com/mastodon\u003c/span\u003e\u003cspan class=\"invisible\"\u003e\u003c/span\u003e\u003c/a\u003e", "verified_at": None}, {"name": "GitHub", "value": "\u003ca href=\"https://github.com/Gargron\" target=\"_blank\" rel=\"nofollow noopener noreferrer me\"\u003e\u003cspan class=\"invisible\"\u003ehttps://\u003c/span\u003e\u003cspan class=\"\"\u003egithub.com/Gargron\u003c/span\u003e\u003cspan class=\"invisible\"\u003e\u003c/span\u003e\u003c/a\u003e", "verified_at": "2023-02-07T23:24:40.347+00:00"}]}
        if not bool(self.network):
            self.network['https://mastodon.social/@Gargron'] = {
                'followers': [], 'following': []}
        if not bool(self.to_scan):
            self.init_instance('https://mastodon.social/',
                             'https://mastodon.social/@Gargron', 1, 0)

        for instance in self.to_scan:
            self.lockers[instance] = threading.Lock()

    def save_archives(self) -> None:
        s = time.time()

        with open(self.users_path, 'w') as f:
            json.dump(self.archive, f, indent=4)

        with open(self.network_path, 'w') as f:
            json.dump(self.network, f, indent=4)

        with open(self.to_scan_path, 'w') as f: 
            json.dump(self.to_scan, f, indent=4)

        print('saved in', round(time.time() - s, 2), 'seconds')

    def get_instance_from_url(self, user_url: str) -> str:
        instance = re.search(r'^.+?(?=@)', user_url)

        if instance:
            return instance.group(0)
        else:
            return None

    def get_username_from_url(self, user_url) -> str:
        username = re.search(r'https?://[^/]+/@(\w+)', user_url)

        if username:
            return username.group(1)
        else:
            return None

    def get_id_from_url(self, user_url: str) -> str:

        instance = self.get_instance_from_url(user_url)
        username = self.get_username_from_url(user_url)

        if instance is None or username is None: 
            return None

        try:
            url = instance + '/api/v2/search/?q=' + username
            r = requests.get(url, timeout=self.TIMEOUT) # TODO I don't check if I have made too many requests

            with self.lock:
                if instance in self.to_scan:
                    self.to_scan[instance]['time_query'].append(time.time())

            id = r.json()['accounts'][0]['id']
        except Exception as e:
            return None

        return id

    def get_followers_following_urls(self, instance_name: str, account_id: str) -> dict[str, str]:

        followers = instance_name + 'api/v1/accounts/' + \
            str(account_id) + '/followers/'
        following = instance_name + 'api/v1/accounts/' + \
            str(account_id) + '/following/'

        return followers, following

    def get_next_page(self, instance_name: str, account: dict, page_name: str):
        if account[page_name] == 'done':
            return {}

        try:
            r = requests.get(account[page_name], timeout=self.TIMEOUT)

            with self.lockers[instance_name]:
                self.to_scan[instance_name]['time_query'].append(
                    round(time.time()))

            # save next availible page otherwise we are done
            if 'next' in r.links.keys():
                account[page_name] = r.links['next']['url']
            else:
                account[page_name] = 'done'

            return r.json()

        except requests.exceptions.RequestException as err:
            print(err)

    def init_instance(self, instance_name: str, user_url: str, user_id: str, depth: int) -> None:
        if instance_name not in list(self.to_scan.keys()):
            self.to_scan[instance_name] = {}
            self.lockers[instance_name] = threading.Lock()
            self.to_scan[instance_name]['time_query'] = []

        if 'accounts' not in list(self.to_scan.keys()):
            self.to_scan[instance_name]['accounts'] = {}

        self.to_scan[instance_name]['accounts'][user_url] = {'id': user_id, 'url': user_url, 'next_page_followers': '',
                                                   'next_page_followings': '', 'depth': depth}

    def is_scan_completed(self) -> None:
        with self.lock:
            for key, value in self.to_scan.items():
                for k, v in self.to_scan[key]['accounts'].items():
                    
                    if v['depth'] <= self.MAX_DEPTH:
                        return False

        return True

    def save_user_links(self, current_account:dict , users_list:list, relationship_type:str):
        if users_list and 'error' not in users_list:
            for f in users_list:
                
                # check user isn't already present
                if f['url'] not in list(self.archive.keys()):
                    self.archive[f['url']] = f  # add to archive
                    self.network[f['url']] = {
                        'followers': [], 'following': []}  # add to archive

                    if relationship_type == 'followers':
                        self.network[current_account['url']]['followers'].append(f['url'])
                        self.network[f['url']]['followers'].append(current_account['url'])
                    elif relationship_type == 'following':
                        self.network[current_account['url']]['following'].append(f['url'])
                        self.network[f['url']]['following'].append(current_account['url'])

    def add_users_to_scan(self, current_account:str, user_list:str) -> None:
        if user_list and 'error' not in user_list:
            for f in user_list:
                if f['url'] not in list(self.archive.keys()):
                    if current_account['depth'] + 1 <= self.MAX_DEPTH:
                        instance = self.get_instance_from_url(f['url'])
                        id = self.get_id_from_url(f['url'])
                        if instance and id:
                            with self.lock:
                                self.init_instance(instance, f['url'], id, current_account['depth'] + 1)

  
    def number_query_last_five_min(self, instance_name:str) -> int:
        five_minutes_ago = time.time() - 60*5
        less_than_five = []
        with self.lockers[instance_name]:
            for i in self.to_scan[instance_name]['time_query']:
                if i > five_minutes_ago:
                    less_than_five.append(i)
            self.to_scan[instance_name]['time_query'] = less_than_five

        return len(less_than_five)
    
    def reset_data_structures(self): 
        self.archive = {}
        self.archive['https://mastodon.social/@Gargron'] = {"id": "1", "username": "Gargron", "acct": "Gargron", "display_name": "Eugen Rochko", "locked": False, "bot": False, "discoverable": True, "group": False, "created_at": "2016-03-16T00:00:00.000Z", "note": "\u003cp\u003eFounder, CEO and lead developer \u003cspan class=\"h-card\"\u003e\u003ca href=\"https://mastodon.social/@Mastodon\" class=\"u-url mention\"\u003e@\u003cspan\u003eMastodon\u003c/span\u003e\u003c/a\u003e\u003c/span\u003e, Germany.\u003c/p\u003e", "url": "https://mastodon.social/@Gargron", "avatar": "https://files.mastodon.social/accounts/avatars/000/000/001/original/dc4286ceb8fab734.jpg", "avatar_static": "https://files.mastodon.social/accounts/avatars/000/000/001/original/dc4286ceb8fab734.jpg", "header": "https://files.mastodon.social/accounts/headers/000/000/001/original/3b91c9965d00888b.jpeg", "header_static": "https://files.mastodon.social/accounts/headers/000/000/001/original/3b91c9965d00888b.jpeg",
                                                                "followers_count": 304814, "following_count": 388, "statuses_count": 73481, "last_status_at": "2023-03-30", "noindex": False, "emojis": [], "roles": [], "fields": [{"name": "Patreon", "value": "\u003ca href=\"https://www.patreon.com/mastodon\" target=\"_blank\" rel=\"nofollow noopener noreferrer me\"\u003e\u003cspan class=\"invisible\"\u003ehttps://www.\u003c/span\u003e\u003cspan class=\"\"\u003epatreon.com/mastodon\u003c/span\u003e\u003cspan class=\"invisible\"\u003e\u003c/span\u003e\u003c/a\u003e", "verified_at": None}, {"name": "GitHub", "value": "\u003ca href=\"https://github.com/Gargron\" target=\"_blank\" rel=\"nofollow noopener noreferrer me\"\u003e\u003cspan class=\"invisible\"\u003ehttps://\u003c/span\u003e\u003cspan class=\"\"\u003egithub.com/Gargron\u003c/span\u003e\u003cspan class=\"invisible\"\u003e\u003c/span\u003e\u003c/a\u003e", "verified_at": "2023-02-07T23:24:40.347+00:00"}]}
        self.network = {}
        self.network['https://mastodon.social/@Gargron'] = {
                'followers': [], 'following': []}
        
        self.to_scan = {}
        self.init_instance('https://mastodon.social/',
                     'https://mastodon.social/@Gargron', 1, 0)
        
        self.save_archives()

    def scan_account(self, instance, account, account_name):
        with self.lockers[instance]:
            num_accounts_still_to_scan = len(self.to_scan[instance]['accounts'].keys())

        while self.number_query_last_five_min(instance) < self.MAX_QUERY_FIVE_MINUTES and num_accounts_still_to_scan > 0:
            # print('last 5 min query for ', instance, ':', self.number_query_last_five_min(instance))
            print('total account scraped', len(self.archive), end = '\r')
            # follower and following of account completely scanned
            if account['next_page_followers'] == 'done' and account['next_page_following'] == 'done':
                with self.lockers[instance]:
                    del self.to_scan[instance]['accounts'][account_name]
                    num_accounts_still_to_scan -= 1

            # if we don't yet know the url for the follower and follwoing
            if account['next_page_followers'] == '' or account['next_page_following'] == '':
                followers_url, following_url = self.get_followers_following_urls(instance, account['id'])
                account['next_page_followers'] = followers_url
                account['next_page_following'] = following_url

            followers = self.get_next_page( instance, account, 'next_page_followers')
            following = self.get_next_page( instance, account, 'next_page_following')


            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                future_to_url = executor.submit(self.add_users_to_scan, account, followers) 
                future_to_url = executor.submit(self.add_users_to_scan, account, following) 

            future_to_url  = concurrent.futures.as_completed(future_to_url)

            self.save_user_links(account, followers, 'followers')
            self.save_user_links(account, following, 'following')

            with self.lockers[instance]:
                num_accounts_still_to_scan = len(self.to_scan[instance]['accounts'].keys())

            print('total account scraped', len(self.archive), end='\r')
            print('total account scraped', len(self.archive), end='\r')


    def query_all(self):
        # query starting from first user until max depth is passed
        i = 0
        while True:
            if self.is_scan_completed():
                break
            print('checking is complete ')

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                
                # deep copy otherwise it would chance while iterating
                with self.lock:
                    current_to_scan = copy.deepcopy(list(self.to_scan.keys()))

                for instance in current_to_scan:

                    for account in list(self.to_scan[instance]['accounts'].keys())[:self.MAX_ACCOUNTS_PER_TIME]:
                        print('scanning', instance)
                        # self.scan_account(instance, self.to_scan[instance]['accounts'][account], account)
                        future_to_url = (executor.submit(self.scan_account, instance, self.to_scan[instance]['accounts'][account], account))
                    

                _ = concurrent.futures.as_completed(future_to_url)

            self.save_archives()
            i += 1
            if i % 10 == 0:
                break




# https://masto.ai/api/v2/search/?q=Gargron@mastodon.social
# https://mastodon.social/api/v1/accounts/1/following/


if __name__ == "__main__":
    u = UserList()
    # u.reset_data_structures()
    u.query_all()
