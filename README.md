# UD-Equity-Metrics
PW Neighborhood Equity Metrics Dashboard
## Overview
## Team
## Metrics
## Work Flow
1. Input lat, lng or Address
2. Construct Study Area
    -  2.1 draw a half-mile circle
    -  2.2 fill the circle with 200 by 200 grid

3. Get Census data for this area
    - 3.1 Census geocoder API to get geometries
        - get FIPS code
    
        reference: https://www.census.gov/programs-surveys/geography/technical-documentation/complete-technical-documentation/census-geocoder.html
    - 3.2 Census API to get tables
         - get FIPS code 
         - get table names
4. Feature engineering
5. Area Interpolation
6. Visualize on web map
      - 6.1 streamlit input box
      - 6.2 streamlit map
      - 6.4 streamlit download geojson
