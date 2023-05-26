import libpysal
from tobler.util import h3fy
from tobler.area_weighted import area_interpolate

#### enrich with census data ###################

# right = 
# left = grid_df

# right = right.to_crs(left.crs)

# final_fishnet = area_interpolate(source_df = right, target_df = left, extensive_variables=['units','jobs'])


#### enrich with prosity data ###################
# sum total length of walkable streets in each grid

#### enrich with retail data ###################
# count number of retail points in each grid


#### enrich with transit data ###################
# count number of transit points in each grid
