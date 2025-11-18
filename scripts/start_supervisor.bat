@echo off
REM Move up one directory from /scripts to project root
cd /d "%~dp0.."

set LOG_DIR=scripts\logs
if not exist %LOG_DIR% mkdir %LOG_DIR%

echo Starting Supervisor Endpoints...


start "Supervisor Agent" cmd /c "python -m supervisor_agent.supervisor_api >> %LOG_DIR%\supervisor_agent.log 2>&1"


echo Supervisory Agent started successfully.
pause