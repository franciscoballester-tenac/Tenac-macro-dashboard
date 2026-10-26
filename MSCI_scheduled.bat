@echo off
cd /d "%~dp0"

REM Corrida diaria de MSCI_Download.py (incremental) desde Task Scheduler, sin pause
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
chcp 65001 >nul

if not exist "%~dp0logs" mkdir "%~dp0logs"
set LOG=%~dp0logs\MSCI_Download.log

echo ============================================================ >> "%LOG%"
echo [%date% %time%] INICIO MSCI_Download.py >> "%LOG%"

"C:\Users\Francisco\anaconda3\python.exe" MSCI_Download.py >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%

echo [%date% %time%] FIN (exit code %RC%) >> "%LOG%"
exit /b %RC%
