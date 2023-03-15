# https://github.com/TheKinrar/instances
# https://instances.social/api/doc/
# Application ID: 70471419
# Secret token: 9oj4cqwvRNjaFiTNnH9KBayh8acmOHscTrKeEa9dJnb0KJyalCWzMJ4EhJegE0ZDDEZZRxDXvkl2Q0KnlDbk8WS5VNSssSCBxkDCfDZIxE1MX5TcsNnaGrtAG6JHgfNr

from mastodon import Mastodon
import json
import requests
import pandas as pd
from mastodon.internals import Mastodon as Internals


Mastodon.create_app(
    'pytooterapp',
    api_base_url = 'https://mastodon.social',
    to_file = 'pytooter_clientcred.secret'
)


mastodon = Mastodon(client_id = 'pytooter_clientcred.secret',)
mastodon.log_in(
    'stefi.viel@gmail.com',
    'Q4kqh@d2fFuR67@',
    to_file = 'pytooter_usercred.secret'
)


# r = requests.get('https://instances.social/api/1.0/instances/list', headers={'Authorization': 'Bearer 9oj4cqwvRNjaFiTNnH9KBayh8acmOHscTrKeEa9dJnb0KJyalCWzMJ4EhJegE0ZDDEZZRxDXvkl2Q0KnlDbk8WS5VNSssSCBxkDCfDZIxE1MX5TcsNnaGrtAG6JHgfNr'})
# print(len(json.loads(r.content)))

class Mine(Internals): 



    def instance(self):
        """
        Internal, non-version-checking helper that does the same as instance()
        """
        instance = super().api_request('GET', '/api/v1/instance/')
        return instance

if __name__ == "__main__": 
    m = Mine()
    print(m.instance())








