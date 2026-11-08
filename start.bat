@echo off
cd /d "%~dp0"

if "%1"=="--rebuild" (
    echo [1/4] Extracting daily ISRO INSAT-3D + CPCB dataset...
    python 01_extract_dataset.py
    echo [2/4] Cleaning dataset and engineering regional seasonal/source features...
    python 02_clean_and_engineer.py
    echo [3/4] Running unsupervised clustering study and saving figures...
    python 03_unsupervised_clustering_study.py
    echo [4/4] Exporting frontend telemetry payload to web/data.js...
    python 04_export_frontend_data.py
)

echo Starting AeroScope Web Workbench at http://localhost:8080 ...
start "" "http://localhost:8080"
python -m http.server 8080 --directory "%~dp0web"
