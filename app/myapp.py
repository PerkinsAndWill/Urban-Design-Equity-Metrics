import streamlit as st
import folium
import branca
import os
os.environ['USE_PYGEOS'] = '0'

from utils import get_point_density, create_grid, get_all_places, get_fips_code, \
            enrich_grid, get_network, get_porosity, locations_to_geojson, \
            get_county_census, make_iso_poly, acs_dict
from streamlit_folium import folium_static, st_folium
import json
import time
import osmnx as ox


if 'center' not in st.session_state:
    st.session_state['center'] = 37.78737, -122.39505

# lat, lng = st.session_state['center']


## set up title, header
st.title("Urban Design Equity Metrics Dashboard")


########### INPUT SECTION ##############
##### Sidebar

# user input lat, lng
with st.sidebar:
    st.markdown("#### Input Latitude and Longitude of your Interested Neighborhood")
    _lat= st.number_input('Insert Latitude', value=37.78737)
    _lng = st.number_input('Insert Longitude', value=-122.39505)
    if st.button('Recompute for user coordinates'):
        # lat, lng = 
        st.session_state['center'] = _lat, _lng
    lat, lng = st.session_state['center']
    state_fips,state_name, county_fips, county_name = get_fips_code(lat, lng)
    st.write('The current coordinates is ', state_name, ', ', county_name)

    # select viz
    option = st.selectbox(label="Select layer to visualize:", options=[
        *acs_dict.keys(), "Porosity", "Retail", "Transit"
    ])

########### CONSTRUCT STUDY AREA ##############

# lat, lng to create grid overlay of given radius around lat,lng
grid_df = create_grid(lat, lng, radius=800, size=200)
print("grid ok")

########### GET METRICS DATA #################

# GET CENSUS DATA
time0 = time.time()
df_county_census = get_county_census(lat,lng)
print(f"\ncall to census completed in {time.time()-time0:.2f} seconds\n")

time0 = time.time()
# GET RETAILS AND TRANSIT STOPS
retail_locations = get_all_places(location=f"{lat}, {lng}", radius=800, category="retail")
print(f"\ncall to retail (Google API) completed in {time.time()-time0:.2f} seconds\n")
retail_geojson = locations_to_geojson(retail_locations)
retail_density = get_point_density(grid_df, retail_locations, normalize=False)

transit_locations = get_all_places(location=f"{lat}, {lng}", radius=800, category="transit")
print(f"\ncall to transit (Google API) completed in {time.time()-time0:.2f} seconds\n")
transit_geojson = locations_to_geojson(transit_locations)
transit_density = get_point_density(grid_df, transit_locations, normalize=False)

# POROSITY DATA
time0 = time.time()
network_graph, network = get_network(lat, lng, distance=800, network_type="walk")
print(f"\ncall to network (OSM) completed in {time.time()-time0:.2f} seconds\n")
iso_poly, iso_graph, iso_points = make_iso_poly(network_graph, lat, lng)
iso_net = ox.graph_to_gdfs(iso_graph, nodes=False, edges=True).reset_index()

network = network.to_crs(grid_df.crs)
network = network.overlay(grid_df, how="intersection")
porosity = get_porosity(grid_df, network, lat, lng)
print(f"\ntotal network processing completed in {time.time()-time0:.2f} seconds\n")


########### FEATURE ENGINEERING #################
#PCT_MINORITY = POPULATION_NON-WHITE/TOTAL_POPULATION

########### ENRICH GRID #################
final_grid = enrich_grid(grid_df, df_county_census, porosity, retail_density, transit_density)

########### DISPLAY MAP ##################
# Load the GeoJSON file
geojson_data = json.loads(final_grid.to_json()) 

# st.write(geojson_data['features'])

# Create a Folium map centered on (lat, lng)
m = folium.Map(location=[lat, lng], zoom_start=15, tiles='CartoDB positron')

# Add the GeoJSON data to the map as a GeoJSON layer
max_opt = max([feature['properties'][option] for feature in geojson_data['features']])
min_opt = min([feature['properties'][option] for feature in geojson_data['features']])

for map_data, metric in zip([retail_geojson, transit_geojson], ["Retail", "Transit"]):
    if option == metric:
        folium.GeoJson(map_data, marker=folium.CircleMarker(
            radius = 2, 
            weight = 0, #outline weight
            fill_color = 'red', 
            fill_opacity = 0.2
        )).add_to(m)

if option == "Porosity":
    folium.GeoJson(network, style_function=lambda feature: {
        'color': '#222222',
        'weight': 0.5,
        'opacity': 0.1
    }).add_to(m)

    folium.GeoJson(iso_net, style_function=lambda feature: {
        'color': '#222222',
        'weight': 0.8,
        'opacity': 0.2
    }).add_to(m)

    folium.GeoJson(iso_poly, style_function=lambda feature: {
        'color': '#222222',
        'weight': 2.0,
        'opacity': 0.3,
        'fillColor': '#444444',
        'fillOpacity': 0.15
    }).add_to(m)


folium.GeoJson(geojson_data, style_function=lambda feature: {
    'color': '#222222',
    'weight': '0.5',
    'opacity': 0.2,
    'fillColor': 'red',
    'fillOpacity': 0.7 * feature['properties'][option]/max_opt
    }
).add_to(m)

colormap = branca.colormap.LinearColormap(colors=[(255, 0, 0, 0), (255, 0, 0, int(255*0.7))], 
            vmin=min_opt, vmax=max_opt)  # , tick_labels=[0, 0.2, 0.4, 0.6, 0.8]
colormap.caption = option
colormap.add_to(m)

# Display the map in Streamlit
# folium_static(m)
st_f_data = st_folium(m, height=600, width=700)

# write current coords to state
def update_map_center():
    st.session_state.center = st_f_data['center']['lat'], st_f_data['center']['lng']

with st.sidebar:
    if 'center' in st_f_data:
        st.markdown(f"\n#### The map is currently centered at: \n{st_f_data['center']['lat']:.2f}, " +
                f"{st_f_data['center']['lng']:.2f}")
    st.button("Recompute for current position", key="update_center",
        on_click=update_map_center)

########### DOWNLOAD DATA ##############
with st.expander("See Dataframe"):
    st.write('PLACESHOLDER TO SHOW DATAFRAME')

st.download_button(
    label="Download data as GeoJSON",
    data=final_grid.to_json(),
    file_name='grid_df.geojson'
)
