from manageDB import ManageDB
import concurrent.futures
import requests
import logging
import gc
import time

class getInstancesPeers(): 
    def __init__(self, manageDB, params) -> None:
        self.logger = logging.getLogger('my_logger')
        self.logger.setLevel(logging.INFO)

        # self.manageData = manageData
        # self.archive, self.network, self.to_scan = self.manageData.get_network_archive_to_scan()
        self.manageDb = manageDB

        self.MAX_CONNECTIONS = params.get('MAX_CONNECTIONS')
        self.TIMEOUT = params.get('TIMEOUT')
        self.CHUNK_SIZE = 1000


    def get_instances_peers_from_to_scan(self) -> None: 
        """
            Iterate all the instances in to_scan and scrape the peers
        """
        while self.manageDb.size_to_scan() > 0 : 
            print( self.manageDb.size_to_scan())
            list_of_peers = []
            instance_info = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                chunk_to_scan = min(self.CHUNK_SIZE, self.manageDb.size_to_scan())
                for i in range(chunk_to_scan): 
                    self.logger.info(i)
                    self.logger.info('Instances still to scan {0}'.format(self.manageDb.size_to_scan()))

                    instance, depth = self.manageDb.get_next_instance_to_scan()
                    logging.debug(instance)
                    # get the known peers of the instance
                    if not self.manageDb.is_in_archive(instance) or not self.manageDb.instance_has_error(instance): 
                        list_of_peers.append(executor.submit(self.get_instances_peers, instance))
                        instance_info.append((depth, instance))

                for peer, (depth, instance) in zip(concurrent.futures.as_completed(list_of_peers), instance_info): 
                    
                    if peer.result() is not None: 
                        self.manageDb.add_instance_to_network(instance, peer.result(), depth)

                    list_of_peers.remove(peer)

                logging.debug('network', self.manageDb.get_network_size())

            list_of_peers.clear()
            instance_info.clear()
            gc.collect()
        
        # self.manageData.save_archive_network_to_scan()
        self.logger.critical('len network {0}'.format(self.manageDb.get_network_size()))



    def get_instances_peers(self, instance_name) -> list[str]: 
        logging.debug("getting", instance_name)
        try: 
            params = {'limit': 100}
            r = requests.get('https://' + instance_name + '/api/v1/instance/peers', params=params, timeout=3)
            res = eval(r.content)
        except Exception as e : 
            self.logger.debug('peer error {0}'.format(e))
            return None

        return res



if "__main__" == __name__: 
    manageDB = ManageDB()
    manageDB.reset_collections()
    manageDB.init_to_test()

    getpeers = getInstancesPeers(manageDB, {"MAX_CONNECTIONS": 100, "TIMEOUT" : 3})
    getpeers.get_instances_peers_from_to_scan()


