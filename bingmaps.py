# Python wrapper for the Bing Maps Routes API 
# (https://docs.microsoft.com/en-us/bingmaps/rest-services/routes/)
import requests


MAX_LOCATIONS = 40 # Maximum number of locations accepted from the Distance Matrix API


class Client:
    def __init__(self, key):
        self.key = key


    def get_route(self, origin, destination):
        url = 'http://dev.virtualearth.net/REST/V1/Routes/Driving'
        params = {
            'key': self.key,                # API key
            'routeAttributes': 'routePath', # Request for route points
            'wp.0': origin,                 # First route waypoint
            'wp.1': destination             # Last route waypoint
        }
        response = requests.get(url, params = params)
        if not response.ok:
            raise requests.RequestException(response.text)
        data = response.json()
        return data['resourceSets'][0]['resources'][0]
    

    def get_partial_distance_matrix(self, origins, destinations):
        # Coordinates are formatted to the ';' separeted pattern requested from the Distance Matrix API
        formatted_origins = ';'.join('{},{}'.format(coordinate[0],coordinate[1]) for coordinate in origins)
        formatted_destinations = ';'.join('{},{}'.format(coordinate[0],coordinate[1]) for coordinate in destinations)
        url = 'https://dev.virtualearth.net/REST/v1/Routes/DistanceMatrix'
        params = {
            'key': self.key,                # API key
            'travelMode': 'driving',        # Travel model (driving/walking/transit) 
            'origins': formatted_origins,
            'destinations' : formatted_destinations 
        }
        response = requests.get(url, params = params)
        if not response.ok:
            raise requests.RequestException(response.text)
        data = response.json()
        return data['resourceSets'][0]['resources'][0]['results']


    # The Distance Matrix API allows the user to retrieve a limited number of results per request.
    # To bypass this limit get_distance_matrix function splits a big distance matrix request in smaller 
    # requests accepted from the API and then merges them together to return a single matrix.
    def get_distance_matrix(self, origins, destinations):
        results = []
        for i in range(0, len(origins), MAX_LOCATIONS):
            partial_origins = [node.coordinates for node in origins[i : min(i + MAX_LOCATIONS, len(origins))]]
            for j in range(0, len(destinations), MAX_LOCATIONS):
                partial_results = self.get_partial_distance_matrix(
                    origins = partial_origins,
                    destinations = [node.coordinates for node in destinations[j : min(j + MAX_LOCATIONS, len(destinations))]]
                )
                for result in partial_results:
                    result['originIndex'] += i
                    result['destinationIndex'] += j
                results += partial_results
        return results