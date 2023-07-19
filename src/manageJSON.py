import json
import logging
import os


class ManageJSON:
    def __init__(self, db_name: str) -> None:
        self.sep = os.path.sep
        self.logger = logging.getLogger("my_logger")
        self.logger.setLevel(logging.CRITICAL)

        self.db_name = db_name

        self.archive = f".{self.sep}data{self.sep}{db_name}{self.sep}db{self.sep}"
        self.network = f".{self.sep}data{self.sep}{db_name}{self.sep}network{self.sep}"

    def is_in_archive(self, instance_id: str) -> bool:
        json_path = self.get_file_path(self.archive, instance_id)
        return os.path.exists(json_path)

    def is_in_network(self, instance_id: str) -> bool:
        json_path = self.get_file_path(self.network, instance_id)
        return os.path.exists(json_path)

    def insert_one_to_archive(self, info, overwrite=False):
        try:
            id = info["_id"]
            # verify if already exists
            if self.is_in_archive(id) and overwrite == False:
                return

            path = self.create_folder_path(self.archive, id)
            # create path
            os.makedirs(path, exist_ok=True)
            # create file
            json_path = self.get_file_path(self.archive, id)
            if json_path != "":
                with open(json_path, "w") as json_file:
                    json.dump(info, json_file)
        except Exception as e:
            logging.info("insert_one_to_archive: {}".format(e))
            pass

    def insert_many_to_archive(self, elems):
        for elem in elems:
            self.insert_one_to_archive(elem)

    def get_from_archive(self, name):
        try:
            if self.is_in_archive(name):
                json_path = self.get_file_path(self.archive, name)
                with open(json_path, "r") as json_file:
                    return json.load(json_file)
            else:
                return None
        except Exception as e:
            logging.info("get_from_archive: {} name {}".format(e, name))
            return None

    def add_follows_instance(self, instance_id, followers, follower_type: str):
        try:
            id = instance_id
            path = self.create_folder_path(self.archive, id)
            # create path
            os.makedirs(path, exist_ok=True)
            # create file
            json_path = self.get_file_path(self.archive, id, file_type=follower_type)
            if json_path != "":
                with open(json_path, "w") as json_file:
                    json.dump(followers, json_file)
        except Exception as e:
            logging.info("add_follows_instance: {}".format(e))
            pass

    def get_follows_instance(self, instance_id, follower_type: str):
        try:
            if self.is_in_archive(instance_id):
                json_path = self.get_file_path(
                    self.archive, instance_id, file_type=follower_type
                )
                with open(json_path, "r") as json_file:
                    return json.load(json_file)
            else:
                return None
        except Exception as e:
            # logging.info("get_follow_instance: {} name {}".format(e, instance_id))
            return None

    def update_archive(self, user):
        self.insert_one_to_archive(user, overwrite=True)

    def add_peers_instance(self, instance_id, peers):
        try:
            id = instance_id
            path = self.create_folder_path(self.archive, id)
            # create path
            os.makedirs(path, exist_ok=True)
            # create file
            json_path = self.get_file_path(self.archive, id, file_type="peers")
            if json_path != "":
                with open(json_path, "w") as json_file:
                    json.dump(peers, json_file)
        except Exception as e:
            logging.info("add_peers_instance: {}".format(e))
            pass
        # info = self.get_from_archive(instance_id)
        # info["peers"] = peers
        # self.insert_one_to_archive(info, overwrite=True)

    def has_peers(self, name):
        json_path = self.get_file_path(self.archive, name, file_type="peers")
        if os.path.exists(json_path):
            with open(json_path, "r") as jfile:
                return json.load(jfile)
        else:
            return []

    def reset_collections(self):
        pass

    def get_file_path(self, collection: str, key: str, file_type="base_file"):
        """
        generate the json file name and path based on the key as the examples
        file_type = base_file:
        test.it/@myuser = base_dir/it/test/@/my/us/er/myuser.json
        test.it = base_dir/it/test/test.it.json
        file_type = peers:
        test.it = base_dir/it/test/test.it.json
        """
        json_path = ""
        try:
            if self.db_name == "users":
                path = self.create_folder_path(collection, key)
                id_name = key.split("{}".format(self.sep))[1]
                if file_type == "all_follow":
                    json_path = path + f"{id_name}_all_follow.json"
                elif file_type == "followers":
                    json_path = path + f"{id_name}_followers.json"
                elif file_type == "following":
                    json_path = path + f"{id_name}_following.json"
                else:
                    json_path = path + f"{id_name}.json"
            else:
                path = self.create_folder_path(collection, key)
                if file_type == "peers":
                    json_path = path + f"{key}.peers.json"
                else:
                    json_path = path + f"{key}.json"
        except Exception as e:
            logging.info("get_file_path: {}".format(e))

        return json_path

    def create_folder_path(self, base_dir: str, key: str):
        """
        based on the key, create the inverse url as the examples
        test.it/@myuser = base_dir/it/test/@/my/us/er/
        test.it = base_dir/it/test/
        """
        # Remove the username from the key and reverse the order of the remaining parts
        try:
            if self.db_name == "users":
                parts = key.split("{}".format(self.sep))
                server_url = parts[0].split(".")
                server_url.insert(0, "@")
                username = parts[1].lstrip("@")
            else:
                server_url = key.split(".")

            reversed_parts = list(reversed(server_url))

            # Create the subfolders based on the inverse key
            current_path = base_dir
            for part in reversed_parts:
                current_path = os.path.join(current_path, part)

            if self.db_name == "users":
                # count 2 caracters to create subfolder
                for i in range(0, len(username), 2):
                    # Check if the remaining characters are less than 2
                    if i + 1 == len(username):
                        # Read only the last character
                        char = username[i]
                    else:
                        # Read 2 characters at a time
                        char = username[i : i + 2]

                    current_path = os.path.join(current_path, char)

            # Return the path to the final subfolder
            return current_path + self.sep
        except Exception as e:
            logging.info("create_folder_path: {} {}".format(e, key))
            return ""
