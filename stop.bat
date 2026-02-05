@echo off
REM Stop Dota 2 Stats Flask Server

echo Stopping Dota 2 Stats server...

REM Find and kill python processes running on port 5000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo Killing process %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo Server stopped.
