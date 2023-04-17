import json
import time
import logging
from typing import Tuple


class ManageData: 
    def __init__(self) -> None:
        logging.basicConfig(level=logging.INFO)

        self.instances_path = 'data/instances/instances.json'
        self.instances_network_path = 'data/instances/instances_network.json'
        self.to_scan_path = 'data/instances/instances_to_scan.json'

        with open(self.instances_path) as f: 
            self.archive = json.load(f)

        with open(self.instances_network_path) as f: 
            self.network = json.load(f)

        with open(self.to_scan_path) as f: 
            self.to_scan = json.load(f)

        if 'to_scan' in self.to_scan: 
            self.to_scan = self.to_scan['to_scan']
        
        # initialize instances to scan next if empty starting from mastodon.social
        if len(self.to_scan) == 0: 
            self.to_scan = [('mastodon.social', 0)]


    def save_archive_network_to_scan(self) -> None:

        print('from data class', len(self.network))

        s = time.time()
        with open(self.instances_path, 'w') as f:
                json.dump(self.archive, f, indent=4)

        with open(self.instances_network_path, 'w') as f:
            json.dump(self.network, f, indent=4)

        with open(self.to_scan_path, 'w') as f: 
            json.dump({'to_scan': self.to_scan}, f, indent=4)

        logging.info('saved in {0} seconds'.format(round(time.time() - s, 2)))

    def get_network_archive_to_scan(self) -> Tuple[dict, dict, dict]: 
        return self.network, self.network, self.to_scan


if "__main__" == __name__: 
    manageData = ManageData()
    
    print(list(manageData.archive.items())[:100])
    print(list(manageData.network.items())[:100])
    print(manageData.to_scan[:100])
    manageData.save_archive_network_to_scan()

    