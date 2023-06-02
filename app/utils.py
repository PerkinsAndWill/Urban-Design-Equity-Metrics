import json
import os
import time
from typing import List
os.environ['USE_PYGEOS'] = '0'
import streamlit as st
import geopandas as gpd
from shapely import geometry
import pandas as pd
import requests
import osmnx as ox
import networkx as nx
import numpy as np
from census import Census
import pygris

import collections.abc
collections = collections.abc
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


@st.cache_data(persist=True)
def get_network(latitude, longitude, distance, network_type):
    """
    Pull network data from open street maps. Used for porosity with network_type='walk'
    """
    location_point = (latitude,longitude)
    G = ox.graph_from_point(location_point, dist=distance, dist_type='bbox', 
            network_type= network_type, simplify=True)
    GP = ox.project_graph(G)
    edges = ox.graph_to_gdfs(GP, nodes=False, edges=True).reset_index()
    return G, edges


@st.cache_data(persist=True)
def get_porosity(_grid, _network, lat, lng):
    """
    intersects each grid cell with the network, calculates network length per cell

    Args:
        grid (GeoDataframe): grid_df
        network (GeoDataframe): streets/walking routes
    Returns:
        List: length of network inside each cell
    """
    _network = _network.to_crs(_grid.crs)
    porosity = []
    for polygon in _grid.geometry:
        gdf = gpd.GeoDataFrame({'geometry': gpd.GeoSeries([polygon])})
        nw = _network.overlay(gdf, how="intersection")
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
            # print(response.status_code)
            # print(json.loads(response.content)['status'])
        except requests.exceptions.Timeout:
            print("The request timed out")
        except requests.exceptions.RequestException as e:
            print("An error occurred:", e)
    
        results =  json.loads(response.content)
        places.extend(results['results'])
        # print(f'page {i+1}',len(places))
        
        if not "next_page_token" in results:
            break
        params['pagetoken'] = results['next_page_token']
        time.sleep(2)

    # print('all pages',len(places))
    return places


@st.cache_data(persist=True)
def get_all_places(location, radius, category):
    """
    Invoke google api around a center for each location type in the retail file (list_retail.csv)

    Args:
        location (str): 'latitude, longitude' center for the search
        radius (str): radius for the places search
        category (str): on of ["retail", "transit"]
    Returns:
        List[Dict {'coordinates': [lon, lat], 'type': str}] 
    """

    # load private key
    with open("../private_key.txt", 'r') as f:
        key = f.readline().strip()

    # load retail list
    with open(f"../data/list_{category}.csv", "r") as f:
        category_list = [line.strip() for line in f]

    # call google api and store results
    category_points = []
    for retail in category_list:
        places = search_places_by_coordinate(key, location, radius, retail)
        for p in places:
            point = {'coordinates': [p['geometry']['location']['lng'], p['geometry']['location']['lat']],
                        'type': retail}
            category_points.append(point)

    return category_points


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


@st.cache_data(persist=True)
def get_point_density(_grid_df, location_points, normalize=True):

    density = np.zeros((len(_grid_df['geometry']),)).astype(float)
    crs = _grid_df.crs
    _grid_df = _grid_df.to_crs(4326)  # google uses wgs84
    for location in location_points:
        point = geometry.Point(*location['coordinates'])
        density += _grid_df.contains(point).astype(float)

    if normalize:
        density = density / len(location_points)

    _grid_df = _grid_df.to_crs(crs)
    return density.tolist()


def enrich_grid(target_df: gpd.GeoDataFrame, source_df: gpd.GeoDataFrame, porosity: List, retail:list, 
                    transit: list, var_select=None):
    """
    spatial join grid_df with blockgroups_df_equity, select blockgroups within study area
    area interpolation from blockgroups_df_equity to grid_df to get census_df: DONE
    aggregate points_count by each grid: DONE
    join census_df, porosity_df on grid_id: DONE    
    dedupe: TODO
    output equity_grid_df

    Args:
        target_df (GeoDataframe): grid_df
        source_df (GeoDataframe): blockgroups_df_equity
    Returns:
        GeoDataframe: grid data frame with census data bundled in
    
    """

    if var_select is None:
        var_select = list(acs_dict.keys())

    source_df = source_df.to_crs(target_df.crs)

    final_fishnet = area_interpolate(source_df, target_df, extensive_variables=var_select)
    
    final_fishnet = final_fishnet.assign(Porosity=porosity)
    final_fishnet = final_fishnet.assign(Retail=retail)
    final_fishnet = final_fishnet.assign(Transit=transit)
    
    return final_fishnet


