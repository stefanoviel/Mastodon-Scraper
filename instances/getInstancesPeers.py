from manageData import ManageData
from manageDB import ManageDB
import concurrent.futures
import requests
import logging
import gc
import time

class getInstancesPeers(): 
    def __init__(self,  params) -> None:
        self.logger = logging.getLogger('my_logger')
        self.logger.setLevel(logging.DEBUG)

        # self.manageData = manageData
        # self.archive, self.network, self.to_scan = self.manageData.get_network_archive_to_scan()
        self.manageDb = ManageDB()

        self.MAX_CONNECTIONS = params.get('MAX_CONNECTIONS')
        self.TIMEOUT = params.get('TIMEOUT')
        self.CHUNK_SIZE = 1000


    def get_peers_instances_to_scan(self) -> None: 
        """
            Iterate all the instances in to_scan and scrape the peers
        """
        while self.manageDb.size_to_scan() > 0 : 
            print( self.manageDb.size_to_scan())
            list_of_peers = []
            instance_info = []
            new_network = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                chunk_to_scan = min(self.CHUNK_SIZE, self.manageDb.size_to_scan())
                for i in range(chunk_to_scan): 
                    self.logger.info(i)
                    self.logger.info('Instances still to scan {0}'.format(self.manageDb.size_to_scan()))

                    instance, depth = self.manageDb.get_next_instance_to_scan()

                    # get the known peers of the instance
                    if not self.manageDb.is_in_archive(instance) or not self.manageDb.instance_has_error(instance): 
                        list_of_peers.append(executor.submit(self.get_instance_peers, instance))
                        instance_info.append((depth, instance))

                for peer, (depth, instance) in zip(concurrent.futures.as_completed(list_of_peers), instance_info): 
                    self.logger.debug(peer.result())
                    if peer.result() is not None: 
                        new_network = self.add_connection(new_network, peer.result(), depth, instance)

                    list_of_peers.remove(peer)

                if len(network) != 0:  # if empty => no more instance to scan => break
                    self.network.update(network)
                else: 
                    break
        
        self.manageData.save_archive_network_to_scan()
        self.logger.critical('len network {0}'.format(len(self.network)))

        list_of_peers.clear()
        instance_info.clear()
        
        # self.manageData.save_archive_network_to_scan()
        self.logger.critical('len network {0}'.format(self.manageDb.get_network_size()))


    # def query_instances_chunk(self, to_scan): 
    #     list_of_peers = []
    #     instance_info = []
    #     new_network = {}
    #     manageDb = ManageDB()
    #     with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
    #         chunk_to_scan = min(self.CHUNK_SIZE, len(to_scan))
    #         for i in range(chunk_to_scan): 
    #             self.logger.info(i)
    #             self.logger.info('Instances still to scan {0}'.format(len(to_scan)))

    #             instance, depth = manageDb.get_next_instance_to_scan()

    #             # get the known peers of the instance
    #             if not manageDb.is_in_archive(instance) or not manageDb.instance_has_error(instance): 
    #                 list_of_peers.append(executor.submit(self.get_instance_peers, instance))
    #                 instance_info.append((depth, instance))

    #         for peer, (depth, instance) in zip(concurrent.futures.as_completed(list_of_peers), instance_info): 
    #             self.logger.debug(peer)
    #             if peer.result() is not None: 
    #                 new_network = self.add_connection(new_network, peer.result(), depth, instance)

    #             list_of_peers.remove(peer)

    #     list_of_peers.clear()
    #     instance_info.clear()

        #return new_network  #, self.manageDb.to_scan


    def get_instance_peers(self, instance_name) -> list[str]: 
        try: 
            params = {'limit': 100}
            r = requests.get('https://' + instance_name + '/api/v1/instance/peers', params=params, timeout=3)
            res = eval(r.content)
        except Exception as e : 
            self.logger.debug('peer error {0}'.format(e))
            return None

        return res
    
    def add_connection(self, network, peers, depth, instance) -> dict: 
        if self.manageDb.is_in_network(instance): 
            instance = {}
            instance['peers'] = peers
            instance['depth'] = depth

            network.append(instance)

        return network



if "__main__" == __name__: 
    manageDB = ManageDB()
    manageDB.reset_collections()
    manageDB.init_to_test()
    getpeers = getInstancesPeers( {"MAX_CONNECTIONS": 100, "TIMEOUT" : 3})
    # print(getpeers.manageDb.size_to_scan())
    getpeers.get_peers_instances_to_scan()


