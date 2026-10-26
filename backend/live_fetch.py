
"""
live_fetch.py

Retrieves current weather and air pollution data from
OpenWeatherMap for selected locations in Sri Lanka.

The module uses the OpenWeatherMap API and the
OPENWEATHER_API_KEY environment variable configured for
the application.

The retrieved data is used as input for air quality
prediction and monitoring.
"""


import os
import math
import requests

# Sri Lanka's two official CEA air quality monitoring stations.
STATIONS = {
    "colombo": {"label": "Colombo", "lat": 6.9271, "lon": 79.8612},
    "kandy":   {"label": "Kandy",   "lat": 7.2906, "lon": 80.6337},
}

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"


def _compute_dew_point(temp_c, humidity_pct):
    a, b = 17.27, 237.7
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(humidity_pct / 100.0)
    return round((b * alpha) / (a - alpha), 1)


def _degrees_to_compass(deg):
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(deg / 22.5) % 16
    return directions[idx]


def get_live_air_features(station="colombo"):
    coords = STATIONS.get(station, STATIONS["colombo"])
    lat, lon = coords["lat"], coords["lon"]
    api_key = os.getenv("OPENWEATHER_API_KEY")

    weather_resp = requests.get(WEATHER_URL, params={
        "lat": lat, "lon": lon, "appid": api_key, "units": "metric"
    }, timeout=10)
    weather_resp.raise_for_status()
    w = weather_resp.json()

    pollution_resp = requests.get(POLLUTION_URL, params={
        "lat": lat, "lon": lon, "appid": api_key
    }, timeout=10)
    pollution_resp.raise_for_status()
    p = pollution_resp.json()["list"][0]["components"]

    temp = w["main"]["temp"]
    humidity = w["main"]["humidity"]

    return {
        "SO2": p["so2"],
        "NO2": p["no2"],
        "CO": p["co"],
        "O3": p["o3"],
        "TEMP": temp,
        "PRES": w["main"]["pressure"],
        "DEWP": _compute_dew_point(temp, humidity),
        "RAIN": w.get("rain", {}).get("1h", 0),
        "wd": _degrees_to_compass(w["wind"]["deg"]),
        "WSPM": w["wind"]["speed"],
    }
