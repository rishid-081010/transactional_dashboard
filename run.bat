@echo off
echo Starting Asquared AI Dubai Real Estate Analytics Dashboard...
start http://localhost:3000
py -m uvicorn main:app --host 0.0.0.0 --port 3000 --reload
pause
