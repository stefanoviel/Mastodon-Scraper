# https://github.com/TheKinrar/instances
# https://instances.social/api/doc/
# Application ID: 70471419
# Secret token: 9oj4cqwvRNjaFiTNnH9KBayh8acmOHscTrKeEa9dJnb0KJyalCWzMJ4EhJegE0ZDDEZZRxDXvkl2Q0KnlDbk8WS5VNSssSCBxkDCfDZIxE1MX5TcsNnaGrtAG6JHgfNr

from mastodon import Mastodon
import mastodon as m
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

print(len(mastodon.account_followers(1)))

# for i in range(1, 10000): 
#     try: 
#         print(mastodon.account(i))
#     except m.errors.MastodonNotFoundError as err: 
#         print(err, i)
