@echo off
echo ==========================================
echo   Stopping specific agent & MCP ports...
echo ==========================================

:: List of ports you want to stop (add/remove as needed)
set PORTS=10010 10020 10030 10100 10200 10300 10400 10500
::set PORTS=10100 10200 10300 10010 10500



for %%P in (%PORTS%) do (
    echo Checking port %%P ...
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P" ^| findstr "LISTENING"') do (
        echo   Killing PID %%A on port %%P ...
        taskkill /PID %%A /F >nul 2>&1
    )
)


echo ------------------------------------------
echo Done. Checked and stopped all listed ports.
echo ==========================================
pause
