import datetime
import time

import persistqueue


class TicketManager:
    def __init__(self) -> None:
        self.tickets = persistqueue.PDict(
            "data/tickets", "tickets", multithreading=True
        )
        self.tickets.auto_commit = False
        self.keys = persistqueue.UniqueAckQ(
            "data/keys",
            "ticket_keys",
            multithreading=True,
        )
        self.MAX_NUMBER_OF_TICKETS = 300

    def exits(self, instance: str) -> bool:
        keys = [k["data"] for k in self.keys.queue()]
        return instance in keys

    def create_tickets_for_instance(self, instance: str):
        self.tickets[instance] = {
            "instance_name": instance,
            "tickets": self.MAX_NUMBER_OF_TICKETS,
            "time_out": datetime.datetime.now() + datetime.timedelta(minutes=5),
        }
        self.tickets.task_done()
        self.keys.put(instance)
        self.keys.task_done()

    def consume_ticket(self, instance: str):
        try:
            if (instance == "") or (instance == None):
                return True
            try:    
                aux = self.tickets[instance]
            except KeyError as e:
                self.create_tickets_for_instance(instance)
                aux = self.tickets[instance]

            if aux["tickets"] <= 0:
                return False

            aux["tickets"] -= 1

            self.tickets[instance] = aux
            self.tickets.task_done()

            return True
        except Exception as e:
            print("TicketManager:consume_ticket: {}".format(e))
            return False

    def get_timeout(self, instance: str) -> int:
        """Returns in seconds the time to wait for more tickets to be generated"""
        try:
            if instance not in self.tickets:
                return 0
            aux = self.tickets[instance]
            now = datetime.datetime.now()
            time_to_wait = int(self.get_seconds_difference(now, aux["time_out"])) + 1
            return time_to_wait
        except Exception as e:
            print("TicketManager:get_timeout: {}".format(e))
            return 0

    def add_tickets(self, instance):
        aux = self.tickets[instance]

        aux["tickets"] = self.MAX_NUMBER_OF_TICKETS
        aux["time_out"] = datetime.datetime.now() + datetime.timedelta(minutes=5)

        self.tickets[instance] = aux
        self.tickets.task_done()

    def print_tickets(self):
        for key in self.keys.queue():
            try:
                key = key["data"]
                print("{} : {}".format(key, self.tickets[key]))
            except Exception as e:
                print(e)
                continue

    def remove_none(self):
        for i in range(self.keys.size):
            k = self.keys.get()
            if k is None:
                self.keys.ack(k)
            
    def update_tickets(self):
        while True:
            # self.print_tickets()
            #self.remove_none
            now = datetime.datetime.now()

            for key in self.keys.queue():
                try:
                    key = key["data"]
                    value = self.tickets[key]
                    if value["time_out"] < now:
                        self.add_tickets(instance=key)
                    if value["tickets"] <= 0:
                        print("{} : {}".format(key, self.tickets[key]))
                except KeyError as e:
                    self.consume_ticket(key)
                    continue
                except Exception as e:
                    print("TicketManager:update_tickets:{}: {}".format(key, e))
                    continue

            time.sleep(60)
            


    def get_seconds_difference(self, date1, date2):
        """Gets the integer seconds difference between two dates."""
        difference = date2.replace(tzinfo=None) - date1.replace(tzinfo=None)
        return difference.total_seconds()
