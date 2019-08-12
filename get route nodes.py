"""
 -----------------------------------------------------------------------------
 Name: road_to_tc_18.py
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
 -----------------------------------------------------------------------------
"""


# import modules
import requests
import json
import xml.etree.ElementTree as et
import math
import pandas as pd


def gcd(o_lat, o_lon, d_lat, d_lon):
    """
    function to calculate great-circle distance using the Haversine formula
    https://en.wikipedia.org/wiki/Haversine_formula
    https://community.esri.com/groups/coordinate-reference-systems/blog/2017/10/05/haversine-formula
    
    inputs: origin lat/lon, destination lat/lon
    outputs: distance in miles
    """

    # if any of the inputs are null, then  return 0
    if pd.isnull(o_lat) or pd.isnull(o_lon) or pd.isnull(d_lat) or pd.isnull(d_lon):
        return 0

    earth_radius = 3956    # radius of the earth, in miles

    lat_diff = math.radians(d_lat - o_lat)
    lon_diff = math.radians(d_lon - o_lon)
    
    a = math.sin(lat_diff/2)**2 + math.cos(math.radians(o_lat)) \
        * math.cos(math.radians(d_lat)) * math.sin(lon_diff/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = earth_radius * c

    return d


def get_nodes(o_lat, o_lon, d_lat, d_lon):
    """
    function that finds nodes along a driving or walking route from the Open Source
    Routing Machine and returns a list containing nodes along the route
    http://project-osrm.org/docs/v5.9.1/api/#general-options
    inputs: origin lat and lon, destination lat and lon
    outputs: OSM node id, node lat, node lon
    """

    # build OSRM API string for the route
    api_string = 'http://router.project-osrm.org/route/v1/driving/' + str(o_lon) \
                + ',' + str(o_lat) + ';' + str(d_lon) + ',' + str(d_lat) + \
                '?overview=false&annotations=nodes'

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
    r_parsed = json.loads(r.text)

    # return the routes element, 
    #   then the legs element within that, 
    #   then the annotation element within that,
    #   then the nodes element within that.
    # nodes is a list of OSM node IDs
    routes = r_parsed['routes'][0]
    legs = routes['legs'][0]
    annotation = legs['annotation']
    nodes = annotation['nodes']
    print('  The route contains ' + str(len(nodes)) + ' nodes')

    # iterate through the nodes in the route and find the lat/lon
    print('  Finding lat/lon for each node...')
    node_list = []

    for i in range(len(nodes)):
        # build the API string for the node info
        # NOTE: this API shouldn't be used for recurring, high-volume requests
        # https://operations.osmfoundation.org/policies/api/
        api_string = 'http://api.openstreetmap.org/api/0.6/node/' + str(nodes[i])
    
        # send the get request
        r = requests.get(api_string)
    
        if r.status_code == 200:    # request was successful
            # read in the xml from the response string
            root = et.fromstring(r.text)

            # within the root, find the node element, 
            # then find the lat and lon attributes
            node_lat = float(root.find('node').get('lat'))
            node_lon = float(root.find('node').get('lon'))

            # add info for this node to the node_list
            node_list.append([nodes[i], node_lat, node_lon])
        else:
            print('Lat/lon could not be found for node ' + str(nodes[i]) \
                  + ' (status code = ' + str(r.status_code) + ')')
            
        # every 100 nodes, print a status message
        if i % 100 == 0:
            print('    Completed node ' + str(i) + ' of ' + str(len(nodes)) + '...')

    print('  Done getting nodes')     

    # add the starting and ending points to the list
    node_list.insert(0, ['start', o_lat, o_lon])
    node_list.append(['end', d_lat, d_lon])
    
    return node_list


# -----------------------------------------------------------------------------
# get a list of nodes along the route
# -----------------------------------------------------------------------------
    
# call the get_nodes function to return the list of nodes with lat/lon
node_list1 = get_nodes(33.7676338,-84.5606888 , 30.345284,-81.9633076)


# OSRM will find an efficient route. If you want to force a specific route,
# it may be necessary to break up the initial route into sections
# continue to call get_nodes for each section using node_list2, etc.


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

print('After removing dups, the node_list_clean contained ' + str(len(node_list_clean)) \
      + ' nodes')


# -----------------------------------------------------------------------------
# write the node list to a csv file
# -----------------------------------------------------------------------------

print('Writing nodes to file...')

# create a dataframe of the nodes
df = pd.DataFrame(node_list_clean, columns=['node_id', 'node_lat', 'node_lon'])

# add the previous lat/lon and calculate the distance
df['prev_lat'], df['prev_lon'] = df['node_lat'].shift(), df['node_lon'].shift()
df['dist_from_prev'] = df.apply(lambda row: gcd(row['prev_lat'], row['prev_lon'], row['node_lat'], row['node_lon']), axis=1)

# add the distance to next
df['distance_to_next'] = df['dist_from_prev'].shift(-1)

# add the cumulative distance
df['cuml_dist'] = df['dist_from_prev'].cumsum()

# drop the previous node coordinates
df.drop(columns=['prev_lat', 'prev_lon'], inplace=True)

# write the file
df.to_csv(path_or_buf='route_nodes.csv', index=True, index_label='node_order')

print(str(i+1) + ' nodes were written to the file.')


# -----------------------------------------------------------------------------
# generate the spatial objects
# ----------------------------------------------------------------------------


# generate a geojson file of the point objects
with  open('route_points_geojson.geojson', 'w') as out_file:
    
    # write out the headers
    outfile.writelines('{')
    outfile.writelines('  "type" : "FeatureCollection",')
    outfile.writelines('  "features : [')


    # write out the point objects
    outfile.writelines('    {')
    outfile.writelines('      "type": "Feature",')
    outfile.writelines('      "properties": { ')
    outfile.writelines('        "node_order": 0,')
    outfile.writelines('        " node_id": 2253384929,')
    outfile.writelines('        " distance_from_prev_node": 0,')
    outfile.writelines('        " cuml_distance": 0,')
    outfile.writelines('        " distance_to_next_node": 0.01601983,')
    outfile.writelines('        "type": "route node",')
    outfile.writelines('        "elevation": 298.978363,')
    outfile.writelines('        "smoothed elevation": 298.978363')
    outfile.writelines('      },')
    outfile.writelines('      "geometry": {')
    outfile.writelines('        "type": "Point",')
    outfile.writelines('        "coordinates": [-84.364689,33.8489982]')
    outfile.writelines('      }')
    
    end_comma = ',' if i == len(node_list_clean)-1 else ''
    
    outfile.writelines('    }' + end_comma)
    
    
    # write out the footers    
    outfile.writelines('  ]')
    outfile.writelines('}')





newfile = pygeoj.new()

# add the features to the file
newfile.add_feature(properties={"country":"Norway"},
                    geometry={"type":"Polygon", "coordinates":[[(21,3),(33,11),(44,22)]]} )
newfile.add_feature(properties={"country":"USA"},
                    geometry={"type":"Polygon", "coordinates":[[(11,23),(14,5),(66,31)]]} )

# save the file
newfile.save("test_construct.geojson")




