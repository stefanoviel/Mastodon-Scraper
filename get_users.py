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

        self.to_scan = {}
        self.to_scan['https://mastodon.social/'] = {}
        self.to_scan['https://mastodon.social/']['https://mastodon.social/@Gargron'] = {
            'id': 1,  'next_page_followers': '', 'next_page_followings': '', 'depth': -1}

        self.to_scan['https://mastodon.social/']['time_query'] = []

        self.priority_queue = ['https://mastodon.social/']
        self.max_depth = 0

        self.MAX_QUERY_FIVE_MINUTES = 280
        self.MAX_ACCOUNTS_PER_TIME = 100
        self.MAX_CONNECTIONS = 100
        self.TIMEOUT = 3
        self.lock = threading.Lock()

    def save_archive(self) -> None:
        s = time.time()
        with open(self.users_path, 'w') as f:
            json.dump(self.archive, f, indent=4)
        print('saved in', round(time.time() - s, 2), 'seconds')

    def get_domain_from_url(self, user_url) -> str:
        return re.search(r'^.+?(?=@)', user_url)

    def get_followers_following_urls(self, instance, account):

        followers = instance + 'api/v1/accounts/' + \
            str(account['id']) + '/followers/'
        following = instance + 'api/v1/accounts/' + \
            str(account['id']) + '/following/'

        return followers, following

    def get_next_page(self, instance, account, page_name):
        if account[page_name] != 'done':
            r = requests.get(account[page_name], timeout=self.TIMEOUT)

            with self.lock:
                self.to_scan[instance]['time_query'].append(round(time.time()))

            if 'next' in r.links.keys():
                account[page_name] = r.links['next']['url']
            else:
                account[page_name] = 'done'

            return r.json()
        else:
            return None

    def add_users_to_scan(self, current_account, user_list):
        if user_list:
            for f in user_list:
                if f['url'] not in self.archive.keys():
                    self.archive[f['url']] = f
                    if current_account['depth'] + 1 < self.max_depth:
                        domain = self.get_domain_from_url(f['url'])
                        with self.lock:
                            self.to_scan[domain][f['url']] = {'id': f['id'],  'next_page_followers': '',
                                                              'next_page_followings': '', 'depth': current_account['depth'] + 1}

    def number_query_last_five_min(self, instance):
        five_minutes_ago = time.time() - 60*5
        less_than_five = []
        with self.lock:
            for i in self.to_scan[instance]['time_query']:
                if i > five_minutes_ago:
                    less_than_five.append(i)
            self.to_scan[instance]['time_query'] = less_than_five

        return len(less_than_five)

    def query_instance_accounts(self, instance):
        """
            keep querying accounts of one specific instance until there are no more accounts or the maximum number of queries have been done 
        """

        num_accounts_still_to_scan = len(self.to_scan[instance].keys())

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
            future_to_url = (executor.submit(self.scan_account, instance, account) for account in self.to_scan[instance][:self.MAX_ACCOUNTS_PER_TIME])
            for _ in  concurrent.futures.as_completed(future_to_url): 
                pass


    def scan_account(self, instance, account): 
         # until we do all the query or finish all the accounts to query (there will always be one = timequery)
        while self.number_query_last_five_min(instance) < self.MAX_QUERY_FIVE_MINUTES and num_accounts_still_to_scan > 1: # TODO fix here

            # follower of the account have been completely scanned
            if account['next_page_followers'] == 'done' and account['next_page_following'] == 'done':
                with self.lock:
                    del self.to_scan[instance][account]
                    

            # if we don't yet know the url for the follower and follwoing
            if account['next_page_followers'] == '':
                followers_url, following_url = self.get_followers_following_urls(
                    instance, account)
                account['next_page_followers'] = followers_url
                account['next_page_following'] = following_url

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                future_to_url = (executor.submit(self.get_next_page, instance, account, page) for page in [
                                 'next_page_followers', 'next_page_following'])
                finished_futures =  concurrent.futures.as_completed(future_to_url)
                followers = next(finished_futures).result()
                following = next(finished_futures).result()

            self.add_users_to_scan(account, followers)
            self.add_users_to_scan(account, following)

            print('archive', len(self.archive))
            print(self.number_query_last_five_min(instance))
            self.save_archive()

    


# header = {'min_id': '110036844381252163'}
# r = requests.get('https://mastodon.social/api/v1/accounts/1/followers/')
# print(r.links)
# for i in r.json():
#     print(i['username'])
# https://masto.ai/api/v2/search/?q=Gargron@mastodon.social
# https://front-end.social/@leaverou/following
# https://front-end.social/api/v2/search/?q=leaverou
# https://mastodon.social/api/v1/accounts/110055463297024710/followers/
# url = 'https://mastodon.social/api/v1/accounts/1/following/'
# while True:
#     r = requests.get(url)
#     print(r.json()[0]['url'])
#     for i in r.json():
#         print(i.keys())
#     if 'next' in r.links.keys():
#         url = r.links['next']['url']
#     else:
#         print('Done!')
#         break
if __name__ == "__main__":
    u = UserList()
    u.query_instance_accounts('https://mastodon.social/')

    # TODO paralelize requests
