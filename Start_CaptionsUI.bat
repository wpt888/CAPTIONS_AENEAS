@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Dynamic Captions Generator - Launcher
cd /d "%~dp0"

set "VENV_DIR=%~dp0.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "REQUIREMENTS=%~dp0requirements.txt"

echo ========================================
echo    Dynamic Captions Generator
echo ========================================
echo.
echo Pornesc interfata grafica...
echo.

REM Creeaza automat mediul virtual cu o versiune Python compatibila.
if not exist "%PYTHON_EXE%" (
    echo [SETUP] Mediul Python lipseste. Il creez acum...
    set "PYTHON_CMD="

    for %%V in (3.12 3.11 3.10 3.13) do (
        if not defined PYTHON_CMD (
            py -%%V -c "import sys" >nul 2>&1
            if not errorlevel 1 set "PYTHON_CMD=py -%%V"
        )
    )

    if not defined PYTHON_CMD (
        python -c "import sys; raise SystemExit(sys.version_info[:2] not in ((3, 10), (3, 11), (3, 12), (3, 13)))" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=python"
    )

    if not defined PYTHON_CMD (
        echo [EROARE] Este necesar Python 3.10-3.13. Python 3.12 este recomandat.
        echo Descarca Python de la https://www.python.org/downloads/
        pause
        exit /b 1
    )

    !PYTHON_CMD! -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [EROARE] Nu am putut crea mediul virtual: "%VENV_DIR%"
        pause
        exit /b 1
    )

    "%PYTHON_EXE%" -m pip install --upgrade pip
    if errorlevel 1 (
        echo [AVERTISMENT] pip nu a putut fi actualizat. Continui cu versiunea existenta.
    )
)

REM Verifica tkinter din instalarea Python.
"%PYTHON_EXE%" -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [EROARE] Instalarea Python nu include tkinter/Tcl-Tk.
    echo Reinstaleaza Python 3.12 cu optiunea Tcl/Tk bifata.
    pause
    exit /b 1
)

REM Instaleaza automat bibliotecile proiectului doar daca lipsesc.
"%PYTHON_EXE%" -c "import whisper_timestamped, pydub, tkinterdnd2, keyring" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Instalez bibliotecile necesare. Prima instalare poate dura cateva minute...
    "%PYTHON_EXE%" -m pip install -r "%REQUIREMENTS%"
    if errorlevel 1 (
        echo [EROARE] Instalarea bibliotecilor a esuat.
        echo Verifica conexiunea la internet si ruleaza din nou acest launcher.
        pause
        exit /b 1
    )
)

echo [OK] Python si bibliotecile sunt pregatite.

REM Verifica FFmpeg dupa configurarea mediului.
echo Verific FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [AVERTISMENT] FFmpeg nu este in PATH. Aplicatia va incerca detectarea instalarii Winget.
) else (
    echo [OK] FFmpeg
)

if /i "%~1"=="--check" (
    echo [OK] Verificarea mediului s-a incheiat cu succes.
    exit /b 0
)

echo Lansez interfata...
"%PYTHON_EXE%" "%~dp0caption_ui.py"
set "APP_EXIT=%ERRORLEVEL%"

if not "%APP_EXIT%"=="0" (
    echo.
    echo [EROARE] Aplicatia s-a inchis cu codul %APP_EXIT%.
    pause
)

endlocal & exit /b %APP_EXIT%
