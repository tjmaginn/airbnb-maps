# -*- coding: utf-8 -*-
"""
Created on Mon Jan  5 15:56:43 2026

@author: teddy
"""

import geopandas as gpd
import pandas as pd
import folium
import branca.colormap as cm

# --------------------------------------------------
# Load data
# --------------------------------------------------

us_tracts = gpd.read_file(
    r"C:\Users\tjmaginn\Dropbox\My Research\Substack\airbnb\data\shapefiles\us tract\US_tract_2023.shp"
).to_crs(epsg=4326)

bnb_data = pd.read_csv(
    r"C:\Users\tjmaginn\Dropbox\My Research\Substack\airbnb\data\clean\airbnb_tract_level_mapping.csv"
)

bnb_data["censustract"] = bnb_data["censustract"].astype(str)
bnb_data.loc[bnb_data["city"].isin(["la", "sf"]), "censustract"] = (
    bnb_data.loc[bnb_data["city"].isin(["la", "sf"]), "censustract"]
    .str.zfill(11)
)

supp_tracts = pd.read_csv(
    r"C:\Users\tjmaginn\Dropbox\My Research\Substack\airbnb\data\clean\supplemental_tract.csv"
)

supp_tracts["censustract"] = supp_tracts["censustract"].astype(str).str.zfill(11)

# --------------------------------------------------
# City boundaries
# --------------------------------------------------

la_geom = gpd.read_file(
    r"C:\Users\tjmaginn\Dropbox\My Research\Substack\airbnb\data\shapefiles\la boundaries\City_Boundary.shp"
).to_crs(epsg=4326).unary_union

chi_geom = gpd.read_file(
    r"C:\Users\tjmaginn\Dropbox\My Research\Substack\airbnb\data\shapefiles\chi boundaries\chi_boundary.shp"
).to_crs(epsg=4326).unary_union

nola_geom = gpd.read_file(
    r"C:\Users\tjmaginn\Dropbox\My Research\Substack\airbnb\data\shapefiles\nola boundaries\nola_tracts.shp"
).to_crs(epsg=4326).unary_union

nash_geom = gpd.read_file(
    r"C:\Users\tjmaginn\Dropbox\My Research\Substack\airbnb\data\shapefiles\nash boundaries\nash_areas.shp"
).to_crs(epsg=4326).unary_union

sf_geom = gpd.read_file(
    r"C:\Users\tjmaginn\Dropbox\My Research\Substack\airbnb\data\shapefiles\sf tract\sf_tracts.shp"
).to_crs(epsg=4326).unary_union

nyc_geom = gpd.read_file(
    r"C:\Users\tjmaginn\Dropbox\My Research\Substack\airbnb\data\shapefiles\ny tract\nyct2020.shp"
).to_crs(epsg=4326).unary_union

city_geoms = {
    "la": la_geom,
    "chi": chi_geom,
    "nola": nola_geom,
    "nash": nash_geom,
    "sf": sf_geom,
    "nyc": nyc_geom,
}

city_views = {
    "nyc": [40.7128, -74.0060, 11],
    "la": [34.0522, -118.2437, 10],
    "sf": [37.7749, -122.4194, 12],
    "chi": [41.8781, -87.6298, 11],
    "nola": [29.9511, -90.0715, 12],
    "nash": [36.1627, -86.7816, 11],
}

# --------------------------------------------------
# Create map
# --------------------------------------------------

m = folium.Map(
    location=[40.7128, -74.0060],
    zoom_start=11,
    tiles="cartodbpositron",
)

map_name = m.get_name()

# --------------------------------------------------
# 🔹 HTML DOCUMENT TITLE (GitHub Pages / browser tab)
# --------------------------------------------------

m.get_root().html.add_child(
    folium.Element("""
    <title>Share of housing units used as Airbnbs</title>
    """)
)

# --------------------------------------------------
# Visual title overlay
# --------------------------------------------------

title_html = """
<div style="
    position: fixed;
    top: 12px;
    left: 0;
    width: 100%;
    text-align: center;
    z-index: 9998;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, Helvetica, Arial, sans-serif;
">
    <div style="
        display: inline-block;
        background: white;
        padding: 8px 18px;
        border-radius: 6px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.25);
        font-size: 20px;
        font-weight: 600;
    ">
        Share of housing units used as Airbnbs
    </div>
</div>
"""

m.get_root().html.add_child(folium.Element(title_html))

# --------------------------------------------------
# Force map height (GitHub Pages)
# --------------------------------------------------

m.get_root().header.add_child(
    folium.Element(f"""
    <style>
        html, body {{
            height: 100%;
            margin: 0;
        }}
        #{map_name} {{
            position: absolute;
            top: 80px;
            bottom: 0;
            left: 0;
            right: 0;
        }}
    </style>
    """)
)

# --------------------------------------------------
# Add city layers
# --------------------------------------------------

