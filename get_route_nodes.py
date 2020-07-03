"""
 -----------------------------------------------------------------------------
 Name: get_route_nodes.py
 Description: Finds all OSM nodes along a driving route between two lat/lon
              pairs and outputs the node lat/lons to a csv file. 
              Uses the OSRM routing engine.
       OSRM documentation: http://project-osrm.org/docs/v5.15.2/api/#services
 Created by: Kelly Gilbert, 2018-05-11
 
 Inputs: origin/destination coordinates (line 134)
 Outputs: csv file (route_nodes.csv) that contains the node coordinates
          geojson file that contains the route object
          geojson file that contains the point objects
 -----------------------------------------------------------------------------
 2018-05-27 - Modified variable and function names to be PEP 8 compliant
 2018-05-27 - Removed previous cuml distance and added distance to next node
 2019-08-11 - Changed distance calculations to use a dataframe
 2019-08-12 - Added geojson output for nodes and line (path)
 2020-07-02 - Removed annotations and added steps to OSRM call
            - Changed to parse intersection coordinates from the JSON route 
              response, rather than using the OSM API to get node coordinates
              Removed get_node_coordinates function as a result.
            - Node ID is now the concatenated lat|lon instead of the 
              OSM node ID
 -----------------------------------------------------------------------------
"""


# import modules
import requests
import json
from math import sin, cos, atan2, sqrt, radians
from pandas import isnull, DataFrame, Series, concat
from os import chdir


