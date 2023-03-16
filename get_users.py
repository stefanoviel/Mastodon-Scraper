import json
import time
import requests
import threading
from tqdm import tqdm

# scrape a few really popular users from the first local ids of each instance
# start a bfs from each of them save in link and outlink
# keep going up util a certain depth
# find a way to make requests to different instances about the same account

class UserList: 
    def __init__(self) -> None:
        self.userspath = 'data/users.json'

        f = open(self.instances_path)
        self.archive = json.load(f)
        f.close()

    