@echo off
title Cargando IA Bolsa de Caracas...
cd /d "%~dp0"
call .venv\Scripts\activate
start /b streamlit run app_bolsa.py --server.headless true
timeout /t 5
start http://localhost:8501
exit