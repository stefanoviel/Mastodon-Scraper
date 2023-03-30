import copy
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
        self.network_path = 'data/user_network.json'

        with open(self.users_path) as f: 
            self.archive = json.load(f)

        with open(self.network_path) as f: 
            self.network = json.load(f)

        self.to_scan = {}
        self.init_domain('https://mastodon.social/', 'https://mastodon.social/@Gargron', 1, 0)
        if not bool(self.archive) or not bool(self.network): 
            self.archive['https://mastodon.social/@Gargron'] = {"id":"1","username":"Gargron","acct":"Gargron","display_name":"Eugen Rochko","locked":False,"bot":False,"discoverable":True,"group":False,"created_at":"2016-03-16T00:00:00.000Z","note":"\u003cp\u003eFounder, CEO and lead developer \u003cspan class=\"h-card\"\u003e\u003ca href=\"https://mastodon.social/@Mastodon\" class=\"u-url mention\"\u003e@\u003cspan\u003eMastodon\u003c/span\u003e\u003c/a\u003e\u003c/span\u003e, Germany.\u003c/p\u003e","url":"https://mastodon.social/@Gargron","avatar":"https://files.mastodon.social/accounts/avatars/000/000/001/original/dc4286ceb8fab734.jpg","avatar_static":"https://files.mastodon.social/accounts/avatars/000/000/001/original/dc4286ceb8fab734.jpg","header":"https://files.mastodon.social/accounts/headers/000/000/001/original/3b91c9965d00888b.jpeg","header_static":"https://files.mastodon.social/accounts/headers/000/000/001/original/3b91c9965d00888b.jpeg","followers_count":304814,"following_count":388,"statuses_count":73481,"last_status_at":"2023-03-30","noindex":False,"emojis":[],"roles":[],"fields":[{"name":"Patreon","value":"\u003ca href=\"https://www.patreon.com/mastodon\" target=\"_blank\" rel=\"nofollow noopener noreferrer me\"\u003e\u003cspan class=\"invisible\"\u003ehttps://www.\u003c/span\u003e\u003cspan class=\"\"\u003epatreon.com/mastodon\u003c/span\u003e\u003cspan class=\"invisible\"\u003e\u003c/span\u003e\u003c/a\u003e","verified_at":None},{"name":"GitHub","value":"\u003ca href=\"https://github.com/Gargron\" target=\"_blank\" rel=\"nofollow noopener noreferrer me\"\u003e\u003cspan class=\"invisible\"\u003ehttps://\u003c/span\u003e\u003cspan class=\"\"\u003egithub.com/Gargron\u003c/span\u003e\u003cspan class=\"invisible\"\u003e\u003c/span\u003e\u003c/a\u003e","verified_at":"2023-02-07T23:24:40.347+00:00"}]}
            self.network['https://mastodon.social/@Gargron'] = {'followers' : [], 'following' : []} 

        self.MAX_DEPTH = 1

        self.MAX_QUERY_FIVE_MINUTES = 290
        self.MAX_ACCOUNTS_PER_TIME = 100
        self.MAX_CONNECTIONS = 50
        self.TIMEOUT = 3
        self.lock = threading.Lock()

    def save_archive(self) -> None:
        s = time.time()
        with open(self.users_path, 'w') as f:
            json.dump(self.archive, f, indent=4)
        
        with open(self.network_path, 'w') as f:
            json.dump(self.network, f, indent=4)
        
        print('saved in', round(time.time() - s, 2), 'seconds')
        
    def get_domain_id_from_url(self, user_url) -> str: 
        domain = re.search(r'^.+?(?=@)', user_url)
        username = re.search(r'https?://[^/]+/@(\w+)', user_url)

        if domain and username:
            domain = domain.group(0)
            username = username.group(1)
        else:
            print("No match")
            return None, None

        url =  domain + '/api/v2/search/?q=' + username
        r = requests.get(url, timeout=self.TIMEOUT)
        with self.lock: 
            if domain in self.to_scan: 
                self.to_scan[domain]['time_query'].append(time.time())

        try: 
            id = r.json()['accounts'][0]['id']
        except Exception as e: 
            return domain, None

        return domain, id

    def get_followers_following_urls(self, instance, account):

        followers = instance + 'api/v1/accounts/' + \
            str(account['id']) + '/followers/'
        following = instance + 'api/v1/accounts/' + \
            str(account['id']) + '/following/'

        return followers, following

    def get_next_page(self, instance, account, page_name):
        if account[page_name] == 'done':
            return None
        
        try: 
            r = requests.get(account[page_name], timeout=self.TIMEOUT)

            with self.to_scan[instance]['lock']:
                self.to_scan[instance]['time_query'].append(round(time.time()))

            if 'next' in r.links.keys():
                account[page_name] = r.links['next']['url']
                print('success', account[page_name])
            else:
                print(account[page_name])
                print('done', r.links.keys())
                account[page_name] = 'done'

            return r.json()
        except requests.exceptions.RequestException as err:
            return None


    def init_domain(self, instance, url, id, depth): 
        if instance not in list(self.to_scan.keys()): 
            self.to_scan[instance] = {}
            self.to_scan[instance]['lock'] = threading.Lock()
            self.to_scan[instance]['time_query'] = []
            self.to_scan[instance]['scanning'] = False
        
        if 'accounts' not in list(self.to_scan.keys()): 
            self.to_scan[instance]['accounts'] = {}

        self.to_scan[instance]['accounts'][url] = {'id': id, 'url' : url, 'next_page_followers': '',
                                    'next_page_followings': '', 'depth': depth }
        # print('to scan')
        # print(self.to_scan)


    def is_completed(self): 
        print('IS COMPLETE', len(self.to_scan))
        for key, value in self.to_scan.items(): 
            for k, v in self.to_scan[key]['accounts'].items(): 
                if v['depth'] <= self.MAX_DEPTH: 
                    return False

        return True

    def add_users_to_scan_and_save_link(self, current_account, user_list, relationship_type):
        if user_list and 'error' not in user_list:
            for f in user_list:
            
                if f['url'] not in list(self.archive.keys()) :
                    self.archive[f['url']] = f  # add to archive
                    self.network[f['url']] = {'followers' : [], 'following' : []}  # add to archive

                    # add to users to scan
                    if current_account['depth'] + 1 <= self.MAX_DEPTH:
                        instance, id = self.get_domain_id_from_url(f['url'])
                        if instance and id: 
                            with self.lock:
                                self.init_domain(instance, f['url'], id, current_account['depth'] + 1)
                
                    if relationship_type == 'followers': 
                        self.network[current_account['url']]['followers'].append(f['url'])
                        self.network[f['url']]['followers'].append(current_account['url'])
                    elif relationship_type == 'following':
                        self.network[current_account['url']]['following'].append(f['url'])
                        self.network[f['url']]['following'].append(current_account['url'])
                    

            
                            
    def number_query_last_five_min(self, instance):
        five_minutes_ago = time.time() - 60*5
        less_than_five = []
        with self.to_scan[instance]['lock']: 
            for i in self.to_scan[instance]['time_query']:
                if i > five_minutes_ago:
                    less_than_five.append(i)
            self.to_scan[instance]['time_query'] = less_than_five

        return len(less_than_five)

    def query_all(self):
        # query starting from first user until max depth is passed
        i = 0
        while True: 
            with self.lock: 
                print('calling is completed')
                if self.is_completed(): 
                    break
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                with self.lock: 
                    current_to_scan = copy.deepcopy(list(self.to_scan.keys()))
                for instance in current_to_scan: 
                    with self.to_scan[instance]['lock']: 
                        currently_scanning = self.to_scan[instance]['scanning']

                    if not currently_scanning: 
                        for account in list(self.to_scan[instance]['accounts'].keys())[:self.MAX_ACCOUNTS_PER_TIME]: 
                            print('scanning', instance)
                            # self.scan_account(instance, self.to_scan[instance]['accounts'][account], account)
                            future_to_url = (executor.submit(self.scan_account, instance, self.to_scan[instance]['accounts'][account], account))
                            _ = concurrent.futures.as_completed(future_to_url)


            self.save_archive()
            i += 1 
            if i % 10 == 0: 
                
                break
            
    def scan_account(self, instance, account, account_name): 
        # until we do all the query or finish all the accounts to query (there will always be one = timequery)
        with self.to_scan[instance]['lock']:
            num_accounts_still_to_scan = len(self.to_scan[instance]['accounts'].keys())
            self.to_scan[instance]['scanning'] = True

        # print(instance, self.number_query_last_five_min(instance))
        while self.number_query_last_five_min(instance) < self.MAX_QUERY_FIVE_MINUTES and num_accounts_still_to_scan >= 1: 
            # follower of the account have been completely scanned
            if account['next_page_followers'] == 'done' and account['next_page_following'] == 'done':

                with self.to_scan[instance]['lock']:
                    print('before delete',  instance, account_name)
                    del self.to_scan[instance]['accounts'][account_name]
                    num_accounts_still_to_scan -= 1 
            
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

            # followers = self.get_next_page( instance, account, 'next_page_followers') 
            # following = self.get_next_page( instance, account, 'next_page_following') 


            self.add_users_to_scan_and_save_link(account, followers, 'followers')
            self.add_users_to_scan_and_save_link(account, following, 'following')
        
            with self.to_scan[instance]['lock']:
                num_accounts_still_to_scan = len(self.to_scan[instance]['accounts'].keys())

        print('to_scan', len(self.to_scan), 'query 5 min instance', instance, self.to_scan[instance]['time_query'])


        with self.to_scan[instance]['lock']:
            self.to_scan[instance]['scanning'] = False
        
            
        
