import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
from shapely import geometry
# import folium
import pandas as pd
 
def create_grid(lat=37.78, lng=-122.39, radius=800, size=200):
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
    boundary = boundary.drop([0],axis = 1)

    grid_gdf = fishnet.sjoin(boundary, how = 'inner')
    grid_gdf = grid_gdf.drop(['index_right'],axis = 1)
    grid_gdf = grid_gdf.to_crs('EPSG:4326')
    
    return grid_gdf