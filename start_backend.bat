@echo off
title AXIOM Neural Core (Backend)
cd services\ai

echo Checking for virtual environment...
if not exist venv (
    echo [INFO] Creating venv...
    py -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv with 'py'. Trying 'python'...
        python -m venv venv
    )
    
    echo [INFO] Activating venv and installing dependencies...
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    echo [INFO] Venv found. Activating...
    call venv\Scripts\activate
)

echo [INFO] Starting Uvicorn Server...
py -m uvicorn main:app --reload --port 8000
if errorlevel 1 (
    echo [ERROR] 'py' failed. Trying 'python'...
    python -m uvicorn main:app --reload --port 8000
)

pause
