import libpysal
from tobler.util import h3fy
from tobler.area_weighted import area_interpolate

# right = 
# left = grid_df

# right = right.to_crs(left.crs)

# final_fishnet = area_interpolate(source_df = right, target_df = left, intensive_variables = ['resi_den', 'FAR'], extensive_variables=['units','jobs'])