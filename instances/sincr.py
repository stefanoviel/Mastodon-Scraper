from manageDB import ManageDB
import concurrent.futures
import requests
import random
import aiohttp
import asyncio
import logging
from queue import Queue
from threading import Thread
import gc
import time
import urllib3

def get_request(url):
    try: 
        r = requests.get(url, timeout=3)
        return eval(r.content)
    except (requests.exceptions.ConnectionError, SyntaxError, requests.exceptions.ReadTimeout, requests.exceptions.TooManyRedirects, NameError) as e: 
        print(e)


manageDB = ManageDB()
manageDB.reset_collections()
manageDB.init_to_test()

for num, item in enumerate(manageDB.get_next_instance_to_scan()):
    instance_name = item.get("_id")
    depth = item.get("depth")
    res = get_request('https://' + instance_name + '/api/v1/instance/peers')


    if res is not None: 
        print('result len' , len(res)) 
        manageDB.add_one_instance_to_network(instance_name, res, depth)
