@echo off
echo ========================================================
echo Starting Caprae Lead Prioritization & Enrichment Engine
echo ========================================================

echo [1/2] Checking Python backend dependencies...
cd backend
python -m pip install -r requirements.txt

echo [2/2] Launching server on http://localhost:8000 ...
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
