import persistqueue
import datetime
import re
import time

class WaitingList():
    def __init__(self) -> None:
        self.waiting_list = persistqueue.PDict('../data', 'waiting_list')

    def extract_instance_name(self, url):
        pattern = r"(?<=//)(.*?)(?=/)"
        result = re.search(pattern, url)
        if result:
            return result.group(1)

    def extract_username(self, url):
        username = re.search(r"@(.+)", url)
        if username:
            return username.group(0)
        else:
            return username

    def create_waiting_list(self, instance):
        new_queue = {
            "timeout": datetime.datetime.now() + datetime.timedelta(minutes=5),
            "instance_name": instance,
            "users": []
        }
        self.waiting_list[instance] = new_queue

    def put_in_waiting_list(self, url):
        instance_name = self.extract_instance_name(url=url)

        if instance_name not in self.waiting_list:
            self.create_waiting_list(instance_name)
            
        self.insert_to_instance(instance_name, url)
        

    def insert_to_instance(self, instance, info):
        try:
            aux = self.waiting_list[instance]
            aux["users"].append(info)
            self.waiting_list[instance] = aux
            return True
        except Exception as e:
            print("insert_to_instance: {}".format(e))
            return False

    def empty_waiting_list(self, instance):
        users = []
        try:
            aux = self.waiting_list[instance]
            for user in aux["users"]:
                users.append(user)
            del self.waiting_list[instance]
            return users
        except Exception as e:
            print("empty_waiting_list: {}".format(e))
            return False

    def check_waiting_lists_ready(self):
        now = datetime.datetime.now()
        to_empty = []
        for key, value in self.waiting_list.items():
            if value["timeout"] <= now:
                to_empty.append(key)
        return to_empty
    
    def main(self):
        while True:
            to_empy = self.check_waiting_lists_ready()
            if to_empy:
                for instance in to_empy:
                    self.empty_waiting_list(instance=instance)
            time.sleep(5)




