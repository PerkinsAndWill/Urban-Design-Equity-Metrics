import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
from shapely import geometry
# import folium
import pandas as pd
import requests

# import libpysal
import collections.abc
collections = collections.abc
#collections.Iterable = collections.abc.Iterable
from tobler.util import h3fy
from tobler.area_weighted import area_interpolate


 
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


def get_county_census_data(state, county, variable_names):
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
    raise NotImplementedError


def census_features(census_df):
    """
    Calculate the metrics using the cencus raw data.

    Args:
        census_df (Dataframe): census block groups dataframe
    Returns:
        Dataframe: bloc kgroups dataframe with calculated equity features. 
    
    """
    raise NotImplementedError


def enrich_grid(target_df: gpd.GeoDataFrame, source_df: gpd.GeoDataFrame, var_select):
    """
    spatial join grid_df with blockgroups_df_equity, select blockgroups within study area
    area interpolation from blockgroups_df_equity to grid_df to get census_df
    aggregate points_count by each grid
    join census_df, porosity_df on grid_id
    dedupe
    output equity_grid_df

    Args:
        target_df (GeoDataframe): grid_df
        source_df (GeoDataframe): blockgroups_df_equity
    Returns:
        GeoDataframe: grid data frame with census data bundled in
    
    """

    source_df = source_df.to_crs(target_df.crs)

    final_fishnet = area_interpolate(source_df, target_df, extensive_variables=var_select)
    return final_fishnet
