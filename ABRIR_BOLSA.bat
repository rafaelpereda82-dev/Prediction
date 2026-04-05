@echo off
title BVC Master Trader - Iniciando...
cd /d "%~dp0"
call .venv\Scripts\activate

echo ==========================================
echo    BVC MASTER TRADER - INICIANDO
echo ==========================================
echo.
echo Abriendo aplicacion unificada...
echo.

start /b streamlit run app_bolsa.py --server.headless true

timeout /t 5
start http://localhost:8501

exit