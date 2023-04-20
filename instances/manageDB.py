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


    def is_in_archive(self, instance_id: str) -> bool: 
        return self.archive.count_documents({ "_id": instance_id }) >= 1
    
    def is_in_network(self, instance_id: str) -> bool: 
        return self.network.count_documents({ "_id": instance_id }) >= 1
    
    def instance_has_error(self, instance_id: str) -> bool: 
        return "error" in self.archive.find_one({"_id": instance_id})

    def add_one_instance_to_network(self, instance_name, peers, depth ) -> None : 
        if not self.is_in_network(instance_name) and type(peers) == list: # check if already presesent to not waste time inserting
            post = {
                "_id" : instance_name, 
                "peers" : peers, 
                "depth" : depth
            }
            self.network.insert_one(post)
    
    def add_many_instances_to_network(self, instances : list[dict]) -> None: 
        self.network.insert_many(instances)

    def get_next_instance_to_scan(self): 
        size = self.size_to_scan()
        print(size)
        while size > 0: 
            res = self.to_scan.find_one({})
            self.to_scan.delete_one({"_id" : res["_id"]}) 
            size -= 1
            yield res
    
    def add_to_scan(self, instance, depth): 
        self.to_scan.insert_one({"_id": instance, "depth": depth})

    def size_to_scan(self): 
        return self.to_scan.count_documents({})
    
    def size_network(self): 
        return self.network.count_documents({})
    
    def size_archive(self): 
        return self.archive.count_documents({})

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
    for i in db.get_next_instance_to_scan(): 
        print(i)






