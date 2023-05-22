# open connection with DB
# get list of working instances
# update network of instances
# return list with instances to scan to hold in memory

# mongoDB

# recreate what manageDat was doing but with mongodb


# 66.3

from pymongo import MongoClient
from pymongo import DeleteOne
import pymongo
import logging

class ManageDB(): 
    def __init__(self, db_name: str) -> None:
        self.logger = logging.getLogger('my_logger')
        self.logger.setLevel(logging.CRITICAL)

        self.client = MongoClient('localhost', 27017)

        self.db = self.client[db_name]
        self.archive = self.db["archive"]
        self.network = self.db["network"]

    def is_in_archive(self, instance_id: str) -> bool: 
        return self.archive.count_documents({ "_id": instance_id }) >= 1
    
    def is_in_network(self, instance_id: str) -> bool: 
        return self.network.count_documents({ "_id": instance_id }) >= 1
    
    def instance_has_error(self, instance_id: str) -> bool: 
        return "error" in self.archive.find_one({"_id": instance_id})
    
    def insert_one_to_archive(self, id, info): 
        try: 
            self.archive.insert_one({"_id" : id, "info" : info})
        except pymongo.errors.DuplicateKeyError:
            pass 

    def insert_many_to_archive(self, elems): 
        self.archive.insert_many(elems)

    def insert_one_instance_to_network(self, instance_name, peers, depth ) -> None : 
        if type(peers) == list: 
            post = {
                "_id" : instance_name, 
                "peers" : peers, 
                "depth" : depth
            }
            try: 
                self.network.insert_one(post)
            except pymongo.errors.DuplicateKeyError:
                pass 

            del post

    # def insert_user_followers(self, user_id, followers): 
    #     user = self.archive.find_one({"_id": user_id})
    #     if user is None: 
    #         user = {"_id": user_id, "followers" : followers, "following" : []}
    #     else: 
    #         user["followers"] = user["followers"] + followers
        
    #     self.archive.insert_one(user)
    
    def insert_many_instances_to_network(self, instances : list[dict]) -> None: 
        self.network.insert_many(instances)

    def get_from_archive(self, name): 
        return self.archive.find_one({'_id': name})
    
    def update_archive(self, user, followers): 
        if followers: 
            self.archive.update_one({'_id': user['_id']}, {"$set": {'followers':user['followers']}}, upsert=False)
        else: 
            self.archive.update_one({'_id': user['_id']}, {"$set": {'following':user['following']}}, upsert=False)

    def size_network(self): 
        return self.network.count_documents({})
    
    def size_archive(self): 
        return self.archive.count_documents({})

    def init_to_test(self): 
        mastodon_peers = open('data/peers.txt').read().splitlines()
        to_insert = [{"_id": instance, "depth" : 1} for instance in mastodon_peers ]
        self.to_scan.insert_many(to_insert)
        

    def reset_collections(self): 
        self.archive.drop()
        self.network.drop()


if "__main__" == __name__: 
    # db = ManageDB('test')
    # for i in db.archive.find([{'_id': 'mofu.one'}, {'_id': 'mastodon.social'}]): 
        # print('o')


    # for i in db.archive.find({}): 
    #     print(i['_id'])
    
    # db.insert_one_to_archive('aa', {'aas': 33})

    print('tutto ok')

    # db.reset_collections()




