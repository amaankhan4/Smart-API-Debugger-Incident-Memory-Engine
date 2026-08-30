@echo off
rem Double-click entry point for the Incident Memory Engine development stack.
setlocal
title Incident Memory Engine
cd /d "%~dp0"

set "PY_CMD="

rem A project virtual environment wins over anything on PATH.
if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PY_CMD=venv\Scripts\python.exe"
) else (
    where py >nul 2>nul && set "PY_CMD=py -3"
)

if not defined PY_CMD (
    where python >nul 2>nul && set "PY_CMD=python"
)

if not defined PY_CMD (
    echo.
    echo   Python was not found.
    echo   Install Python 3.11+ from https://www.python.org/downloads/
    echo   and make sure "Add python.exe to PATH" is ticked.
    echo.
    pause
    exit /b 1
)

%PY_CMD% start.py %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo   Startup exited with code %EXIT_CODE%. Read the message above.
    echo.
    pause
)

exit /b %EXIT_CODE%
