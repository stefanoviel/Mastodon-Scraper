import sys
import os
import unittest
import mock

from src.manage_db.manage_mongo_db import ManageDB

class TestInstanceScanner(unittest.TestCase): 

    def setUp(self) -> None:
        self.manage_db = ManageDB('test')

    @mock.patch("pymongo.collection.Collection.insert_one")
    def test_element_gets_save_in_archive(self, insert_one): 
        element = {'info': 'info'}
        id = 'first'
        self.manage_db.save_element_to_archive(id, element)

        insert_one.assert_called_once_with({'_id': id, 'info': 'info'})

    @mock.patch("pymongo.collection.Collection.count_documents")
    def test_calls_count_documents(self, count_documents): 
        id = 'first'
        self.manage_db.is_present_in_archive(id)
        
        count_documents.assert_called_once_with({'_id': id})

    @mock.patch("pymongo.collection.Collection.count_documents")
    def test_return_correct_if_elements_exists(self, count_documents): 
        count_documents.return_value = 1
        id = 'first'
        res = self.manage_db.is_present_in_archive(id)
        self.assertTrue(res)

        count_documents.return_value = 0
        id = 'first'
        res = self.manage_db.is_present_in_archive(id)
        self.assertFalse(res)


if __name__ == '__main__': 
    unittest.main()
