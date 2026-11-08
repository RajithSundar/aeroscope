"""Loading the NCAP city list and its CAMS grid-cell mapping."""

import pandas as pd

from .config import CITIES_CSV, GRID_CELLS_CSV


def load_cities() -> pd.DataFrame:
    return pd.read_csv(CITIES_CSV, comment="#")


def load_city_cells() -> pd.DataFrame:
    """Cities joined to the model grid cell whose data they use."""
    cities = load_cities()
    if not GRID_CELLS_CSV.exists():
        raise FileNotFoundError(f"{GRID_CELLS_CSV} missing - run 01_fetch_cams.py first")
    cells = pd.read_csv(GRID_CELLS_CSV)
    return cities.merge(cells, on="city_id", how="left")


def cell_id_for(lat: float, lon: float) -> str:
    return f"{lat:.3f}_{lon:.3f}"
