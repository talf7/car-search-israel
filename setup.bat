@echo off
echo ============================================
echo    Car Search App - Setup
echo ============================================
echo.

:: Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Trying to install via winget...
    winget install --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo.
        echo Auto-install failed.
        echo Please download Python from: https://www.python.org/downloads/
        echo IMPORTANT: Check "Add Python to PATH" during installation.
        echo Then run this file again.
        pause
        exit /b 1
    )
    echo.
    echo Python installed successfully!
    echo Please close and reopen this window to refresh PATH, then run again.
    pause
    exit /b 0
)

echo Installing Python libraries...
python -m pip install customtkinter requests pyinstaller --quiet
if %errorlevel% neq 0 (
    echo Error installing libraries. Check your internet connection.
    pause
    exit /b 1
)

echo.
echo Building car_search.exe - please wait...
python -m PyInstaller --onefile --windowed --name car_search main.py
if %errorlevel% neq 0 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   SUCCESS!
echo   File is ready at: dist\car_search.exe
echo   Double-click to run.
echo ============================================
pause
