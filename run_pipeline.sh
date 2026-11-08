#!/usr/bin/env sh
# macOS / Linux equivalent of "start.bat --rebuild" (without starting the server).
set -e
cd "$(dirname "$0")"
python 01_fetch_cams.py
python 01b_fetch_weather.py
python 01c_fetch_firms.py
python 02_clean_and_engineer.py
python 03_unsupervised_clustering_study.py
python 04_export_frontend_data.py
echo "Done. Serve with: python -m http.server 8080 --directory web"
