# UD-Equity-Metrics
PW Neighborhood Equity Metrics Dashboard

## Instructions
* clone repo locally: 
    ````
    git clone https://github.com/PerkinsAndWill/Urban-Design-Equity-Metrics.git
    ````
* navigate to folder,  create python environment, and activate it:
    ```
    cd Urban-Design-Equity_Metrics
    python3 -m venv ud_env
    source ud_env/bin/activate
    ```
* install python packages:
    ```
    pip install -r requirements.txt
    ```
* run streamlit app:
    ```
    streamlit run app/myapp.py
    ```

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
