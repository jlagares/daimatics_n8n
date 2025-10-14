@echo off
echo Installing FastAPI dependencies...
cd /d "%~dp0"
call "..\venv\Scripts\activate.bat"

echo Installing required packages...
pip install -r requirements_api.txt

echo Starting Email Scraper API...
echo API will be available at: http://localhost:8000
echo API documentation at: http://localhost:8000/docs
echo Press Ctrl+C to stop the server
echo.

python scraper_api.py