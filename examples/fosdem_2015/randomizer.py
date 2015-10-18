import pymongo
import random
import time
import json
import requests

NUMBER = 20


# Clean the DB
con = pymongo.MongoClient()
con.drop_database('db')

time.sleep(2)

# Create 100 new power
for i in range(NUMBER):
    print
    resource = {"value": i, "status": "pending"}
    resp = requests.post('http://localhost:5001/power/',
                         data=json.dumps({"resource_id": str(i), "resource_data": resource}))
    resp.raise_for_status()

# Sleep

time.sleep(5)

while True:
    value = random.randint(0, 999)
    resource_id = random.randint(0, NUMBER-1)

    resp = requests.patch('http://localhost:5001/power/{}'.format(resource_id),
                          data=json.dumps({"patch": {"$set": {"value": value, "status": "pending"}}}))
    time.sleep(0.05)
