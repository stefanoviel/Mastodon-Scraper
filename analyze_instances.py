import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math
import json

with open('data/instances_old.json', 'r') as f: 
    data = json.load(f)

df = pd.DataFrame.from_dict(data, orient='index')

df = df.stats.dropna()
users = []
status = []
domain = []

no_domain = 0
for index, row in df.iteritems():
    try: 
        if row['user_count'] is not None and row['status_count'] is not None and row['domain_count'] is not None: 
            users.append(math.log( (int(row['user_count']) + 1)))
            status.append(row['status_count'])
            domain.append(row['domain_count'])
    except KeyError: 
        no_domain += 1


print('instances with no domain', no_domain)



plt.hist(users)
plt.show()


plt.locator_params(numticks=4)
plt.hist(status)
plt.show()

plt.hist(domain)
plt.show()