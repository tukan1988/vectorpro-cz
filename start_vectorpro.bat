@echo off
cd /d "%~dp0"
echo Spoustim VectorPro CZ server...
start "" python server.py
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8765/
echo Otevreno v prohlizeci: http://127.0.0.1:8765/
