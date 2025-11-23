@echo off
REM Distributed Deadlock Simulation - Windows Batch Startup Script

echo.
echo ============================================================
echo 🛜 Distributed Deadlock Simulation
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to your PATH
    pause
    exit /b 1
)

REM Check if Streamlit is installed
python -m pip show streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠ Streamlit is not installed
    echo Installing required packages...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Failed to install requirements
        pause
        exit /b 1
    )
)

REM Get current directory
cd /d "%~dp0"

echo Starting application...
echo.

REM Run the Streamlit application with environment variables
python -m streamlit run app.py ^
    --server.port=8503 ^
    --server.address=localhost ^
    --client.showErrorDetails=true ^
    --logger.level=info

if %errorlevel% neq 0 (
    echo.
    echo ❌ Error starting application
    pause
    exit /b 1
)

pause
