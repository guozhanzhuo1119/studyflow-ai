@echo off
cd /d "%~dp0nginx-1.29.8"
nginx.exe -s stop
echo nginx stopped
