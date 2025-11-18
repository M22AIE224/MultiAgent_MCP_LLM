@echo off
REM Move up one directory from /scripts to project root
cd /d "%~dp0.."

set LOG_DIR=scripts\logs
if not exist %LOG_DIR% mkdir %LOG_DIR%

echo Starting all agents and MCP Endpoints...

:: --- Start MCP Servers ---
start "Data MCP" cmd /c "python -m mcp_servers.mcp_data >> %LOG_DIR%\mcp_data.log 2>&1"
start "Modelling MCP" cmd /c "python -m mcp_servers.mcp_ml >> %LOG_DIR%\mcp_ml.log 2>&1"
::start "Visualization MCP" cmd /c "python -m mcp_servers.mcp_dv >> %LOG_DIR%\mcp_dv.log 2>&1"

:: --- Start Agents ---
start "Data Agent" cmd /c "python -m agents.data_agent.agent_main >> %LOG_DIR%\data_agent.log 2>&1"
start "Modelling Agent" cmd /c "python -m agents.ml_agent.agent_main >> %LOG_DIR%\ml_agent.log 2>&1"
start "Visualization Agent" cmd /c "python -m agents.dv_agent.agent_main >> %LOG_DIR%\dv_agent.log 2>&1"


echo All agents and MCP servers started successfully.
pause