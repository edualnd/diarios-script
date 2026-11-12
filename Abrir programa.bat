@echo off
rem Abre o programa dos Diarios de Classe.
rem De dois cliques neste arquivo.
cd /d "%~dp0"

py -3.15 -c "import tkinter, playwright, pypdf, reportlab" >nul 2>&1
if not errorlevel 1 (
    start "" pyw -3.15 programa\app.py
    exit /b
)

python -c "import tkinter, playwright, pypdf, reportlab" >nul 2>&1
if not errorlevel 1 (
    start "" pythonw programa\app.py
    exit /b
)

echo Faltam programas para rodar os Diarios.
echo.
echo De dois cliques em "Instalar dependencias.bat" e depois tente de novo.
echo.
pause
