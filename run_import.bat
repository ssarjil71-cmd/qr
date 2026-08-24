@echo off
REM Run import script from project root
pushd "%~dp0"
"%~dp0\.venv\Scripts\python.exe" "scripts\import_districts_geojson.py"
IF ERRORLEVEL 1 echo Import script returned error: %ERRORLEVEL%
popd
