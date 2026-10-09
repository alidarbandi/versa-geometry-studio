@echo off
cd /d "%~dp0"
if exist "dist\VersaGeometryStudio\VersaGeometryStudio.exe" (
    start "" "dist\VersaGeometryStudio\VersaGeometryStudio.exe"
    exit /b
)
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m versa_geometry_studio
    exit /b
)
echo Install the application following README.md first.
pause
