import time
from threading import Lock, Thread

from tickets import TicketManager
from user_collector import UserCollector
from waiting_list import WaitingList

FIRST_TIME = False
NUMBER_THREADS = 20
NUMBER_THREADS_FEDERATED = 20


ticket_manager = TicketManager()
waiting_list = WaitingList()

ticket_thread = Thread(target=ticket_manager.update_tickets)
ticket_thread.start()

u = UserCollector(ticketmanager=ticket_manager)

if FIRST_TIME:
    u.add_to_queue("https://mastodon.social/@mastodon")
    u.add_to_queue("https://mastodon.social/@MrLovenstein")

status = Thread(target=u.status)
status.daemon = True
status.start()

lock = Lock()
for i in range(NUMBER_THREADS):
    t = Thread(target=u.collect_data, args=(lock,))
    t.daemon = True
    t.start()
    time.sleep(5)

for i in range(NUMBER_THREADS_FEDERATED):
    t = Thread(target=u.collect_data_federated, args=(lock,))
    t.daemon = True
    t.start()
    time.sleep(5)
