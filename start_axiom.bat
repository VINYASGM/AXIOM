@echo off
echo ===========================================
echo   AXIOM: Autonomous Execution Environment
echo   Initializing Neural Core v2.0...
echo ===========================================

start start_backend.bat
start start_frontend.bat

echo.
echo [SYSTEM] Launch signals sent.
echo [SYSTEM] Backend: Port 8000
echo [SYSTEM] Frontend: Port 3000
echo.
echo Launching access portal...

timeout /t 15

start http://localhost:3000

echo.
echo ===========================================
echo   SYSTEM ONLINE
echo ===========================================
pause
