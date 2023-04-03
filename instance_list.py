# https://stackoverflow.com/questions/4783735/problem-with-multi-threaded-python-app-and-socket-connections 
# 1008303

import json
import time
import requests
import threading
import concurrent.futures
from tqdm import tqdm

class InstanceList: 
    def __init__(self) -> None:
        self.instances_path = 'data/instances.json'
        self.instances_network_path = 'data/instances_network.json'

        self.to_scan = [('mastodon.social', 0)]
        self.max_depth = 2

        with open(self.instances_path) as f: 
            self.archive = json.load(f)

        with open(self.instances_network_path) as f: 
            self.network = json.load(f)

        if len(self.archive): 
            self.archive['mastodon.social'] = {"uri":"mastodon.social","title":"Mastodon","short_description":"The original server operated by the Mastodon gGmbH non-profit","description":"","email":"staff@mastodon.social","version":"4.1.1","urls":{"streaming_api":"wss://streaming.mastodon.social"},"stats":{"user_count":1011953,"status_count":53995715,"domain_count":53284},"thumbnail":"https://files.mastodon.social/site_uploads/files/000/000/001/@1x/57c12f441d083cde.png","languages":["en"],"registrations":true,"approval_required":false,"invites_enabled":true,"configuration":{"accounts":{"max_featured_tags":10},"statuses":{"max_characters":500,"max_media_attachments":4,"characters_reserved_per_url":23},"media_attachments":{"supported_mime_types":["image/jpeg","image/png","image/gif","image/heic","image/heif","image/webp","image/avif","video/webm","video/mp4","video/quicktime","video/ogg","audio/wave","audio/wav","audio/x-wav","audio/x-pn-wave","audio/vnd.wave","audio/ogg","audio/vorbis","audio/mpeg","audio/mp3","audio/webm","audio/flac","audio/aac","audio/m4a","audio/x-m4a","audio/mp4","audio/3gpp","video/x-ms-asf"],"image_size_limit":10485760,"image_matrix_limit":16777216,"video_size_limit":41943040,"video_frame_rate_limit":60,"video_matrix_limit":2304000},"polls":{"max_options":4,"max_characters_per_option":50,"min_expiration":300,"max_expiration":2629746}},"contact_account":{"id":"1","username":"Gargron","acct":"Gargron","display_name":"Eugen Rochko","locked":false,"bot":false,"discoverable":true,"group":false,"created_at":"2016-03-16T00:00:00.000Z","note":"\u003cp\u003eFounder, CEO and lead developer \u003cspan class=\"h-card\"\u003e\u003ca href=\"https://mastodon.social/@Mastodon\" class=\"u-url mention\"\u003e@\u003cspan\u003eMastodon\u003c/span\u003e\u003c/a\u003e\u003c/span\u003e, Germany.\u003c/p\u003e","url":"https://mastodon.social/@Gargron","avatar":"https://files.mastodon.social/accounts/avatars/000/000/001/original/dc4286ceb8fab734.jpg","avatar_static":"https://files.mastodon.social/accounts/avatars/000/000/001/original/dc4286ceb8fab734.jpg","header":"https://files.mastodon.social/accounts/headers/000/000/001/original/3b91c9965d00888b.jpeg","header_static":"https://files.mastodon.social/accounts/headers/000/000/001/original/3b91c9965d00888b.jpeg","followers_count":305403,"following_count":388,"statuses_count":73499,"last_status_at":"2023-04-02","noindex":false,"emojis":[],"roles":[],"fields":[{"name":"Patreon","value":"\u003ca href=\"https://www.patreon.com/mastodon\" target=\"_blank\" rel=\"nofollow noopener noreferrer me\"\u003e\u003cspan class=\"invisible\"\u003ehttps://www.\u003c/span\u003e\u003cspan class=\"\"\u003epatreon.com/mastodon\u003c/span\u003e\u003cspan class=\"invisible\"\u003e\u003c/span\u003e\u003c/a\u003e","verified_at":null},{"name":"GitHub","value":"\u003ca href=\"https://github.com/Gargron\" target=\"_blank\" rel=\"nofollow noopener noreferrer me\"\u003e\u003cspan class=\"invisible\"\u003ehttps://\u003c/span\u003e\u003cspan class=\"\"\u003egithub.com/Gargron\u003c/span\u003e\u003cspan class=\"invisible\"\u003e\u003c/span\u003e\u003c/a\u003e","verified_at":"2023-02-07T23:24:40.347+00:00"}]},"rules":[{"id":"1","text":"Sexually explicit or violent media must be marked as sensitive when posting"},{"id":"2","text":"No racism, sexism, homophobia, transphobia, xenophobia, or casteism"},{"id":"3","text":"No incitement of violence or promotion of violent ideologies"},{"id":"4","text":"No harassment, dogpiling or doxxing of other users"},{"id":"7","text":"Do not share intentionally false or misleading information"}]}

        self.scanned = list(self.archive.keys())


        self.CONNECTIONS = 100
        self.TIMEOUT = 3
        self.i = 0 
        self.lock = threading.Lock()

    def save_archive(self) -> None:
        s = time.time()
        with open(self.instances_path, 'w') as f:
                json.dump(self.archive, f, indent=4)

        with open(self.instances_network_path, 'w') as f:
            json.dump(self.network, f, indent=4)

        print('saved in', round(time.time() - s, 2), 'seconds')

    def add_connection(self, instance, peer) -> None: 
        if instance not in self.network: 
            self.network[instance] = []

        self.network[instance].append(peer)

    def deep_scan(self) -> None: 
        """
            with a BFS scan all instances up to self.max_depth
        """ 
        s = time.time()

        with self.lock: 
            still_to_scan = len(self.to_scan)

        while still_to_scan > 0: 
            with self.lock: 
                # get next instance to scan
                if len(self.to_scan) > 0:
                    instance, depth = self.to_scan.pop(0)
                else: 
                    break

            try: 
                # get the known peers of the instance
                peers = self.get_instance_peers(instance)   
            except (SyntaxError, requests.exceptions.RequestException) as err : 
                print('peers request', str(err))
            
            futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.CONNECTIONS) as executor:
                for peer in peers: 
                    self.add_connection(instance, peer)
                    futures.append(executor.submit(self.scan_peer, peer, depth+1) )

            _ = concurrent.futures.as_completed(futures)
            

                
        self.save_archive()
        print('finished in', round(time.time() - s, 2), 'seconds - ', self.i, 'instances retrieved')


    def scan_peer(self, peer, depth):
        """
            scan individual instance and save information in the archive
        """ 
        try:
            with self.lock:
                # mark the instance as visited
                if peer in self.scanned : 
                    return 
                else: 
                    self.scanned.append(peer)    

            # print(f"Scanning peer: {peer} ")
            response = self.get_instance_info(peer)
            response.raise_for_status()

            if response.status_code != 204:
                data = response.json()
            else: 
                print('NO CONTENT')
            
            # Remove unnecessary keys to make instance file smaller
            keys_to_remove = ['configuration', 'contact_account', 'rules']
            for key in keys_to_remove:
                data.pop(key, None)

            
            uri = data.get('uri')
            if isinstance(uri, str): 
                with self.lock: 
                    self.i += 1 
                    if self.i % 1000 == 0: 
                        self.save_archive()

                print('instances found', self.i, 'for', len(self.scanned), 'scanned',  end='\r')

                # save instance to archive    
                self.archive[peer] = data
                # don't scan anymore when max_depth is exceeded
                if  depth <= self.max_depth: 
                    with self.lock: 
                        self.to_scan.append((peer, depth))
        
        except requests.exceptions.RequestException as err:
            print('first request' + str(err))
            self.archive[peer] = str(err)
            

        

        
    def get_instance_peers(self, instance_name) -> list[str]: 
        params = {'limit': 100}
        r = requests.get('https://' + instance_name + '/api/v1/instance/peers', params=params, timeout=3)
        return eval(r.content)
    
    def get_instance_info(self, instance_name) -> requests.models.Response: 
        r = requests.get('https://' + instance_name + '/api/v1/instance', timeout=4)
        return r
    


if __name__ == "__main__": 
    instancesList = InstanceList()    
    instancesList.deep_scan()   
    # print(len(instancesList.archive.keys()))


