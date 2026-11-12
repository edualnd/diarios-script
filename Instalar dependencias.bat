@echo off
rem Instala as dependencias Python SEM internet, a partir da pasta "dependencias".
rem De dois cliques neste arquivo (uma vez so, no computador novo).
cd /d "%~dp0"
py -3.15 -m pip install --no-index --find-links=dependencias -r requirements.txt || python -m pip install --no-index --find-links=dependencias -r requirements.txt
echo.
pause
