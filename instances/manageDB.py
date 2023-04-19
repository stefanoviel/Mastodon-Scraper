# open connection with DB
# get list of working instances
# update network of instances
# return list with instances to scan to hold in memory

# mongoDB

# recreate what manageDat was doing but with mongodb
from manageData import ManageData
from pymongo import MongoClient
from pymongo import DeleteOne
import logging

class ManageDB(): 
    def __init__(self) -> None:
        self.logger = logging.getLogger('my_logger')
        self.logger.setLevel(logging.CRITICAL)

        self.client = MongoClient('localhost', 27017)

        self.db = self.client["users"]
        self.archive = self.db["archive"]
        self.network = self.db["network"]
        self.to_scan = self.db["to_scan"]

        # TODO: I think json should be used as a queue
        # if self.to_scan.count_documents({'_id': 'to_scan'}) == 1: 
        #     self.to_scan_list = self.to_scan.find_one({'_id': 'to_scan'})["to_scan"]
        # elif self.to_scan.count_documents({'_id': 'to_scan'}) == 0: 
        #     self.to_scan.insert_one({'_id': 'to_scan', 'to_scan' : []})
        #     self.to_scan_list = [('mastodon.social', 0)]


    def is_in_archive(self, instance_id: str) -> bool: 
        return self.archive.count_documents({ "_id": instance_id }) >= 1
    
    def is_in_network(self, instance_id: str) -> bool: 
        return self.network.count_documents({ "_id": instance_id }) >= 1
    
    def instance_has_error(self, instance_id: str) -> bool: 
        # self.archive.find_one({ "_id": instance_id }) 
        return "error" in self.archive.find_one({"_id": instance_id})

    def add_instance_to_network(self, instance_name, peers, depth ) -> None : 
        if not self.is_in_network(instance_name) and type(peers) == list: # check if already presesent to not waste time inserting
            post = {
                "_id" : instance_name, 
                "peers" : peers, 
                "depth" : depth
            }
            self.network.insert_one(post)
    
    def add_instances_to_network(self, instances : list[dict]) -> None: 
        self.network.insert_many(instances)

    def get_next_instance_to_scan(self): 
        res = db.archive.find_one({})
        self.to_scan.delete_one({"_id" : res["_id"]}) 
        return res
    

    def add_to_scan(self, instance, depth): 
        self.to_scan.insert_one({"_id": instance, "depth": depth})

    
    def update_to_scan(self, to_scan): 
        self.to_scan_list = to_scan
        db.to_scan.update_one({
        '_id': "to_scan"
        },{
        '$set': {
            'to_scan': to_scan
        }
        }, upsert=False)

    def size_to_scan(self): 
        return len(self.to_scan_list)
    
    def get_network_size(self): 
        return self.network.count_documents({})

    def init_to_test(self): 
        manageData = ManageData()
        to_insert = []
        for instance in manageData.network['mastodon.social']['peers']: 
            to_insert.append({"_id": instance, "depth" : 1})

        self.to_scan.insert_many(to_insert)
        

    def reset_collections(self): 
        self.archive.drop()
        self.network.drop()
        self.to_scan.drop()
        


# post = {"_id" : 4, "name" : "ste", "score" : 33}
# collection.insert_one(post)

if "__main__" == __name__: 
    db = ManageDB()
    db.reset_collections()

    # post1 = {"_id" : '1', "name" : "ste", "error" : 33}
    # post2 = {"_id" : '2', "name" : "ste", "error" : 33}
    # post3 = {"_id" : '3', "name" : "ste", "score" : 33}
    # post4 = {"_id" : '4', "name" : "ste", "score" : 33}

    # db.archive.insert_many([post1, post2, post3, post4])

    # res = db.archive.find_one({})
    # db.archive.delete_one({"_id" : res["_id"]}) 
    # for d in db.archive.find(): 
    #     print(d)

    # for post in db.archive.find(): 
    #     print(post)

    # print(db.has_error('3'))

    # db.update_to_scan([('mastodon.social', 0)])
    # print(db.to_scan.find_one({'_id': 'to_scan'}))

    db.init_to_test()
    for post in db.to_scan.find(): 
        print(post)







