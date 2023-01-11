# Python wrapper for the Open Charge Map API 
# (https://openchargemap.org/site/develop#api)
import requests


class Client:
    def __init__(self, key):
        self.key = key
        
            
    def get_chargers(self, polyline, distance, max_results):
        url = 'https://api.openchargemap.io/v3/poi/output=json'
        params = {
            'key': self.key,        # API key
            'polyline': polyline,   # Route poyline
            'distance' : distance,  # Distance from polyline points
            'distanceunit' : 'km',
            'maxresults': max_results
        }
        response = requests.get(url, params = params)
        if not response.ok:
            raise requests.RequestException(response.text)
        data = response.json()
        return data