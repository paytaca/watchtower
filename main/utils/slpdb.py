
import json,requests,base64

class SLPDB(object):

    def __init__(self):
        self.base_url = 'https://slpdb.fountainhead.cash/q/'

    def get_data(self, payload):
        raw = json.dumps(payload)
        raw = raw.replace(", ", ",")
        json_query = str(base64.b64encode(raw.encode()).decode())
        resp = requests.get(f"{self.base_url}{json_query}")
        data = resp.json()
        return data['c']


    def get_transactions_by_blk(self, block):
        payload = {
            'v': 3,
            'q': {
                "db": ["c"],
                "find": {
                    "blk.i": block
                },
                "limit": 100000
            }
        }
        return self.get_data(payload)

    

    