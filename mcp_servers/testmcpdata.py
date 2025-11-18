import requests
import logging
from typing import Any, Dict

# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("MCPClient")

# ---------------------------------------------------------------------
# MCP Client Utility
# ---------------------------------------------------------------------
def call_mcp_tool(tool_name: str, payload: Dict[str, Any] | None = None, base_url: str = "http://127.0.0.1:10010") -> Dict[str, Any]:
    """Call a specific MCP tool endpoint with optional JSON payload."""
    if payload is None:
        payload = {}

    url = f"{base_url}/tools/{tool_name}"
    logger.info(f"Sending POST request to MCP tool: {url}")

    try:
        response = requests.post(url, json=payload, timeout=10)
        logger.info(f"Response: {response.status_code} {response.reason}")
        logger.debug(f"Raw Body: {response.text}")

        # Raise for HTTP errors
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call MCP tool '{tool_name}': {e}")
        return {"error": str(e)}

# ---------------------------------------------------------------------
# Example Usage
# ---------------------------------------------------------------------
if __name__ == "__main__":
    result = call_mcp_tool("download_data")
    logger.info(f"Tool Result: {result}")
