"""Shared helpers for the AeroScope pipeline (paths, city list, HTTP, AQI, geometry)."""

import sys

# Windows consoles default to cp1252, which cannot print labels such as "SO₂".
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
