import json
import os
import time
from typing import List
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
from shapely import geometry
# import folium
import pandas as pd
import requests
import osmnx as ox
import numpy as np

# import libpysal
import collections.abc
collections = collections.abc
#collections.Iterable = collections.abc.Iterable
from tobler.util import h3fy
from tobler.area_weighted import area_interpolate

ox.config(log_console=True, use_cache=True)
ox.__version__

 
def create_grid(lat=37.78, lng=-122.39, radius=800, size=200):
    """
    Generate a radius buffer centered on the lat, lng and fill with a grid of polygons.

    Args:
        lat (float): latitude of grid center
        lng (float): longitude of grid center
        radius: (float) radius around center in meters, defines grid boundaries
        size (float): cell size of grid in meters
    Returns:
        GeoDataFrame: the generated grid
    """

    # point from lat, lng
    df = pd.DataFrame({'lat': [lat], 'lng': [lng]})
    point = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['lng'], df['lat'],crs="EPSG:4326"))

    # boundary file
    # distance in meters
    boundary = point.to_crs('EPSG:3857').buffer(distance = radius)
    grid_size = size

    # Get the extent of the shapefile
    # Get minX, minY, maxX, maxY
    boundary = boundary.to_crs("EPSG:3857")
    minX, minY, maxX, maxY = boundary.total_bounds
    # Create a fishnet
    minX, minY = minX - 0.5*grid_size, minY - 0.5*grid_size
    x, y = (minX, minY)
    geom_array = []

    while y <= maxY:
        while x <= maxX:
            geom = geometry.Polygon([(x,y), (x, y+grid_size), (x+grid_size, y+grid_size), (x+grid_size, y), (x, y)])
            geom_array.append(geom)
            x += grid_size
        x = minX
        y += grid_size

    fishnet = gpd.GeoDataFrame(geom_array, columns=['geometry']).set_crs(boundary.crs)
    boundary = gpd.GeoDataFrame(boundary)
    boundary = boundary.set_geometry(boundary[0])
    boundary = boundary.drop([0],axis = 1)  # NOTE: why are you dropping this?

    grid_gdf = fishnet.sjoin(boundary, how = 'inner')
    grid_gdf = grid_gdf.drop(['index_right'],axis = 1) # NOTE: why are you dropping this?
    grid_gdf = grid_gdf.to_crs('EPSG:4326')
    
    return grid_gdf


def get_fips_code(lat, lng):
    url = "https://geo.fcc.gov/api/census/block/find"
    params = {
        "latitude": lat,
        "longitude": lng,
        "format": "json"
    }
    response = requests.get(url, params=params)
    data = response.json()
    state_fips = data["State"]["FIPS"]
    state_name = data["State"]["name"]
    county_fips = data["County"]["FIPS"]
    county_name = data["County"]["name"]
    return state_fips,state_name, county_fips, county_name

def get_network(latitude, longitude, distance, network_type):
    """
    Pull network data from open street maps. Used for porosity with network_type='walk'
    """
    location_point = (latitude,longitude)
    G = ox.graph_from_point(location_point, dist=distance, dist_type='bbox', 
            network_type= network_type, simplify=True)
    G = ox.project_graph(G)
    edges = ox.graph_to_gdfs(G, nodes=False, edges=True).reset_index()
    return edges

def get_porosity(grid, network):
    """
    intersects each grid cell with the network, calculates network length per cell

    Args:
        grid (GeoDataframe): grid_df
        network (GeoDataframe): streets/walking routes
    Returns:
        List: length of network inside each cell
    """
    network = network.to_crs(grid.crs)
    porosity = []
    for polygon in grid.geometry:
        gdf = gpd.GeoDataFrame({'geometry': gpd.GeoSeries([polygon])})
        nw = network.overlay(gdf, how="intersection")
        porosity.append(sum(nw.geometry.length))
    return porosity


def search_places_by_coordinate(key, location, radius, type, max_pages=20):
    """
    Use google api to retrieve 'places' around location within radius

    Args:
        key: google api key
        location (str): 'latitude, longitude' center for the search
        radius (str): radius for the places search
        types (str): type of places to search for
    Returns:
        List: places as returned by google api
    """

    endpoint_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    places = []
    params = {
        'location': location,
        'radius': radius,
        'type': type,
        'key': key
    }

    for i in range(max_pages):
        try:
            response = requests.get(endpoint_url, params=params, timeout=(3, 5))
            print(response.status_code)
            print(json.loads(response.content)['status'])
        except requests.exceptions.Timeout:
            print("The request timed out")
        except requests.exceptions.RequestException as e:
            print("An error occurred:", e)
    
        results =  json.loads(response.content)
        places.extend(results['results'])
        print(f'page {i+1}',len(places))
        
        if not "next_page_token" in results:
            break
        params['pagetoken'] = results['next_page_token']
        time.sleep(2)

    print('all pages',len(places))
    return places


def get_all_retail_points(location, radius):
    """
    Invoke google api around a center for each location type in the retail file (list_retail.csv)

    Args:
        location (str): 'latitude, longitude' center for the search
        radius (str): radius for the places search
    Returns:
        List[Dict {'coordinates': [lon, lat], 'type': str}] 
    """

    # load private key
    with open("../private_key.txt", 'r') as f:
        key = f.readline().strip()

    # load retail list
    with open("../data/list_retail.csv", "r") as f:
        retail_list = [line.strip() for line in f]

    # call google api and store results
    retail_points = []
    for retail in retail_list:
        places = search_places_by_coordinate(key, location, radius, retail)
        for p in places:
            point = {'coordinates': [p['geometry']['location']['lng'], p['geometry']['location']['lat']],
                        'type': retail}
            retail_points.append(point)

    return retail_points


def locations_to_geojson(locations):

    features = []
    for loc in locations:
        features.append({ "type": "Feature",
        "geometry": {"type": "Point", "coordinates": loc['coordinates']},
        "properties": {"type": loc['type']}
        }
      )

    geojson_locations = { "type": "FeatureCollection", "features": features}
    return geojson_locations


def get_point_density(grid_df, location_points, normalize=True):

    density = np.zeros((len(grid_df['geometry']),)).astype(float)
    crs = grid_df.crs
    grid_df = grid_df.to_crs(4326)  # google uses wgs84
    for location in location_points:
        point = geometry.Point(*location['coordinates'])
        density += grid_df.contains(point).astype(float)

    if normalize:
        density = density / len(location_points)

    grid_df = grid_df.to_crs(crs)
    return density.tolist()


def enrich_grid(target_df: gpd.GeoDataFrame, source_df: gpd.GeoDataFrame, porosity: List, density:list, var_select):
    """
    spatial join grid_df with blockgroups_df_equity, select blockgroups within study area
    area interpolation from blockgroups_df_equity to grid_df to get census_df: DONE
    aggregate points_count by each grid: TODO
    join census_df, porosity_df on grid_id:
    dedupe: TODO
    output equity_grid_df

    Args:
        target_df (GeoDataframe): grid_df
        source_df (GeoDataframe): blockgroups_df_equity
    Returns:
        GeoDataframe: grid data frame with census data bundled in
    
    """

    source_df = source_df.to_crs(target_df.crs)

    final_fishnet = area_interpolate(source_df, target_df, extensive_variables=var_select)
    
    final_fishnet = final_fishnet.assign(porosity=porosity)

    final_fishnet = final_fishnet.assign(density=density)
    
    return final_fishnet
