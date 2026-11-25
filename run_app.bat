@echo off
title Blocked Internet Server (ipTIME AX3000M)
cd /d "%~dp0"
echo ========================================================
echo  Starting Blocked Internet Server...
echo  Local PC URL   : http://localhost:3088
echo  Smartphone URL : http://192.168.4.2:3088
echo ========================================================
python -m streamlit run app.py --server.port 3088 --server.headless true
pause
