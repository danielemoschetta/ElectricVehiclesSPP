# Electric Veichles Shortest Path Problem
# The purpose of this module is, from a set of input parameters, to retrieve the data needed to construct 
# a graph on which to search for the shortest path between a starting location and a destination location.
# Units of measurements used: distance [km], time [h], power [kW], battery capacity [kWh].
import bingmaps
import openchargemap
import polyline
import evspp_pyomo
from math import floor, ceil


MAX_POINTS = 100 # The maximum number of points that form a route
KM_CHARGERS_FACTOR = 0.25 # Conversion factor between route km and max number of charging station to be returned


# Node class stores informations about a node of the graph.
# If a node is a charging station, additional information about the charger type and the charger 
# power has to be provided to the intializer.
class Node:
    def __init__(self, name, coordinates, charger_type = None, charger_power = 0):
        self.name = name
        self.coordinates = coordinates
        self.charger_type = charger_type
        self.charger_power = charger_power
     

    def __str__(self):
        if self.charger_type and self.charger_power:
            return '{} {} charger type {} at {} kW'.format(self.name, str(self.coordinates), str(self.charger_type), str(self.charger_power))
        else:
            return '{} {}'.format(self.name, str(self.coordinates))


    def __repr__(self):
        return str(self)


# check_charger function checks that a given charging station returned by the Open Charge Map API meets the requirements.
# If it meets the requirements, a RouteNode with the retrieved data is returned, otherwise None is returned.
# If more chargers are aviable at the charging station, the one with the best performances will be choosen.
def check_charger(charger):
    name = charger['AddressInfo']['Title']
    coordinates = (round(charger['AddressInfo']['Latitude'], 5), round(charger['AddressInfo']['Longitude'], 5))
    power = None
    for connection in charger['Connections']:
        # Check if required data are aviable
        if connection['PowerKW'] and connection['ConnectionType']['FormalName']:
            # Check if fast type connector is compatible
            if fast_type in connection['ConnectionType']['FormalName']:
                charger_type = connection['ConnectionType']['Title']
                # The real charging power it's the lower between veichle's and charger's ones
                power = min(fast_power, connection['PowerKW'])
                break
            if std_type in connection['ConnectionType']['FormalName']:
                charger_type = connection['ConnectionType']['Title']
                # The real charging power it's the lower between veichle's and charger's ones
                power = min(std_power, connection['PowerKW'])
    # If a compatible charger has been found, then return a RouteNode with the collected data
    if power:
        return Node(name, coordinates, charger_type, power)
    else:
        return None


# get_nodes function retrieves the points that form the route from given origin and destination and then returns 
# a list of nodes containing the origin, the destination and set of the charging stations within a certain 
# distance from the route.
def get_nodes(origin, destination):
    global max_chargers
    route = bingmaps_client.get_route(origin, destination)
    if max_chargers == -1:
        max_chargers = ceil(route['travelDistance'] * KM_CHARGERS_FACTOR)
    all_points = route['routePath']['line']['coordinates']
    # Route points are filtered to get a smaller set of points because the polyline string encoded from the 
    # points will be sent via HTTP GET request, that has maximum length of 2048 characters
    filtered_points = all_points[1 : -1 : floor(len(all_points) / MAX_POINTS)]
    filtered_points.insert(0, all_points[0])
    filtered_points.append(all_points[-1])
    route_polyline = polyline.encode(filtered_points)
    print('{} max charging stations returned\n'.format(max_chargers))
    chargers = openchargemap_client.get_chargers(route_polyline, max_charger_distance, max_chargers)
    nodes = []
    for charger in chargers:
        current = check_charger(charger)
        if current:
            nodes.append(current)
    print('{} aviable charging stations found\n'.format(len(nodes)))
    nodes.insert(0, Node(origin, filtered_points[0]))
    nodes.append(Node(destination, filtered_points[-1]))
    return nodes


