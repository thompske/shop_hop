import folium
import numpy as np
import pandas as pd
import polyline
import requests


def set_lat_lng(
    index, address, df, maps_key=None, api="gm", lat_col_name="lat", lng_col_name="lng"
):

    lat, lng = get_lat_lng(address, maps_key, api)
    if lat:
        df.loc[index, lat_col_name] = lat
    if lng:
        df.loc[index, lng_col_name] = lng

    return df


def get_lat_lng(address, maps_key, api="gm"):

    if api == "osm":
        params = {
            "q": address,
            "format": "json",
        }
        geo_code = requests.get("https://nominatim.openstreetmap.org/search", params)

        response = geo_code.json()
        if len(response) > 0:
            lat = response[0]["lat"]
            lng = response[0]["lon"]
        else:
            print("No results")
            lat = np.nan
            lng = np.nan

    elif api == "gm":
        params = {"address": address, "key": maps_key}
        geo_code = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json", params
        )

        response = geo_code.json()
        if len(response["results"]) > 0:
            lat = response["results"][0]["geometry"]["location"]["lat"]
            lng = response["results"][0]["geometry"]["location"]["lng"]
        else:
            print("No results")
            lat = np.nan
            lng = np.nan
    else:
        print(
            "API name not recognized -- Use either 'gm' for google maps or 'osm' for open street maps."
        )
        return

    return lat, lng


def format_coords(shops, home_lat, home_lng, region=None, region_col="region"):
    coord_str = f"{home_lng},{home_lat}"

    if region is not None:
        s = shops[shops[region_col] == region]
    else:
        s = shops

    for i, r in s.iterrows():
        coord_str += f";{r['lng']},{r['lat']}"

    return coord_str


def map_trip_region(
    shops,
    region,
    home_lat,
    home_lng,
    color="#0fa6d9",
    region_col="region",
    existing_map=None,
):

    region_coords = format_coords(shops, home_lat, home_lng, region, region_col)

    r = requests.get(
        f"http://router.project-osrm.org/trip/v1/driving/{region_coords}?roundtrip=true&source=first"
    )
    res = r.json()

    geometry = res["trips"][0]["geometry"]

    region_df = shops[shops[region_col] == region].copy()

    if existing_map:
        m = existing_map

    else:
        m = folium.Map(location=region_df[["lat", "lng"]].mean())

        sw = region_df[["lat", "lng"]].min().values.tolist()
        ne = region_df[["lat", "lng"]].max().values.tolist()
        m.fit_bounds([sw, ne])

    # Get polyline from OSRM & add to map
    pl = polyline.decode(geometry)

    region_name = str(region).title()

    folium.PolyLine(
        locations=pl, tooltip=f"{region_name} Region", color=color, opacity=0.75
    ).add_to(m)

    # Create location markers for stops
    m = add_loc_markers(region_df, color, m)

    # Create location marker for "home"
    folium.Marker(
        location=[home_lat, home_lng],
        icon=folium.Icon(color="blue", icon="glyphicon-home"),
    ).add_to(m)

    distance = res["trips"][0]["distance"] / 1609.34
    duration = res["trips"][0]["duration"] / 60 / 60

    return m, distance, duration


def map_all_regions(shops, home_lat, home_lng, region_col="region", existing_map=None):

    if existing_map:
        m = existing_map
    else:
        m = folium.Map(location=shops[["lat", "lng"]].mean())
        sw = shops[["lat", "lng"]].min().values.tolist()
        ne = shops[["lat", "lng"]].max().values.tolist()
        m.fit_bounds([sw, ne])

    colors = [
        "#f77189",
        "#d58c32",
        "#a4a031",
        "#50b131",
        "#34ae91",
        "#37abb5",
        "#3ba3ec",
        "#bb83f4",
        "#f564d4",
    ]

    distances = {}
    durations = {}
    i = 0
    for region in shops[region_col].unique():
        new_map, distance, duration = map_trip_region(
            shops,
            region,
            home_lat,
            home_lng,
            color=colors[i],
            existing_map=m,
            region_col=region_col,
        )
        distances[region] = distance
        durations[region] = duration
        m = new_map
        i += 1

    return m, distances, durations


def map_all_shops(shops, home_lat, home_lng, region_col="region"):

    m = folium.Map(location=shops[["lat", "lng"]].mean())

    sw = shops[["lat", "lng"]].min().values.tolist()
    ne = shops[["lat", "lng"]].max().values.tolist()
    m.fit_bounds([sw, ne])

    color = "#37abb5"
    colors = [
        "#f77189",
        "#d58c32",
        "#a4a031",
        "#50b131",
        "#34ae91",
        "#37abb5",
        "#3ba3ec",
        "#bb83f4",
        "#f564d4",
    ]

    coords = format_coords(shops, home_lat, home_lng)

    r = requests.get(
        f"http://router.project-osrm.org/trip/v1/driving/{coords}?roundtrip=true&source=first"
    )
    res = r.json()

    geometry = res["trips"][0]["geometry"]

    # Get polyline from OSRM & add to map
    pl = polyline.decode(geometry)

    folium.PolyLine(
        locations=pl, tooltip=f"Minnesota Quilts Shop Hop", color=color, opacity=0.75
    ).add_to(m)

    # Create location markers for stops
    i = 0
    for region in shops[region_col].unique():
        region_df = shops[shops[region_col] == region].copy()
        region_name = str(region).title()
        m = add_loc_markers(region_df, colors[i], m)
        i += 1

    # Create location marker for "home"
    folium.Marker(
        location=[home_lat, home_lng],
        icon=folium.Icon(color="blue", icon="glyphicon-home"),
    ).add_to(m)

    distance = res["trips"][0]["distance"] / 1609.34
    duration = res["trips"][0]["duration"] / 60 / 60

    return m, distance, duration


def add_loc_markers(df, color, m):
    for _, row in df.iterrows():
        lat, lng = row["lat"], row["lng"]
        popup = folium.Popup(f"({lat:.4f}, {lng:.4f})", max_width=9999)
        folium.CircleMarker(
            location=(lat, lng),
            popup=popup,
            tooltip=row["shop name"],
            radius=6,
            fill=True,
            fill_opacity=0.25,
            color=color,
        ).add_to(m)
    return m


def add_region_markers(
    shops, region, color="#0fa6d9", region_col="region", existing_map=None
):

    region_df = shops[shops[region_col] == region].copy()

    if existing_map:
        m = existing_map

    else:
        m = folium.Map(location=region_df[["lat", "lng"]].mean())

        sw = region_df[["lat", "lng"]].min().values.tolist()
        ne = region_df[["lat", "lng"]].max().values.tolist()
        m.fit_bounds([sw, ne])

    # Create location markers for stops
    m = add_loc_markers(region_df, color, m)

    return m


def add_all_region_markers(shops, region_col="region", existing_map=None):

    if existing_map:
        m = existing_map

    else:
        m = folium.Map(location=region_df[["lat", "lng"]].mean())

        sw = region_df[["lat", "lng"]].min().values.tolist()
        ne = region_df[["lat", "lng"]].max().values.tolist()
        m.fit_bounds([sw, ne])

    colors = [
        "#f77189",
        "#d58c32",
        "#a4a031",
        "#50b131",
        "#34ae91",
        "#37abb5",
        "#3ba3ec",
        "#bb83f4",
        "#f564d4",
    ]
    i = 0
    for region in shops[region_col].unique():
        region_df = shops[shops[region_col] == region].copy()
        region_name = str(region).title()
        m = add_loc_markers(region_df, colors[i], m)
        i += 1

    return m
