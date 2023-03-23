import pandas as pd
# import googlemaps
import time
import requests # requests through url
import json
import csv



# Search places by coordinates
def search_places_by_coordinate(key, location, radius):
    
    endpoint_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    places = []
    params = {
        'location': location,
        'radius': radius,
        'key': key
    }
    res = requests.get(endpoint_url, params = params)
    
    results = json.loads(res.content)
    places.extend(results['results'])
    time.sleep(2)
    # print('page1 count',len(places))
    while "next_page_token" in results:
        params['pagetoken'] = results['next_page_token'],
        res = requests.get(endpoint_url, params = params)
        results = json.loads(res.content)
        places.extend(results['results'])
        time.sleep(2)
    print('total count: ',len(places))
    return places



# read in grid_gdf

# create search points from grid centroids
grid_point = grid_gdf.centroid
p = []
i = 0
for index, rows in grid_point.iterrows():
    i+=1
    # need to use your own column name to replace degy, degx
    location_point = str()
    # print(location_point)

    p_i = search_places_by_coordinate(key='INSET-YOUR-API-KEY-HERE', 
                                         location=location_point, 
                                         radius = 'DEFINE-YOUR-SEARCH-RADIUS')
    print(f'=============search_{i} is done!===============')
    p.extend(p_i)