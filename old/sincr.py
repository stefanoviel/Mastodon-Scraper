from instances.manageDB import ManageDB
import concurrent.futures
import requests
import random
import aiohttp
import asyncio
from url_parser import parse_url
from threading import Thread
import httplib2, sys

import logging
from queue import Queue
from threading import Thread
import gc
import time
import urllib3
import sys

count = 0

@profile
def get_request(url):
    try: 
        with requests.Session() as s:
            r = s.get(url, timeout=3)
            print(len(r.content))
            res = r.content
            r.close()
        return res
    except (requests.exceptions.ConnectionError, SyntaxError, requests.exceptions.ReadTimeout, requests.exceptions.TooManyRedirects, NameError) as e: 
        # print(e)
        # r.close()
        pass


# def getStatus(ourl):
#     try:
#         url = parse_url(ourl)
#         conn = httplib2.HTTPConnection(url.netloc)   
#         print(url.path)
#         conn.request("HEAD", url.path)
#         res = conn.getresponse()
#         return res.status, ourl
#     except:
#         return "error", ourl

manageDB = ManageDB()
manageDB.reset_collections()
manageDB.init_to_test()

results = []


def fun(): 
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        for num, item in enumerate(manageDB.get_next_instance_to_scan()):
            


            instance_name = item.get("_id")
            depth = item.get("depth")
            # res = get_request('https://' + instance_name + '/api/v1/instance/peers')

            results.append(executor.submit(get_request, 'https://' + instance_name + '/api/v1/instance/peers'))

            if num > 1000: 
                break

        for future in concurrent.futures.as_completed(results):
            # print(future)
            if future.result() is not None: 
                print(future.result())

            results.remove(future)
            gc.collect()

    results.clear()
    gc.collect()
    print('sleeping')
    time.sleep(10)

fun()