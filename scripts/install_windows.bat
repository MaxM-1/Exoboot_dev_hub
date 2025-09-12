@echo off
REM Installation script for Windows 11
REM Run as Administrator: scripts\install_windows.bat

echo === Exoboot Perception Experiment - Windows Installation ===
echo Installing for Windows 11...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.11 or higher from https://python.org
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1') do set python_version=%%a
echo Python version: %python_version%

REM Create virtual environment
echo Creating virtual environment...
python -m venv .venv
if %errorlevel% neq 0 (
    echo Error: Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel

REM Install FlexSEA package
echo Installing FlexSEA package...
if exist "Actuator-Package-develop" (
    pip install -e ./Actuator-Package-develop
) else (
    echo Warning: FlexSEA package not found in Actuator-Package-develop/
    echo Please ensure the FlexSEA package is available and install it manually:
    echo   pip install -e ./Actuator-Package-develop
)

REM Install project dependencies
echo Installing project dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

REM Install development dependencies (optional)
if "%1"=="dev" (
    echo Installing development dependencies...
    pip install -r requirements-dev.txt
    
    REM Install pre-commit hooks
    pre-commit install
)

REM Install the project in editable mode
echo Installing exoboot-perception-experiment package...
pip install -e .

REM Create necessary directories
echo Creating data directories...
if not exist "data" mkdir data
if not exist "results" mkdir results
if not exist "settings" mkdir settings
if not exist "logs" mkdir logs

echo.
echo === Installation Complete! ===
echo.
echo To activate the environment:
echo   .venv\Scripts\activate.bat
echo.
echo To run the experiment:
echo   python -m exoboot_perception.gui
echo   # OR
echo   exoboot-experiment
echo.
echo To deactivate the environment:
echo   deactivate
echo.
pause