def get_acs_code(var_select,filepath = '../data/acs_variable_code.csv'):
    """
    Get Variable Code [ Deprecated ]
    """
    acs_code_df = pd.read_csv(filepath)
    acs_dict = {}
    for i in range(len(acs_code_df)):
        acs_dict[acs_code_df.loc[i,'Variable Name']] = acs_code_df.loc[i,'Variable Code']

    code_list = ['NAME']
    for f in var_select:
        code_list.append(acs_dict[f])
    return tuple(code_list), acs_dict


def get_file_contents(filename):
    """ Given a filename,
        return the contents of that file
    """
    try:
        with open(filename, 'r') as f:
            # It's assumed our file contains a single line,
            # with our API key
            return f.read().strip()
    except FileNotFoundError:
        print("'%s' file not found" % filename)


@st.cache_data(persist=True)
def get_county_census(lat,lng):
    """
    use census API to query the census table
    query for all block groups in selected county

    Args:
        state (str): FIPS code of state
        county (str): FIPS code of county
        variable_names List(str): table names (e.g.'B01003_001E' for total population)
    Returns:
        Dataframe: census block group geometry with corresponding census variables. 
    """

    # read in variable code
    code_list = tuple(acs_dict.values())

    # read in census api
    api_key = get_file_contents('census_api_key.txt')
    c = Census(api_key)
    # get state, county fips codes
    state_fips, state_name, county_fips, county_name = get_fips_code(lat,lng)

    # call census api for selected variables at given location
    sc_census = c.acs5.state_county_blockgroup(fields= code_list, 
                                            state_fips = str(state_fips), 
                                            county_fips = str(county_fips[2::]), 
                                            blockgroup = '*', 
                                            year = 2019)

    
    # Feature Engineering, create geoid
    acs_df = pd.DataFrame(sc_census)
    acs_df['GEOID'] = acs_df['state'] + acs_df['county'] + acs_df['tract'] + acs_df['block group']

    # rename columns back to metrics name for readability
    inv_acs_dict = {v: k for k, v in acs_dict.items()}
    acs_df.rename(columns=inv_acs_dict, inplace=True)

    county_tiger = pygris.block_groups(state = state_fips, county = county_fips[2::], cache = True, year = 2019)

    acs_gdf = county_tiger.merge(acs_df, on='GEOID', how='inner')

    return acs_gdf


def make_iso_poly(G, lat, lng, trip_time=10, speed=4.5, edge_buff=25, node_buff=50, infill=False):
    """
    source: http://kuanbutts.com/2017/12/16/osmnx-isochrones/

    Args:
        G (osmnx graph): travel routes
        trip_time (float): threshold time in min
        speed (float) : travel speed in kmph
    """

    # find center
    # gdf_nodes = ox.graph_to_gdfs(G, edges=False)
    # x, y = gdf_nodes['geometry'].unary_union.centroid.xy
    G = ox.project_graph(G, to_crs='epsg:4326')  # , to_crs="EPSG:3857")4326
    center_node = ox.distance.nearest_nodes(G, lng, lat)

    # add travel time info to graph
    meters_per_minute = speed * 1000 / 60
    for u, v, k, data in G.edges(data=True, keys=True):
        data['time'] = data['length'] / meters_per_minute

    subgraph = nx.ego_graph(G, center_node, radius=trip_time, distance='time')

    node_points = [geometry.Point(data['x'], data['y']) for node, data in subgraph.nodes(data=True)]
    node_points.append(geometry.Point(lat, lng))
    # nodes_gdf = gpd.GeoDataFrame({'id': subgraph.nodes()}, geometry=node_points)
    # nodes_gdf = nodes_gdf.set_index('id')
    nodes_gdf = gpd.GeoDataFrame(geometry=node_points)

    # edge_lines = []
    # for n_fr, n_to in subgraph.edges():
    #     f = nodes_gdf.loc[n_fr].geometry
    #     t = nodes_gdf.loc[n_to].geometry
    #     edge_lines.append(geometry.LineString([f,t]))

    # n = nodes_gdf.buffer(node_buff).geometry
    # e = gpd.GeoSeries(edge_lines).buffer(edge_buff).geometry
    # all_gs = list(n) + list(e)
    # new_iso = gpd.GeoSeries(all_gs).unary_union
    
    # If desired, try and "fill in" surrounded
    # areas so that shapes will appear solid and blocks
    # won't have white space inside of them
    if infill:
        new_iso = geometry.Polygon(new_iso.exterior)
    # return json.loads(gpd.GeoSeries(new_iso).to_json()), subgraph
    return json.loads(nodes_gdf.to_json())


acs_dict = {
    "Total Population": "B01003_001E",
    # "Total Jobs (All Workers)": "B08126_001E",
    "Total Housing Units": "B25001_001E",
    "Total Low Income Population": "C17002_001E",
    "Black Population": "B02001_003E",
    "Hispanic or Latino Population": "B03003_003E",
    "Pct_Rent_Burdened": "B25070_010E",
}