# get_route_matrix function retrieves from the Distance Matrix API the adjacency matrix that represents the 
# graph between a list of given nodes.
def get_route_matrix(nodes):
    print('Building route matrix...\n')
    route_matrix = [[None for j in range(len(nodes))] for i in range(len(nodes))]
    results = bingmaps_client.get_distance_matrix(origins = nodes, destinations = nodes)
    for entry in results:
        distance = entry['travelDistance']
        time = entry['travelDuration'] / 60
        # If a certain arc has invalid data or a travel time exceeding the max drive time
        # then the arc is set to the not valid state (-1, -1)
        if time <= 0 or time > max_drive_time:
            route_matrix[entry['originIndex']][entry['destinationIndex']] = (-1, -1)
        else:
            route_matrix[entry['originIndex']][entry['destinationIndex']] = (time, distance)
    return route_matrix


# ampl_set function returns an AMPL formatted string containing the given set.
def ampl_set(name, values):
    content = ' '.join(str(value) for value in values)
    return 'set {} := {} ;'.format(name, content)


# ampl_param functionreturns an AMPL formatted string containing the given param.
def ampl_param(name, param):
    return 'param {} := {} ;'.format(name, param)


# ampl_param_set function returns an AMPL formatted string containing the given param related to the given set.
def ampl_param_set(name, param, set):
    rows = '\n'.join('{} {}'.format(set[i], param[i]) for i in range(len(set)))
    return 'param {} :=\n{}\n;'.format(name, rows)


# ampl_param_sets function returns an AMPL formatted string containing the given param related to the given sets.
def ampl_param_sets(name, param, set_a, set_b):
    rows = '\n'.join('{} {} {}'.format(set_a[i], set_b[j], param[i][j]) for i in range(len(set_a)) for j in range(len(set_b)))
    return 'param {} :=\n{}\n;'.format(name, rows)


if __name__ == '__main__':
    import json
    import sys
    
    # Reading API keys from file
    with open('input\keys.json') as file:
        keys = json.load(file)
    bingmaps_client = bingmaps.Client(key = keys['bingmaps_api'])
    openchargemap_client = openchargemap.Client(key = keys['openchargemap_api'])
    
    # Reading input parameters from file
    with open('input\input.json') as file:
        input = json.load(file)
    origin = input['origin']
    destination = input['destination']
    max_capacity = input['max_capacity']
    start_capacity = input['start_capacity']
    autonomy = input['autonomy']
    std_type = input['std_type']
    std_power = input['std_power']
    fast_type = input['fast_type']
    fast_power = input['fast_power']
    min_charge_time = input['min_charge_time']
    max_charge_time = input['max_charge_time']
    max_drive_time = input['max_drive_time']

    max_chargers = input['max_chargers']
    instance_name = input['instance_name']
    
    #sys.stdout = open('data\{}.log'.format(instance_name),'w')
    
    # Calculating needed parameters from the given ones
    max_charger_distance = autonomy / 10 # 10% of the total autonomy
    min_capacity = max_capacity / 20 # 5% of the total battery capacity
    car_efficiency = max_capacity / autonomy
    
    # Building the graph
    nodes = get_nodes(origin, destination)
    route_matrix = get_route_matrix(nodes)
    
    # Writing the AMPL format file for Pyomo
    with open('data\{}.dat'.format(instance_name), 'w') as writer:
        node_indexes = [i for i in range(len(nodes))]
        writer.writelines('\n\n'.join(
            [
                ampl_set('nodes', node_indexes),
                ampl_param('start_node', node_indexes[0]),
                ampl_param('end_node', node_indexes[-1]),
                ampl_param('max_capacity', max_capacity),
                ampl_param('min_capacity', min_capacity),
                ampl_param('start_capacity', start_capacity),
                ampl_param('car_efficiency', car_efficiency),
                ampl_param('max_charge_time', max_charge_time),
                ampl_param('min_charge_time', min_charge_time),
                ampl_param_set('charger_power', [node.charger_power for node in nodes], node_indexes),
                ampl_param_sets('arc_time', [[entry[0] for entry in row] for row in route_matrix], node_indexes, node_indexes),
                ampl_param_sets('arc_distance', [[entry[1] for entry in row] for row in route_matrix], node_indexes, node_indexes)
            ]
        ))

    print('Charging stations found:')
    for i in range(len(nodes)):
        print('\t{} - {}'.format(i, nodes[i]))
    

    print('Optimizing route...\n')
    # Calling the optimizer
    evspp_pyomo.optimize('data\{}.dat'.format(instance_name))