def gcd(o_lat, o_lon, d_lat, d_lon):
    """
    function to calculate great-circle distance using the Haversine formula
    https://en.wikipedia.org/wiki/Haversine_formula
    https://community.esri.com/groups/coordinate-reference-systems/blog/2017/10/05/haversine-formula
    
    inputs: origin lat/lon, destination lat/lon
    outputs: distance in miles
    """

    # if any of the inputs are null, then  return 0
    if isnull(o_lat) or isnull(o_lon) \
       or isnull(d_lat) or isnull(d_lon):
        return 0

    earth_radius = 3956    # radius of the earth, in miles

    lat_diff = radians(d_lat - o_lat)
    lon_diff = radians(d_lon - o_lon)
    
    a = sin(lat_diff/2)**2 + cos(radians(o_lat)) \
        * cos(radians(d_lat)) * sin(lon_diff/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    d = earth_radius * c

    return d


def get_nodes(o_lat, o_lon, d_lat, d_lon):
    """
    function that finds nodes (intersections) along a driving or walking route 
    # from the Open Source Routing Machine and returns a list containing nodes 
    # along the route
    # http://project-osrm.org/docs/v5.9.1/api/#general-options
    # inputs: origin lat and lon, destination lat and lon for the route
    # outputs: node id, node lat, node lon
    """

    # build OSRM API string for the route
    api_string = 'http://router.project-osrm.org/route/v1/driving/' + str(o_lon) \
                + ',' + str(o_lat) + ';' + str(d_lon) + ',' + str(d_lat) + \
                '?overview=false&steps=true'

    # send the get request
    r = requests.get(api_string)

    # check the result (should be 200); if not, exit the function
    if r.status_code != 200:
        print('get_nodes: unable to process route for (' + str(o_lat) + ', ' + str(o_lon)
              + ") to (" + str(d_lat) + ', ' + d_lat + ')')
        print('  Status = ' + str(r.status_code))
        return
    else:
        pass
    
    # parse the json route response
    # route --> leg --> step --> intersection
    # in this case, there will only be one route/leg in the response
    steps = json.loads(r.text)['routes'][0]['legs'][0]['steps']

    # iterate through the intersections in the route and find the lat/lons
    node_list = []
    for s in steps:
        for i in s['intersections']:
            node_list.append([str(i['location'][1]) + '|' + str(i['location'][0]), \
                                 i['location'][1], i['location'][0] ])                   

    # add the starting and ending points to the list
    node_list.insert(0, ['start', o_lat, o_lon])
    node_list.append(['end', d_lat, d_lon])
    
    return node_list


def point_string(row, points_count):
    """ 
    function that receives a row from a dataframe
    and outputs a geojson-formatted string for the point feature
    """
    point_string = '    {'
    point_string += '      "type": "Feature",'
    point_string += '      "properties": { '
    point_string += '        "node_order": ' + str(row.name) + ','
    point_string += '        "node_id": "' + str(row['node_id']) + '",'
    point_string += '        "distance_from_prev_node": ' + str(row['dist_from_prev']) + ','
    point_string += '        "cuml_distance": ' + str(row['cuml_dist']) + ','
    point_string += '        "distance_to_next_node": ' + str(row['dist_to_next']) + ','
    point_string += '        "type": "route node"'
    point_string += '      },'
    point_string += '      "geometry": {'
    point_string += '        "type": "Point",'
    point_string += '        "coordinates": [' + str(row['node_lon']) + ',' + str(row['node_lat']) + ']'
    point_string += '      }'
    point_string += '    }'
    
    if not int(row.name) == points_count-1:
        point_string += ','
    
    return point_string


def line_string(row, points_count):
    """ 
    function that receives a row from a dataframe
    and outputs a geojson-formatted string for the line feature
    """
    line_string = '[' + str(row['node_lon']) + ',' + str(row['node_lat']) + ']'
    
    if not int(row.name) == points_count-1:
        line_string += ','
    
    return line_string


# -----------------------------------------------------------------------------
# get a list of nodes along the route
# -----------------------------------------------------------------------------

# set the path for output files
chdir('C:\\test')


# return the list of nodes along the route 
# (enter the origin and destination lat/lons here)
node_list1 = get_nodes(33.7354442,-84.3980167 , 33.735652, -84.389573)


# OSRM will find an efficient route. If you want to force a specific route,
# it may be necessary to break up the initial route into sections, calling
# get_nodes for multiple origin/destination pairs
# node_list2 = get_nodes(,,,)
# node_list3 = get_nodes(,,,)


# concatenate the node lists
# if you broke up the route by using multiple calls to get_nodes, add them here
full_node_list = node_list1     # + node_list2 + node_list3


# check the most recent five nodes, as sometimes nodes may be duplicated
# this will also remove duplicates at the beginning/end of a list if the 
# route was broken into parts
node_list_clean = []
prev_5_nodes = [0,0,0,0,0]

print('Before removing dups, the full_node_list contained ' \
      + str(len(full_node_list)) + ' nodes')

for i in range(len(full_node_list)):
    if not full_node_list[i][0] in prev_5_nodes:
        node_list_clean.append(full_node_list[i])

        # update the previous five nodes list
        del prev_5_nodes[0]
        prev_5_nodes.append(full_node_list[i][0])                

print('    After removing dups, the node_list_clean contained ' + str(len(node_list_clean)) \
      + ' nodes')


# -----------------------------------------------------------------------------
# calculate between-node distances
# -----------------------------------------------------------------------------

print('Calculating distances...')

# convert the node list to a dataframe
df = DataFrame(node_list_clean, columns=['node_id', 'node_lat', 'node_lon'])

# add the previous lat/lon and calculate the distance from previous node
df['prev_lat'], df['prev_lon'] = df['node_lat'].shift(), df['node_lon'].shift()
df['dist_from_prev'] = df.apply(lambda row: 
                                gcd(row['prev_lat'], row['prev_lon'], 
                                    row['node_lat'], row['node_lon']), axis=1)

# add the distance to next
df['dist_to_next'] = df['dist_from_prev'].shift(-1)
df['dist_to_next'] = df['dist_to_next'].fillna(0)

# add the cumulative distance
df['cuml_dist'] = df['dist_from_prev'].cumsum()
df['cuml_dist'] = df['cuml_dist'].fillna(0)

# drop the previous node coordinates
df.drop(columns=['prev_lat', 'prev_lon'], inplace=True)


# -----------------------------------------------------------------------------
# write the node list to a csv file
# -----------------------------------------------------------------------------

print('Writing nodes to file...')

df.to_csv(path_or_buf='route_nodes.csv', index=True, index_label='node_order')

print('    ' + str(len(df)) + ' nodes were written to the csv file.')


# -----------------------------------------------------------------------------
# generate the spatial objects
# ----------------------------------------------------------------------------

# generate a geojson file of the point objects
print('Writing nodes geojson file...')

points_count = len(df)

header = '{' 
header += '  "type" : "FeatureCollection",'
header += '  "features" : ['
s_header = Series(header)

footer =  '  ]'
footer += '}'
s_footer = Series(footer)

s_points = df.apply(lambda row: point_string(row, points_count), axis=1)
s_points = concat([s_header, s_points, s_footer], ignore_index=True)

with open('route_points_geojson.geojson', 'w') as f:
    f.write(s_points.to_string(index=False, header=False, na_rep='0'))


# generate a geojson file of the line object
print('Writing line geojson file...')
    
header = '{' 
header += '  "type" : "FeatureCollection",'
header += '  "features" : ['
header += '    {'
header += '      "type" : "Feature",'
header += '      "properties" : {},'
header += '      "geometry" : {'
header += '        "type" : "LineString",'
header += '        "coordinates" : ['
s_header = Series(header)

footer =  '        ]'
footer +=  '      }'
footer +=  '    }'
footer +=  '  ]'
footer += '}'
s_footer = Series(footer)

s_line = df[['node_lat','node_lon']].apply(lambda row: line_string(row, points_count), axis=1)
s_line = concat([s_header, s_line, s_footer], ignore_index=True)

with open('route_line_geojson.geojson', 'w') as f:
    f.write(s_line.to_string(index=False, header=False, na_rep='0'))
    
    
print('Done')