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

        self.to_scan = [('mastodon.social', -1)]
        self.max_depth = 1

        f = open(self.instances_path)
        self.archive = json.load(f)
        self.scanned = list(self.archive.keys())
        f.close()

        self.CONNECTIONS = 100
        self.TIMEOUT = 3
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
                if len(self.to_scan) > 0:
                    instance, depth = self.to_scan.pop(0)
                else: 
                    break

            try: 
                # get the known peers of the instance
                peers = self.get_instance_peers(instance)   
            except (SyntaxError, requests.exceptions.RequestException) as err : 
                pass
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.CONNECTIONS) as executor:
                future_to_url = (executor.submit(self.scan_peer, url, depth+1) for url in peers)
                for future in concurrent.futures.as_completed(future_to_url):
                    pass
            
     
                
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
                if  depth < self.max_depth: 
                    with self.lock: 
                        self.to_scan.append((peer, depth))
        
        except requests.exceptions.RequestException as err:
            # Log the error
            # print(f"Error scanning peer {peer}: {type(err)} ")
            pass

        

        
    def get_instance_peers(self, instance_name) -> list[str]: 
        params = {'limit': 100}
        r = requests.get('https://' + instance_name + '/api/v1/instance/peers', params=params, timeout=3)
        return eval(r.content)
    
    def get_instance_info(self, instance_name) -> requests.models.Response: 
        r = requests.get('https://' + instance_name + '/api/v1/instance', timeout=4)
        return r
    


if __name__ == "__main__": 
    instancesList = InstanceList()    
    # instancesList.deep_scan()   
    print(len(instancesList.archive.keys()))


