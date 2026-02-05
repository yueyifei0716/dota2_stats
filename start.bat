@echo off
REM Start Dota 2 Stats Flask Server

echo Starting Dota 2 Stats server...
echo Access at: http://127.0.0.1:5000
echo Press Ctrl+C to stop
echo.

cd /d "%~dp0"
C:\Users\there\miniconda3\envs\dota2\python.exe app.py
