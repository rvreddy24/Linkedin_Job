@echo off
cd /d "%~dp0"
echo ===================================================
echo   Auto Bot LinkedIn Job - On-Demand Search
echo ===================================================
echo Running hunt across 5 job feeds...
python -m engine.run_hunt
echo.
echo ===================================================
echo   Done! Check your Discord channel for new leads.
echo ===================================================
pause
