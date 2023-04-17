# https://stackoverflow.com/questions/4783735/problem-with-multi-threaded-python-app-and-socket-connections 
# 1008303


# https://unqlite-python.readthedocs.io/en/latest/quickstart.html

import copy
import json
import time
import sys
import requests
import threading
import concurrent.futures
import asyncio
import gc


from tqdm import tqdm

# 2000 trovate attive in 40 min => mastodon dice 12000 attive 40*6 240 = 4 ore



class InstanceList: 
    def __init__(self) -> None:
        self.instances_path = 'data/instances.json'
        self.instances_network_path = 'data/instances_network.json'
        self.to_scan_path = 'data/instances_to_scan.json'

        with open(self.instances_path) as f: 
            self.archive = json.load(f)

        with open(self.instances_network_path) as f: 
            self.network = json.load(f)

        with open(self.to_scan_path) as f: 
            self.to_scan = json.load(f)

        if 'to_scan' in self.to_scan: 
            self.to_scan = self.to_scan['to_scan']
        
        if len(self.to_scan) == 0: 
            self.to_scan = [('mastodon.social', 0)]

        
        self.max_depth = 2
        self.MAX_CONNECTIONS = 100
        self.TIMEOUT = 3
        self.SAVE_EVERY = 1000
        self.successful_response = 0 
        self.successful_peer_request = 0 
        self.lock = threading.Lock()

    def save_archive(self) -> None:
        s = time.time()
        with open(self.instances_path, 'w') as f:
                json.dump(self.archive, f, indent=4)

        with open(self.instances_network_path, 'w') as f:
            json.dump(self.network, f, indent=4)

        with open(self.to_scan_path, 'w') as f: 
            json.dump({'to_scan': self.to_scan}, f, indent=4)

        print('saved in', round(time.time() - s, 2), 'seconds')

    def add_connection(self, peers, depth, instance) -> None: 
        if instance not in self.network: 
            self.network[instance] = {}
            self.network[instance]['peers'] = peers
            self.network[instance]['depth'] = depth

    def get_all_peers(self) -> None: 
        still_to_scan = len(self.to_scan)
        
        while still_to_scan > 0: 
            list_of_peers = []
            instance_info = []
            step = still_to_scan

            print('still to scan', still_to_scan)
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                while still_to_scan > 0 and still_to_scan > step - 200: 
                    instance, depth = self.to_scan.pop(0)
                    # get the known peers of the instance
                    if instance not in self.archive or 'error' not in self.archive[instance]: 
                        list_of_peers.append(executor.submit(self.get_instance_peers, instance))
                        instance_info.append((depth, instance))
                    
                    still_to_scan -= 1

                    if still_to_scan % 2000 == 0: 
                        self.save_archive()


                for peer, (depth, instance) in zip(concurrent.futures.as_completed(list_of_peers), instance_info): 
                    # print(peer)
                    if peer.result() is not None: 
                        self.add_connection(peer.result(), depth, instance)

                    list_of_peers.remove(peer)


            
                del list_of_peers[:]
                del instance_info[:]
                del list_of_peers
                del instance_info

            

        print('len network', len(self.network))



    def chunks(self, lst, n):
        """Yield successive n-sized chunks from lst."""
        try: 
            for i in range(0, len(lst), n):
                yield lst[i:i + n]
        except TypeError as tp: 
            return []


    def scan_known_instances(self) -> None: 
        network = copy.deepcopy(self.network)
        # scanning = 0
        for instance in network: 
            print(instance)
            for peers in self.chunks(network[instance]['peers'], 200): 

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                    for peer in peers: 
                        if peer not in self.archive : 
                            # scanning += 1
                            executor.submit(self.scan_peer, peer, network[instance]['depth']+1)



    def scan_peer(self, peer, depth):
        """
            scan individual instance and save information in the archive
        """ 
        try:

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
                    self.successful_response += 1 
                    if self.successful_response % self.SAVE_EVERY == 0: 
                        print('saving')
                        try: 
                            self.save_archive()
                        except Exception as e: 
                            print(e)
                    
                    self.archive[peer] = data

                print('instances found', self.successful_response, 'for', len(self.archive), 'scanned')

                # save instance to archive    
                # don't scan anymore when max_depth is exceeded
                if  depth <= self.max_depth: 
                    with self.lock: 
                        # print('adding', peer)
                        self.to_scan.append((peer, depth))
        
        except requests.exceptions.RequestException as err:
            # print('first request' + str(err))
            with self.lock: 
                self.archive[peer] = {'error': str(err)}


    def get_instance_peers(self, instance_name) -> list[str]: 
        try: 
            params = {'limit': 100}
            r = requests.get('https://' + instance_name + '/api/v1/instance/peers', params=params, timeout=3)
            res = eval(r.content)
        except Exception as e : 
            # print('peer error', e)
            return None

        return res
    
    def get_instance_info(self, instance_name) -> requests.models.Response: 
        r = requests.get('https://' + instance_name + '/api/v1/instance', timeout=4)
        return r
    

    def main(self) -> None: 
        """
            with a BFS scan all instances up to self.max_depth
        """ 
        s = time.time()
        
        still_to_scan = len(self.to_scan)

        
        while still_to_scan > 0: 

            # self.get_all_peers()
            self.get_all_peers()
            self.save_archive()
            
            self.scan_known_instances()
            self.save_archive()

            still_to_scan = len(self.to_scan)
                
        self.save_archive()
        print('finished in', round(time.time() - s, 2), 'seconds - ', self.successful_response, 'instances retrieved')



if __name__ == "__main__": 
    instancesList = InstanceList()    
    instancesList.main()   
    # print(len(instancesList.archive.keys()))

    # to_scan = {'to_scan': [ (instance, 1) for instance in instancesList.network['mastodon.social']['peers']]}
    # with open(instancesList.to_scan_path, 'w') as f: 
    #     json.dump(to_scan, f, indent=4)
    



