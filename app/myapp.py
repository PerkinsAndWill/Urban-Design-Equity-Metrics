

import streamlit as st
import folium
import geopandas as gpd
import pandas as pd
from utils import create_grid
from streamlit_folium import folium_static
import json

## set up title, header
st.title("Urban Desgin Equity Metrics Dashboard")



########### INPUT SECTION ##############
##### Sidebar

# user input lat, lng
with st.sidebar:
    st.markdown("#### Input Latitude and Longitude of your Interested Neighborhood")
    lat= st.number_input('Insert Latitude', value=37.78737)
    lng = st.number_input('Insert Longitude', value=-122.39505)

    st.write('The current coordinates is ', lat, lng)

    options = st.multiselect(
    'Select Metrics',
    ['Residents', 'Jobs', 'Housing Units', 'Pct_Black or Hispanic Residents', 'Pct_Rent Burdened', 'Pct_Low-Wage Workers', 'Median House Value', 'Porosity', 'Retail Spots', 'Transit Stops'],
    ['Retail Spots', 'Transit Stops'])

    st.write('You selected:', options)



########### CONSTRUCT STUDY AREA ##############

# lat, lng to create grid overlay of given radius around lat,lng
grid_df = create_grid(lat, lng, radius=800, size=200)
# st.write(grid_df.head())

########### GET METRICS DATA #################
# READ SELECTED VARIABLES
# acs_code_df = pd.read_csv('../data/acs_variable_code.csv')


# GET CENSUS DATA


# GET RETAILS AND TRANSIT STOPS


########### FEATURE ENGINEERING #################


########### DISPLAY MAP ##################
# Load the GeoJSON file
geojson_data = json.loads(grid_df.to_json())
# st.write(geojson_data['features'])

# Create a Folium map centered on the first polygon in the GeoJSON data
coords = geojson_data['features'][0]['geometry']['coordinates'][0][:-1]
center_lat = sum(p[1] for p in coords) / len(coords)
center_lon = sum(p[0] for p in coords) / len(coords)
m = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles='CartoDB positron')

# Add the GeoJSON data to the map as a GeoJSON layer
folium.GeoJson(geojson_data, style_function=lambda feature:{
    'color': 'black',
    'weight': '1',
    'fillColor': 'red',
    'fillOpacity': 0.1
    }
).add_to(m)

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