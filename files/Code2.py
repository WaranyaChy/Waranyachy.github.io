import requests
import geopandas as gpd
import pandas as pd
import folium
import xml.etree.ElementTree as ET
import branca.colormap as cm
import webbrowser
import os
from shapely.geometry import box  # Required for creating the mask

# --- 1. FETCH & PARSE DATA ---
def get_weather_data_extended():
    url = "https://data.tmd.go.th/api/WeatherForecast7Days/v2/?uid=api&ukey=api12345"
    
    try:
        print("Fetching XML data...")
        response = requests.get(url, timeout=15)
        root = ET.fromstring(response.content)
        records = []
        
        for province in root.findall('./Provinces/Province'):
            name_node = province.find('ProvinceNameEnglish')
            name_en = name_node.text if name_node is not None else None
            forecast = province.find('SevenDaysForecast')
            
            if name_en and forecast is not None:
                def get_val(tag):
                    node = forecast.find(tag)
                    return node.text if node is not None else "N/A"

                records.append({
                    'province_en': name_en,
                    'date': get_val('ForecastDate'),
                    'max_temp': float(get_val('MaximumTemperature') or 0),
                    'min_temp': get_val('MinimumTemperature'),
                    'wind_speed': get_val('WindSpeed'),
                    'desc': get_val('DescriptionEnglish')
                })
        
        df = pd.DataFrame(records)
        if not df.empty:
            df['province_en'] = df['province_en'].replace({
                'Bangkok': 'Bangkok Metropolis',
                'Nakhon Ratchasima': 'Nakhon Ratchasima'
            })
        return df
    except Exception as e:
        print(f"Parsing Error: {e}")
        return pd.DataFrame()

# --- 2. CREATE MASKED MAP ---
def create_interactive_map(weather_df):
    map_url = "https://raw.githubusercontent.com/cvibhagool/thailand-map/master/thailand-provinces.geojson"
    output_file = "thailand_weather_cropped.html"
    
    if weather_df.empty:
        print("No data to plot.")
        return

    try:
        print("Downloading map geometry...")
        gdf = gpd.read_file(map_url)
        merged = gdf.merge(weather_df, left_on='NAME_1', right_on='province_en', how='left')
        merged['max_temp'] = merged['max_temp'].fillna(0)
        
        # Dynamic Scale
        valid_temps = merged[merged['max_temp'] > 0]['max_temp']
        if not valid_temps.empty:
            min_scale = valid_temps.min()
            max_scale = valid_temps.max()
        else:
            min_scale, max_scale = 20, 40

        print(f"Color Scale: {min_scale}°C - {max_scale}°C")

        # --- SETUP MAP ---
        esri_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}'
        esri_attr = 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'

        m = folium.Map(
            location=[13.0, 101.0], 
            zoom_start=6, 
            tiles=esri_url, 
            attr=esri_attr
        )
        
        # --- NEW STEP: CREATE THE "INVERSE MASK" ---
        print("Generating mask to crop base map...")
        # 1. Merge all provinces into one single Thailand polygon
        thailand_outline = gdf.dissolve().geometry[0]
        
        # 2. Create a box representing the whole world (or a large area)
        world_box = box(-180, -90, 180, 90)
        
        # 3. Subtract Thailand from the World (World - Thailand = Mask)
        mask_geom = world_box.difference(thailand_outline)
        
        # 4. Add this mask as a WHITE layer on top of the base map
        folium.GeoJson(
            mask_geom,
            style_function=lambda x: {
                'fillColor': 'white', 
                'color': 'white',      # Border color of the mask
                'weight': 0,           # No border lines
                'fillOpacity': 1.0     # 100% Opaque (solid white)
            },
            name="Mask"
        ).add_to(m)

        # --- END MASK STEP ---

        # Colormap
        colormap = cm.LinearColormap(
            colors=['#4575b4', '#91bfdb', '#fee090', '#fc8d59', '#d73027'],
            vmin=min_scale,
            vmax=max_scale,
            caption='Max Temperature (°C)'
        )
        colormap.add_to(m)

        # Style for Data Layer
        def style_fn(feature):
            temp = feature['properties'].get('max_temp', 0)
            return {
                'fillColor': colormap(temp) if temp > 0 else '#d9d9d9',
                'color': 'black',
                'weight': 0.5,
                'fillOpacity': 0.6 # Transparency so Hillshade shows through
            }

        # Add Data Layer (This goes ON TOP of the mask's hole)
        folium.GeoJson(
            merged,
            name='Weather Data',
            style_function=style_fn,
            tooltip=folium.GeoJsonTooltip(fields=['NAME_1'], aliases=['Province:']),
            popup=folium.GeoJsonPopup(
                fields=['NAME_1', 'date', 'max_temp', 'min_temp', 'wind_speed', 'desc'],
                aliases=['Province', 'Date', 'Max Temp', 'Min Temp', 'Wind', 'Weather'],
                localize=True
            )
        ).add_to(m)

        m.save(output_file)
        print(f"Success! Map saved as '{output_file}'")
        
        open_in_browser(output_file)

    except Exception as e:
        print(f"Mapping Error: {e}")

def open_in_browser(filename):
    try:
        file_path = os.path.abspath(filename)
        url = f'file://{file_path}'
        print(f"Opening {url} in browser...")
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")

if __name__ == "__main__":
    df = get_weather_data_extended()
    create_interactive_map(df)




