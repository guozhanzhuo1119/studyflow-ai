@echo off
cd /d "%~dp0nginx-1.29.8"
start "" nginx.exe
echo nginx started: http://localhost/
