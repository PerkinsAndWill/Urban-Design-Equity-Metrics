import pandas as pd
from census import Census
import pygris
from utils import get_fips_code

# Get Variable Code
def get_acs_code(var_select,filepath = '../data/acs_variable_code.csv'):
    acs_code_df = pd.read_csv(filepath)
    acs_dict = {}
    for i in range(len(acs_code_df)):
        acs_dict[acs_code_df.loc[i,'Variable Name']] = acs_code_df.loc[i,'Variable Code']

    code_list = ['NAME']
    for f in var_select:
        code_list.append(acs_dict[f])
    return tuple(code_list), acs_dict


# read in census api key
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

def get_county_census(lat,lng,var_select):
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
    code_list,acs_dict = get_acs_code(var_select,filepath = '../data/acs_variable_code.csv')

    # read in census api
    api_file = 'census_api_key.txt'
    api_key = get_file_contents(api_file)
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
    acs_df = acs_df.rename(columns=inv_acs_dict, inplace=True)
    county_tiger = pygris.block_groups(state = state_name, county = county_name, cache = True, year = 2019)

    acs_gdf = acs_df.merge(county_tiger, on='GEOID', how='inner')
    acs_gdf = acs_gdf.set_geometry('geometry')

    return acs_gdf



