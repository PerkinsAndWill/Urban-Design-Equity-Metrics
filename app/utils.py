from shapely import geometry
import geopandas as gpd
 
def create_grid(lat, lng, radius, grid_size):
    # point from lat, lng
    points_gdf = gpd.points_from_xy(lat, lng)

    # boundary file
    boundary = points_gdf.buffer(radius)

    # Get the extent of the shapefile
    # Get minX, minY, maxX, maxY
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
    grid_gdf = fishnet.sjoin(boundary, how = 'inner')
    return grid_gdf