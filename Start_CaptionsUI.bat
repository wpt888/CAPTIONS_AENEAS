@echo off
title Dynamic Captions Generator - Launcher
cd /d "%~dp0"

echo ========================================
echo    🎬 Dynamic Captions Generator 🎬
echo ========================================
echo.
echo Pornesc interfata grafica...
echo.

REM Activez environment-ul Python
call ".venv\Scripts\activate.bat"

REM Verific si adaug FFmpeg la PATH
echo 🎬 Verific FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FFmpeg nu este in PATH, dar Whisper va incerca sa-l gaseasca...
) else (
    echo ✓ FFmpeg OK
)

REM Verific daca tkinter si tkinterdnd2 sunt instalate
python -c "import tkinter; print('✓ tkinter OK')" 2>nul
if errorlevel 1 (
    echo ❌ tkinter nu este instalat!
    echo Instalez tkinter...
    pip install tk
)

python -c "import tkinterdnd2; print('✓ tkinterdnd2 OK')" 2>nul
if errorlevel 1 (
    echo 📦 Instalez tkinterdnd2 pentru drag&drop...
    pip install tkinterdnd2
)

REM Lansez UI-ul
echo 🚀 Lansez interfata...
python caption_ui.py

REM Pauza la final pentru a vedea eventualele erori
if errorlevel 1 (
    echo.
    echo ❌ A aparut o eroare!
    pause
)