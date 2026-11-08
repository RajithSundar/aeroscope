@echo off
cd /d "%~dp0"

if "%1"=="--rebuild" (
    echo [1/6] Downloading CAMS air-quality data for the 131 NCAP cities ^(resumable^)...
    python 01_fetch_cams.py
    if errorlevel 2 (
        echo Open-Meteo daily quota reached. Re-run "start.bat --rebuild" tomorrow to finish.
        exit /b 2
    )
    echo [2/6] Downloading ERA5 winds and mixing height ^(Oct-Feb^)...
    python 01b_fetch_weather.py
    if errorlevel 2 (
        echo Open-Meteo daily quota reached. Re-run "start.bat --rebuild" tomorrow to finish.
        exit /b 2
    )
    echo [3/6] Downloading NASA FIRMS fire detections ^(needs FIRMS_MAP_KEY in .env; skipped otherwise^)...
    python 01c_fetch_firms.py
    echo [4/6] Quality checks and features...
    python 02_clean_and_engineer.py
    echo [5/6] Clustering study and figures...
    python 03_unsupervised_clustering_study.py
    echo [6/6] Exporting city briefs for the web app...
    python 04_export_frontend_data.py
)

echo Starting AeroScope at http://localhost:8080 ...
start "" "http://localhost:8080"
python -m http.server 8080 --directory "%~dp0web"
