@echo off
echo ==========================================
echo   Stopping specific agent & MCP ports...
echo ==========================================

:: List of ports you want to stop (add/remove as needed)
set PORTS=10100 10200 10300 10010 10020 10030 10400 10500


for %%P in (%PORTS%) do (
    echo Checking port %%P ...
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P" ^| findstr "LISTENING"') do (
        echo   Running PID %%A on port %%P ...
        
    )
)
