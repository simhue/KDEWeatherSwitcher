#!/usr/bin/env python3
"""Select a KDE color scheme using daylight and cloud cover."""

import argparse
import configparser
import json
import logging
import os
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request


def load_config(path):
    config = configparser.ConfigParser()
    if not config.read(path):
        raise ValueError(f"Cannot read configuration: {path}")
    settings = config["weather-theme"]
    latitude = settings.getfloat("latitude")
    longitude = settings.getfloat("longitude")
    dark = settings.getfloat("dark_cloud_percent")
    light = settings.getfloat("light_cloud_percent")
    interval = settings.getint("interval_seconds")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Invalid location coordinates")
    if not 0 <= light < dark <= 100 or interval < 60:
        raise ValueError("Require 0 <= light threshold < dark threshold <= 100 and interval >= 60")
    return settings


def fetch_weather(settings):
    query = urllib.parse.urlencode({
        "latitude": settings.getfloat("latitude"),
        "longitude": settings.getfloat("longitude"),
        "current": "cloud_cover",
        "daily": "sunrise,sunset",
        "timezone": "GMT",
        "timeformat": "unixtime",
        "forecast_days": 3,
    })
    with urllib.request.urlopen(
        f"https://api.open-meteo.com/v1/forecast?{query}", timeout=20
    ) as response:
        data = json.load(response)
    cloud = data["current"]["cloud_cover"]
    if not isinstance(cloud, (int, float)) or not 0 <= cloud <= 100:
        raise ValueError("Invalid cloud cover in weather response")
    daily = data["daily"]
    if not daily["time"] or not (
        len(daily["time"]) == len(daily["sunrise"]) == len(daily["sunset"])
    ):
        raise ValueError("Invalid daylight data in weather response")
    for start, sunrise, sunset in zip(daily["time"], daily["sunrise"], daily["sunset"]):
        if not all(isinstance(value, (int, float)) for value in (start, sunrise, sunset)):
            raise ValueError("Missing daylight data for this location")
    return data


def choose_scheme(settings, weather, now, previous):
    daily = weather["daily"]
    if not daily["time"][0] <= now < daily["time"][-1] + 86400:
        raise ValueError("Daylight forecast has expired; keeping the current theme")
    daylight = any(
        sunrise <= now < sunset
        for sunrise, sunset in zip(daily["sunrise"], daily["sunset"])
    )
    if not daylight:
        return settings["dark_scheme"]
    current = weather["current"]
    if not 0 <= now - current["time"] <= 3600:
        return settings["light_scheme"]
    cloud = current["cloud_cover"]
    if cloud >= settings.getfloat("dark_cloud_percent"):
        return settings["dark_scheme"]
    if cloud <= settings.getfloat("light_cloud_percent"):
        return settings["light_scheme"]
    return previous or settings["light_scheme"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    parser.add_argument("--config", type=Path, default=config_home / "auto-weather-theme.ini")
    parser.add_argument("--once", action="store_true", help="Check once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Log decisions without changing KDE")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        settings = load_config(args.config)
    except (ValueError, KeyError, configparser.Error) as error:
        parser.error(str(error))
    weather = None
    previous = None
    while True:
        success = False
        try:
            try:
                weather = fetch_weather(settings)
            except (OSError, ValueError, KeyError, TypeError) as error:
                logging.warning("Weather request failed: %s", error)
                if weather is None:
                    raise ValueError("No forecast available; keeping the current theme")
            scheme = choose_scheme(settings, weather, time.time(), previous)
            if scheme != previous:
                logging.info("Selected color scheme: %s", scheme)
                if not args.dry_run:
                    subprocess.run(["plasma-apply-colorscheme", scheme], check=True, timeout=30)
                previous = scheme
            success = True
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            logging.error("Theme update failed: %s", error)
        if args.once:
            return 0 if success else 1
        time.sleep(settings.getint("interval_seconds"))


if __name__ == "__main__":
    raise SystemExit(main())
