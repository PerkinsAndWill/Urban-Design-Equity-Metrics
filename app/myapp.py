import streamlit as st
import folium
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import pandas as pd

import pygris
from utils import get_point_density, create_grid, get_all_retail_points, get_fips_code, \
            enrich_grid, get_network, get_porosity, locations_to_geojson
from get_census import get_county_census
from streamlit_folium import folium_static
import json

## set up title, header
st.title("Urban Design Equity Metrics Dashboard")


########### INPUT SECTION ##############
##### Sidebar

# user input lat, lng
with st.sidebar:
    st.markdown("#### Input Latitude and Longitude of your Interested Neighborhood")
    lat= st.number_input('Insert Latitude', value=37.78737)
    lng = st.number_input('Insert Longitude', value=-122.39505)
    state_fips,state_name, county_fips, county_name = get_fips_code(lat, lng)
    st.write('The current coordinates is ', state_name, ', ', county_name)

    options = st.multiselect(
    'Select Metrics',
    ['Total Population', 'Total Jobs (All Workers)', 'Total Housing Units', 
    'Total Low Income Population', 'Black Population', 'Hispanic or Latino Population', 
    'Pct_Rent_Burdened', 'Porosity', 'Retail Spots', 'Transit Stops'],
    ['Total Population', 'Total Housing Units'])

    st.write('You selected:', options)
    var_select = options

    st.write(type(var_select))



########### CONSTRUCT STUDY AREA ##############

# lat, lng to create grid overlay of given radius around lat,lng
grid_df = create_grid(lat, lng, radius=800, size=200)
print("grid ok")
# st.write(grid_df.head())

########### GET METRICS DATA #################

# GET CENSUS DATA
df_county_census = get_county_census(lat,lng, var_select)
print("sensus ok")

# GET RETAILS AND TRANSIT STOPS
retail_locations = get_all_retail_points(location=f"{lat}, {lng}", radius=800)
locations_geojson = locations_to_geojson(retail_locations)
print("retail ok")
density = get_point_density(grid_df, retail_locations, normalize=True)

# POROSITY DATA
network = get_network(lat, lng, distance=800, network_type="walk")
network = network.to_crs(grid_df.crs)
network = network.overlay(grid_df, how="intersection")
porosity = get_porosity(grid_df, network)

########### FEATURE ENGINEERING #################
#PCT_MINORITY = POPULATION_NON-WHITE/TOTAL_POPULATION

########### ENRICH GRID #################
final_grid = enrich_grid(grid_df, df_county_census, porosity, density, var_select)

########### DISPLAY MAP ##################
# Load the GeoJSON file
geojson_data = json.loads(final_grid.to_json()) 

# st.write(geojson_data['features'])

# Create a Folium map centered on the first polygon in the GeoJSON data  # NOTE: polygons are centered on map now
coords = geojson_data['features'][0]['geometry']['coordinates'][0][:-1]
start_lat = sum(p[1] for p in coords) / len(coords)
start_lon = sum(p[0] for p in coords) / len(coords)
coords = geojson_data['features'][-1]['geometry']['coordinates'][0][:-1]
end_lat = sum(p[1] for p in coords) / len(coords)
end_lon = sum(p[0] for p in coords) / len(coords)
m = folium.Map(location=[0.5*(start_lat + end_lat), 0.5*(start_lon+end_lon)], zoom_start=14, tiles='CartoDB positron')

# Add the GeoJSON data to the map as a GeoJSON layer
options=['density']
max_opt = max([feature['properties'][options[0]] for feature in geojson_data['features']])

folium.GeoJson(geojson_data, style_function=lambda feature:{
    'color': 'black',
    'weight': '0.5',
    'fillColor': 'red', # NEED TO BE A VARIABLE INPUT BY THE USER
    'fillOpacity': feature['properties'][options[0]]/max_opt
    }
).add_to(m)

folium.GeoJson(network, style_function=lambda feature: {
    'color': 'blue',
    'weight': '0.5',
}).add_to(m)

folium.GeoJson(locations_geojson, marker=folium.CircleMarker(
    radius = 5, # Radius in metres
    weight = 0, #outline weight
    fill_color = 'green', 
    fill_opacity = 1
)).add_to(m)

# Display the map in Streamlit
folium_static(m)

########### DOWNLOAD DATA ##############
with st.expander("See Dataframe"):
    st.write('PLACESHOLDER TO SHOW DATAFRAME')

@st.cache_data
def convert_df(_df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return _df.to_json()

download_json = convert_df(grid_df)

st.download_button(
    label="Download data as GeoJSON",
    data=download_json,
    file_name='grid_df.geojson'
)
