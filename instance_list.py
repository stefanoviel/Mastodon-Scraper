# https://stackoverflow.com/questions/4783735/problem-with-multi-threaded-python-app-and-socket-connections 

import json
import time
import requests
import threading
from tqdm import tqdm

class InstanceList: 
    def __init__(self) -> None:
        self.instances_path = 'data/instances.json'

        self.to_scan = [('mastodon.social', 0)]
        self.max_depth = 0

        f = open(self.instances_path)
        self.archive = json.load(f)
        self.scanned = list(self.archive.keys())
        f.close()

        self.i = 0
        self.lock = threading.Lock()

    def save_archive(self) -> None:
        s = time.time()
        with open(self.instances_path, 'w') as f:
            json.dump(self.archive, f, indent=4)
        print('saved in', round(time.time() - s, 2), 'seconds')


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
                instance, depth = self.to_scan.pop(0)

            try: 
                # get the known peers of the instance
                peers = self.get_instance_peers(instance)   
            except SyntaxError as err: 
                 print(peer, 'as no peers')
            
            prev = 0
            if len(peers) > 50: 
                start_step = 50
            else: 
                start_step = len(peers) -1

            # open 50 threads at the time otherwise connections get lost
            for i in range(start_step, len(peers[:1000]), start_step): 
                threads = []
                for n, peer in enumerate(peers[prev:i]): 
                    with self.lock: 
                        if  peer in self.scanned  : 
                            continue

                    thread = threading.Thread(target=self.scan_peer, args=(peer, depth + 1))
                    thread.start()
                    threads.append(thread)

                for t in threads: 
                    t.join()
                prev = i

        self.save_archive()

        print('finished in', round(time.time() - s, 2), 'seconds - ', self.i, 'instances retrieved')


    def scan_peer(self, peer, depth):
        """
            scan individual instance and save information in the archive
        """ 

        try:
            with self.lock:
                # mark the instance as visited
                self.scanned.append(peer)    

            print(f"Scanning peer: {peer} ")
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
                self.i += 1 
                print(self.i)

                # save instance to archive    
                self.archive[peer] = data
                # don't scan anymore when max_depth is exceeded
                if  depth < self.max_depth: 
                    self.to_scan.append((peer, depth))
        
        except requests.exceptions.RequestException as err:
            # Log the error
            print(f"Error scanning peer {peer}: {type(err)} ")

        
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


