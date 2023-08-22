import datetime
import re
import time
from threading import Lock

import persistqueue
import requests

from manageJSON import ManageJSON
from tickets import TicketManager


class UserCollector:
    def __init__(self, ticketmanager: TicketManager) -> None:
        """
        Collects user information from mastodon
        userl_url: The user URL e.g https://my.mastodon.server/@myname
        """
        self.ticketmanager = ticketmanager
        self.manageJSON = ManageJSON("users")
        self.main_queue = persistqueue.UniqueAckQ(
            "data/main_queue", "main_queue", multithreading=True
        )
        self.federated_queue = persistqueue.UniqueAckQ(
            "data/federated_queue", "federated_queue", multithreading=True
        )
        self.error_queue = persistqueue.UniqueAckQ(
            "data/error", "error", multithreading=True
        )

    def add_to_queue(self, user_url: str):
        self.main_queue.put(user_url)

    def remove_https(self, url: str):
        """Remove HTTPS from URL"""
        return url.replace("https://", "")

    def get_seconds_difference(self, date1, date2):
        """Gets the integer seconds difference between two dates."""
        difference = date2.replace(tzinfo=None) - date1.replace(tzinfo=None)
        return difference.total_seconds()

    def convert_string_to_datetime(self, string):
        """Converts a string to a datetime object."""
        datetime_object = datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.%fZ")
        return datetime_object

    def extract_username(self, url):
        """extract username from url"""
        username = re.search(r"@(.+)", url)
        if username:
            return username.group(0)
        else:
            return username

    def extract_instance_name(self, url):
        """extract instance name from url"""
        pattern = r"(?<=//)(.*?)(?=/)"

        result = re.search(pattern, url)
        if result:
            return result.group(1)

    def get_user_id(self, server_url: str, username: str, lock: Lock):
        """Retrive the numerical id from a username in a server"""
        url = "https://{}/api/v1/accounts/lookup?acct={}".format(server_url, username)

        self.verify_resources(server_url=server_url, lock=lock)
        response = requests.get(url)

        if response.status_code == 200:
            aux = response.json()
            return aux["id"]
        else:
            return None

    def get_user_info(self, server_url: str, username: str, lock: Lock):
        """Retrive user iformationf from a Mastodon server using the numerical user id"""
        url = "https://{}/api/v1/accounts/{}".format(server_url, username)

        self.verify_resources(server_url=server_url, lock=lock)
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            return None

    def get_followees(
        self,
        _id: str,
        server_url: str,
        user_server_id: str,
        followers_or_following: str,
        lock: Lock,
    ):
        """Retrive Followers or Following users from a Mastodon User"""
        users = []
        count = 0
        url = "https://{}/api/v1/accounts/{}/{}".format(
            server_url, user_server_id, followers_or_following
        )
        while url != "":
            count += 1

            self.verify_resources(server_url=server_url, lock=lock)
            response = requests.get(url, params={"limit": 80})

            if response.status_code == 200:
                self.save_data_info(response.json())
                self.save_followers_following(_id, response.json(), url)
                if "next" in response.links.keys():
                    url = str(response.links["next"]["url"])
                else:
                    url = ""
            elif response.status_code == 429:
                """Save in case of conflict with tickets"""
                time_for_reset = self.convert_string_to_datetime(
                    response.headers["x-ratelimit-reset"]
                )
                now = datetime.datetime.now(datetime.timezone.utc)
                waiting_time = int(self.get_seconds_difference(now, time_for_reset)) + 1
                # print("waiting {} seconds".format(waiting_time))
                if waiting_time > 0:
                    time.sleep(waiting_time)
                else:
                    time.sleep(60)
            else:
                url = ""

        return users

    def save_data_info(self, user_list: list[dict]):
        """Save user info from Followers/Followees of a user"""
        to_save = []

        for r in user_list:
            r["_id"] = self.remove_https(r["url"])
            r["instance"] = self.extract_instance_name(r["url"])

            if not self.manageJSON.is_in_archive(r["_id"]):
                to_save.append(r)
            if not self.manageJSON.has_followers(r["_id"]):
                if self.extract_instance_name(r["url"]) == "mastodon.social":
                    self.main_queue.put(r["url"])
                else:
                    self.federated_queue.put(r["url"])

        if len(to_save) > 0:
            self.manageJSON.insert_many_to_archive(to_save)

    def save_followers_following(self, id: str, user_list: list, url: str):
        """Save Followers/Followees"""
        current_all = self.manageJSON.get_follows_instance(
            id, follower_type="all_follow"
        )

        peers_id = [self.remove_https(user.get("url")) for user in user_list]
        peers_id = list(filter(lambda item: item is not None, peers_id))

        if "followers" in url:
            current_followers = self.manageJSON.get_follows_instance(
                id, follower_type="followers"
            )
            if current_followers:
                current_followers.extend(peers_id)
                # remove duplicates
                # current_followers = list(dict.fromkeys(current_followers))
                self.manageJSON.add_follows_instance(
                    id, current_followers, follower_type="followers"
                )
            else:
                self.manageJSON.add_follows_instance(
                    id, peers_id, follower_type="followers"
                )
        elif "following" in url:
            current_following = self.manageJSON.get_follows_instance(
                id, follower_type="following"
            )
            if current_following:
                current_following.extend(peers_id)
                # remove duplicates
                # current_following = list(dict.fromkeys(current_following))
                self.manageJSON.add_follows_instance(
                    id, current_following, follower_type="following"
                )
            else:
                self.manageJSON.add_follows_instance(
                    id, peers_id, follower_type="following"
                )

        if current_all:
            current_all.extend(peers_id)
            # remove duplicates
            # current_all = list(dict.fromkeys(current_all))
            self.manageJSON.add_follows_instance(
                id, current_all, follower_type="all_follow"
            )
        else:
            self.manageJSON.add_follows_instance(
                id, peers_id, follower_type="all_follow"
            )

    def verify_resources(self, server_url: str, lock: Lock):
        """Verify if the collector has the resources to request information from a mastodon server, if not wait"""
        flag = False
        while not flag:
            with lock:
                flag = self.ticketmanager.consume_ticket(server_url)
            if not flag:
                time_to_wait = self.ticketmanager.get_timeout(server_url)
                if time_to_wait > 0:
                    time.sleep(time_to_wait)
                else:
                    time.sleep(60)
                    flag = True

    def status(self):
        while True:
            print("M.Social Users to analyze: {}".format(self.main_queue.size))
            print("Federated Users to analyze: {}".format(self.federated_queue.size))
            print("Errors: {}".format(self.error_queue.size))
            time.sleep(60)

    def collect_data(self, lock: Lock):
        while True:
            try:
                with lock:
                    user_url = self.main_queue.get()
                    self.main_queue.ack(user_url)
                    # print("Users to analyze: {}".format(self.main_queue.size))

                # print("Collecting Data From {}".format(user_url))
                server_url = self.extract_instance_name(user_url)
                username = self.extract_username(user_url)
                _id = self.remove_https(user_url)

                user_server_id = self.get_user_id(server_url, username, lock)
                user_info = self.get_user_info(server_url, user_server_id, lock)

                self.save_data_info([user_info])

                self.get_followees(_id, server_url, user_server_id, "following", lock)
                self.get_followees(_id, server_url, user_server_id, "followers", lock)
            except Exception as e:
                # print("UserCollector:collect_data:{}: {}".format(user_url, e))
                self.error_queue.put(user_url)
                time.sleep(30)

    def collect_data_federated(self, lock: Lock):
        while True:
            try:
                with lock:
                    user_url = self.federated_queue.get()
                    self.federated_queue.ack(user_url)
                    # print(
                    #     "Federated Users to analyze: {}".format(
                    #         self.federated_queue.size
                    #     )
                    # )

                # print("Collecting Data From {}".format(user_url))
                server_url = self.extract_instance_name(user_url)
                username = self.extract_username(user_url)
                _id = self.remove_https(user_url)

                user_server_id = self.get_user_id(server_url, username, lock)
                user_info = self.get_user_info(server_url, user_server_id, lock)

                self.save_data_info([user_info])

                self.get_followees(_id, server_url, user_server_id, "following", lock)
                self.get_followees(_id, server_url, user_server_id, "followers", lock)
            except Exception as e:
                # print("UserCollector:collect_data:{}: {}".format(user_url, e))
                self.error_queue.put(user_url)
                time.sleep(30)
