from pymongo import MongoClient
from pymongo import DeleteOne
import pymongo
import logging

class ManageDB(): 

    def __init__(self, db_name: str) -> None:
        """Open connection with DB"""
        self.client = MongoClient('localhost', 27017)

        self.db = self.client[db_name]
        self.archive = self.db["archive"]

    def save_element_to_archive(self, id, element): 
        element['_id'] = id
        self.archive.insert_one(element)

    def is_present_in_archive(self, id): 
        return self.archive.count_documents({'_id': id}) == 1
        