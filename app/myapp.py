import streamlit as st
import folium
import branca
import os
os.environ['USE_PYGEOS'] = '0'

from utils import get_point_density, create_grid, get_all_retail_points, get_fips_code, \
            enrich_grid, get_network, get_porosity, locations_to_geojson, \
            get_county_census, acs_dict
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

    # select viz
    option = st.selectbox(label="Select layer to visualize:", options=[
        *acs_dict.keys(), "Porosity", "Retail"
    ])

########### CONSTRUCT STUDY AREA ##############

# lat, lng to create grid overlay of given radius around lat,lng
grid_df = create_grid(lat, lng, radius=800, size=200)
print("grid ok")

########### GET METRICS DATA #################

# GET CENSUS DATA
df_county_census = get_county_census(lat,lng)
print("sensus ok")

# GET RETAILS AND TRANSIT STOPS
retail_locations = get_all_retail_points(location=f"{lat}, {lng}", radius=800)
# with open('../cached_retail_locations.json', 'r') as f:
#     retail_locations = json.load(f)
locations_geojson = locations_to_geojson(retail_locations)
print("retail ok")
retail_density = get_point_density(grid_df, retail_locations, normalize=False)

# POROSITY DATA
network = get_network(lat, lng, distance=800, network_type="walk")
network = network.to_crs(grid_df.crs)
network = network.overlay(grid_df, how="intersection")
porosity = get_porosity(grid_df, network, lat, lng)

########### FEATURE ENGINEERING #################
#PCT_MINORITY = POPULATION_NON-WHITE/TOTAL_POPULATION

########### ENRICH GRID #################
final_grid = enrich_grid(grid_df, df_county_census, porosity, retail_density)

########### DISPLAY MAP ##################
# Load the GeoJSON file
geojson_data = json.loads(final_grid.to_json()) 

# st.write(geojson_data['features'])

# Create a Folium map centered on (lat, lng)
m = folium.Map(location=[lat, lng], zoom_start=15, tiles='CartoDB positron')

# Add the GeoJSON data to the map as a GeoJSON layer
max_opt = max([feature['properties'][option] for feature in geojson_data['features']])
min_opt = min([feature['properties'][option] for feature in geojson_data['features']])

if option == "Porosity":
    folium.GeoJson(network, style_function=lambda feature: {
        'color': 'blue',
        'weight': '0.5',
        'opacity': 0.2
    }).add_to(m)

if option == "Retail":
    folium.GeoJson(locations_geojson, marker=folium.CircleMarker(
        radius = 2, 
        weight = 0, #outline weight
        fill_color = 'red', 
        fill_opacity = 0.2
    )).add_to(m)

folium.GeoJson(geojson_data, style_function=lambda feature:{
    'color': '#222222',
    'weight': '0.5',
    'opacity': 0.2,
    'fillColor': 'red',
    'fillOpacity': 0.8 * feature['properties'][option]/max_opt
    }
).add_to(m)

colormap = branca.colormap.LinearColormap(colors=[(255, 0, 0, 0), (255, 0, 0, int(255*0.8))], 
            vmin=min_opt, vmax=max_opt)  # , tick_labels=[0, 0.2, 0.4, 0.6, 0.8]
colormap.caption = option
colormap.add_to(m)

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