# print(self.number_query_last_five_min(instance))
# self.save_archive()

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
    u.query_all()


    # TODO paralelize requests
    # l = ['https://c18.masto.host/@grubstreetwomen', 'https://social.lfx.dev/@linuxfoundation', 'https://mozilla.social/@mconley', 'https://mastodon.social/@ianmcque', 'https://social.kernel.org/users/torvalds', 'https://mastodon.social/@rhipratchett', 'https://flipboard.social/@mike', 'https://mstdn.maud.io/@fn_aki', 'https://social.panic.com/@cabel', 'https://hachyderm.io/@davidfowl', 'https://zdf.social/@ZDF', 'https://flipboard.social/@miaq', 'https://me.dm/@coachtony', 'https://mastodon.social/@ZachWeinersmith', 'https://mastodon.social/@MrLovenstein', 'https://mastodon.social/@mastodonusercount', 'https://hachyderm.io/@samhenrigold', 'https://mastodon.social/@tiffanycli', 'https://mastodon.social/@triketora', 'https://crab.garden/@brainblasted', 'https://tilde.zone/@ftrain', 'https://hachyderm.io/@mekkaokereke', 'https://hachyderm.io/@rmondello', 'https://mastodon.social/@sandofsky', 'https://mastodon.social/@tenderlove', 'https://journa.host/@mergerson', 'https://mastodon.social/@lindsayellis', 'https://social.nil.nu/@nullkal', 'https://mastodon.social/@tvler', 'https://1password.social/@1password', 'https://mastodon.social/@williamgunn', 'https://neo.knzk.me/@Knzk', 'https://oak.social/@oak', 'https://mastodon.social/@davidslifka', 'https://mastodon.social/@jonasdowney', 'https://mastodon.social/@RebeccaSlatkin', 'https://mastodon.social/@xeraa', 'https://me.dm/@ev', 'https://me.dm/@biz', 'https://tmspk.net/@teamspeak']
    # for i in l: 
    #     print(u.get_domain_from_url(i))