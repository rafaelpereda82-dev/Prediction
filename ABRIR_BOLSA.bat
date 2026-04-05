@echo off
title BVC Master Trader - Menu
cd /d "%~dp0"
call .venv\Scripts\activate

cls
echo ==========================================
echo     BVC MASTER TRADER - MENU PRINCIPAL
echo ==========================================
echo.
echo [1] Abrir App Streamlit (Analisis IA)
echo [2] Abrir Portfolio HTML + API (Visual)
echo.
set /p choice="Selecciona opcion (1 o 2): "

if "%choice%"=="1" goto streamlit
if "%choice%"=="2" goto api

echo Opcion invalida
pause
exit

:streamlit
title Cargando IA Bolsa de Caracas...
start /b streamlit run app_bolsa.py --server.headless true
timeout /t 5
start http://localhost:8501
exit

:api
title Iniciando API Server + Portfolio HTML...
start /b python api_server.py
timeout /t 3
echo.
echo ==========================================
echo API Server iniciado en: http://localhost:5000
echo.
echo Esperando 5 segundos para abrir navegador...
echo ==========================================
timeout /t 5
start http://localhost:5000
exit