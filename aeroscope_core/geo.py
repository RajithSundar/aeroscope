"""Great-circle distance, bearings and upwind-sector tests (vectorised)."""

import numpy as np

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2):
    """Initial bearing from point 1 to point 2, degrees clockwise from north."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    x = np.sin(lon2 - lon1) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(lon2 - lon1)
    return (np.degrees(np.arctan2(x, y)) + 360) % 360


def angular_difference(a, b):
    return np.abs((np.asarray(a) - np.asarray(b) + 180) % 360 - 180)


def is_upwind(city_lat, city_lon, src_lat, src_lon, wind_from_deg, half_width_deg=45.0):
    """True where the source lies in the sector the wind is blowing FROM, as seen from the city."""
    brg = bearing_deg(city_lat, city_lon, src_lat, src_lon)
    return angular_difference(brg, wind_from_deg) <= half_width_deg