for city_code, (lat, lon, zoom) in city_views.items():

    city_geom = city_geoms[city_code]

    city_tracts = us_tracts[
        us_tracts.intersects(city_geom)
    ][["GEOID", "geometry"]].copy()

    # geometry simplification (file size)
    city_tracts["geometry"] = city_tracts["geometry"].simplify(
        tolerance=0.0005,
        preserve_topology=True
    )

    city_gdf = city_tracts.merge(
        supp_tracts,
        left_on="GEOID",
        right_on="censustract",
        how="left",
    )

    city_bnb = bnb_data[bnb_data["city"] == city_code][
        ["censustract", "tract_bnb_share"]
    ]

    city_gdf = city_gdf.merge(
        city_bnb,
        on="censustract",
        how="left",
    )

    mask = city_gdf["GEOID"] == "06075980300"
    cols_to_nan = city_gdf.columns.difference(["geometry", "GEOID", "censustract"])
    city_gdf.loc[mask, cols_to_nan] = pd.NA

    city_gdf["tract_bnb_share"] = city_gdf["tract_bnb_share"].fillna(0)
    city_gdf["bnb_capped"] = city_gdf["tract_bnb_share"].clip(upper=0.15)

    city_gdf["bnb_pct"] = (city_gdf["tract_bnb_share"] * 100).round(2).astype(str) + "%"
    city_gdf["nonwhite_pct"] = (city_gdf["nonwhite_share"] * 100).round(2).astype(str) + "%"
    city_gdf["vacancy_pct"] = (city_gdf["vacancy_rate"] * 100).round(2).astype(str) + "%"
    city_gdf["med_hh_inc_fmt"] = "$" + city_gdf["med_hh_inc"].round(0).astype("Int64").astype(str)
    city_gdf["med_rent_fmt"] = "$" + city_gdf["med_rent"].round(0).astype("Int64").astype(str)
    city_gdf["med_hvalue_fmt"] = "$" + city_gdf["med_hvalue"].round(0).astype("Int64").astype(str)

    bins = [0.0001, 0.0025, 0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15]

    color_scale = cm.StepColormap(
        colors=[
            "#fffff0", "#ffffe5", "#fff7bc", "#fee391", "#fec44f",
            "#fe9929", "#ec7014", "#cc4c02", "#7f0000"
        ],
        index=bins,
        vmin=0,
        vmax=0.15,
    )

    def style_function(feature):
        val = feature["properties"]["bnb_capped"]

        if val is None or pd.isna(val):
            return {
                "fillColor": "#bdbdbd",
                "color": "#777777",
                "weight": 0.6,
                "fillOpacity": 0.5,
            }

        if val == 0:
            return {
                "fillColor": "#ffffff",
                "color": "#666666",
                "weight": 0.6,
                "fillOpacity": 0.85,
            }

        return {
            "fillColor": color_scale(val),
            "color": "#444444",
            "weight": 0.7,
            "fillOpacity": 0.75,
        }

    folium.GeoJson(
        city_gdf,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "GEOID",
                "bnb_pct",
                "med_hh_inc_fmt",
                "med_rent_fmt",
                "med_hvalue_fmt",
                "nonwhite_pct",
                "vacancy_pct",
            ],
            aliases=[
                "Tract:",
                "Airbnb Share:",
                "Median HH Income:",
                "Median Rent:",
                "Median Home Value:",
                "Nonwhite Share:",
                "Vacancy Rate:",
            ],
            labels=True,
        ),
    ).add_to(m)

# --------------------------------------------------
# Dropdown
# --------------------------------------------------

dropdown_html = f"""
<div style="
    position: fixed;
    top: 10px;
    left: 50px;
    z-index: 9999;
    background: white;
    padding: 8px 10px;
    border-radius: 4px;
    box-shadow: 0 1px 5px rgba(0,0,0,0.3);
    font-size: 14px;
">
<b>Select city</b><br>
<select onchange="zoomCity(this.value)">
    <option value="nyc" selected>New York City</option>
    <option value="chi">Chicago</option>
    <option value="la">Los Angeles</option>
    <option value="sf">San Francisco</option>
    <option value="nola">New Orleans</option>
    <option value="nash">Nashville</option>
</select>
</div>

<script>
function zoomCity(city) {{
    var views = {{
        nyc: [40.7128, -74.0060, 11],
        la: [34.0522, -118.2437, 10],
        sf: [37.7749, -122.4194, 12],
        chi: [41.8781, -87.6298, 11],
        nola: [29.9511, -90.0715, 12],
        nash: [36.1627, -86.7816, 11]
    }};
    {map_name}.setView(
        [views[city][0], views[city][1]],
        views[city][2]
    );
}}
</script>
"""

m.get_root().html.add_child(folium.Element(dropdown_html))

# --------------------------------------------------
# Save
# --------------------------------------------------

m.save(
    r"C:\Users\tjmaginn\Dropbox\My Research\Substack\airbnb\outputs\maps\index.html"
)
