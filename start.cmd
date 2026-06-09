@echo off
REM MetricWatch — Windows launcher (use this instead of start.sh)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
