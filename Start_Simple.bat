@echo off
title Dynamic Captions Generator - Simple Launcher
cd /d "%~dp0"

echo ========================================
echo    Dynamic Captions Generator
echo ========================================
echo.
echo Pornesc interfata grafica...
echo.

REM Activez environment-ul Python
call ".venv\Scripts\activate.bat"

REM Verific tkinter
python -c "import tkinter" 2>nul
if errorlevel 1 (
    echo ❌ tkinter nu este instalat!
    pause
    exit /b 1
)

REM Verific tkinterdnd2
python -c "import tkinterdnd2" 2>nul
if errorlevel 1 (
    echo 📦 Instalez tkinterdnd2...
    pip install tkinterdnd2
)

REM Lansez UI-ul
echo 🚀 Lansez interfata...
python caption_ui.py

REM Pauza la final pentru erori
if errorlevel 1 (
    echo.
    echo ❌ A aparut o eroare!
    pause
)