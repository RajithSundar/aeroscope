"""Paths and study-wide constants."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "figures"
WEB_DATA_DIR = ROOT / "web" / "data"

CITIES_CSV = CONFIG_DIR / "ncap_cities.csv"
INTERVENTIONS_JSON = CONFIG_DIR / "interventions.json"
GRID_CELLS_CSV = RAW_DIR / "grid_cells.csv"
CAMS_DIR = RAW_DIR / "cams"
WEATHER_DIR = RAW_DIR / "weather"
FIRMS_DIR = RAW_DIR / "firms"

# Study period: three full calendar years so regimes can be checked year against year.
YEARS = (2023, 2024, 2025)
START_DATE = f"{YEARS[0]}-01-01"
END_DATE = f"{YEARS[-1]}-12-31"
TIMEZONE = "Asia/Kolkata"

DATA_SOURCE_LABEL = (
    "Copernicus Atmosphere Monitoring Service (CAMS) global atmospheric composition "
    "reanalysis/analysis via Open-Meteo (~0.4° / ~40 km model grid, assimilates satellite AOD)"
)

# India + upwind neighbourhood (Pakistan Punjab, Nepal, Bangladesh) for fire detections.
FIRE_BBOX = (66.0, 6.0, 98.0, 37.5)  # west, south, east, north

# CPCB 24-hour National Ambient Air Quality Standard for PM2.5 (ug/m3).
NAAQS_PM25_24H = 60.0
NAAQS_PM10_24H = 100.0


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader (KEY=VALUE lines) so no extra dependency is needed."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
