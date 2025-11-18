from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP
import asyncio
import uvicorn
import contextlib
import base64
import requests
import os
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin
# ------------------------
# MCP Setup
# ------------------------
data_mcp = FastMCP("Data MCP Server", stateless_http=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@data_mcp.tool()
async def download_data() -> dict:
    """Simulate data download."""
    print("Running download_data()")
    return {"status": "success", "message": "Data downloaded successfully."}

@data_mcp.tool()
async def process_data() -> dict:
    """Simulate data processing."""
    print("Running process_data()")
    return {"status": "success", "message": "Data processed successfully."}

# ------------------------
# Lifespan for MCP session
# ------------------------
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(data_mcp.session_manager.run())
        yield

app = FastAPI(lifespan=lifespan)

# Mount the MCP HTTP app directly under /data
app.mount("/data", data_mcp.streamable_http_app())

# ------------------------
# Helper FastAPI wrapper endpoint for manual invoke
# ------------------------
class ToolRequest(BaseModel):
    tool: str

@app.post("/data/tools/run", summary="Run a registered MCP tool")
async def run_tool(req: ToolRequest):
    tools = await data_mcp.get_tools()
    tool = next((t for t in tools if t.name == req.tool), None)

    if not tool:
        return {"error": f"Tool '{req.tool}' not found."}

    print(f"Invoking MCP tool: {req.tool}")
    result = await tool.run({})
    return result



@app.get("/load_data")
def load_data():
    """
    Download IIT Jodhpur academic data (HTML and PDF) from official URLs.
    Saves them into 'pre_processed/' folder and returns their base64-encoded contents.

    Returns:
        dict: {
            "ug_curriculum": "<base64-encoded HTML>",
            "academic_programs": "<base64-encoded HTML>",
            "all_curriculum": "<base64-encoded HTML>",
            "academic_calendar": "<base64-encoded PDF>"
        }
    """
    urls = {
        "ug_curriculum": "http://academics.iitj.ac.in/?page_id=377",
        "academic_programs": "https://iitj.ac.in/office-of-academics/en/list-of-academic-programs",
        "all_curriculum": "https://iitj.ac.in/office-of-academics/en/curriculum",
        "academic_calendar": "https://www.iitj.ac.in/PageImages/Gallery/07-2025/Academic-Calendar-AY-202526SemI2-with-CCCD-events-638871414539740843.pdf"
    }

    preprocessed_folder = os.getenv("DATA_OUTPUT_DIR", "./artifacts/data_results")
    os.makedirs(preprocessed_folder, exist_ok=True)

    results = {}
    logger.info(f"MCP Data extract invoked for URLs: {urls}")

    for name, url in urls.items():
        try:
            print(f"⬇️ Downloading {name} from {url}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Determine file type and save accordingly
            if url.endswith(".pdf"):
                # Directly save PDF
                file_path = os.path.join(preprocessed_folder, f"{name}.pdf")
                with open(file_path, "wb") as f:
                    f.write(response.content)

            else:
                         # Parse HTML and download stylesheets
                html_content = response.text
                soup = BeautifulSoup(html_content, "html.parser")

                css_dir = os.path.join(preprocessed_folder, f"{name}_css")
                os.makedirs(css_dir, exist_ok=True)

                for link_tag in soup.find_all("link", rel="stylesheet"):
                    css_url = urljoin(url, link_tag["href"])
                    css_name = os.path.basename(css_url.split("?")[0])
                    css_path = os.path.join(css_dir, css_name)

                    try:
                        css_resp = requests.get(css_url, timeout=15)
                        css_resp.raise_for_status()
                        with open(css_path, "w", encoding="utf-8") as f:
                            f.write(css_resp.text)

                        # Update link href to local path
                        link_tag["href"] = f"./{name}_css/{css_name}"
                        print(f"  ✅ Downloaded stylesheet: {css_name}")

                    except Exception as css_err:
                        print(f"  ⚠️ Failed to download {css_url}: {css_err}")

                # Save updated HTML
                file_path = os.path.join(preprocessed_folder, f"{name}.html")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(soup))

             # Base64 encode saved file
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            
            results[name] = encoded

            print(f"✅ Saved {file_path}")

        except Exception as e:
            results[name] = f"Failed to download {url}: {e}"
            print(f"❌ Error downloading {name}: {e}")

    return results


@app.get("/debug/tools")
async def list_tools():
    """Debug route to list registered tools safely."""
    tools = await data_mcp.list_tools()
    # Convert everything to string for JSON safety
    tool_names = []
    for t in tools:
        if isinstance(t, str):
            tool_names.append(t)
        elif hasattr(t, "name"):
            tool_names.append(t.name)
        elif callable(t):
            tool_names.append(t.__name__)
        else:
            tool_names.append(str(t))
    return {"registered_tools": tool_names}


import uvicorn

HOST = "0.0.0.0"
PORT = 10010

# 🔍 DEBUG: list all registered routes before server starts
def print_routes(router, prefix=""):
    for route in router.routes:
        # Handle mounted sub-apps (like /data → FastMCP)
        if hasattr(route, "app"):
            print(f"MOUNTED APP: {prefix}{route.path}")
            if hasattr(route.app, "router"):
                print_routes(route.app.router, prefix + route.path)
        else:
            methods = getattr(route, "methods", [])
            print(f"ROUTE: {prefix}{route.path} → {list(methods)}")

# 🔍 Print all routes
print_routes(app.router)

for route in app.routes:
    print(route.path)

def print_datamcp_route(data_mcp):
    print("\n=== MCP ROUTES ===")
    for route in getattr(data_mcp.streamable_http_app(), "router", []).routes:
        path = getattr(route, "path", "<no-path>")
        methods = getattr(route, "methods", None)
        if methods:
            print(f"MCP ROUTE: {path} → {list(methods)}")
        else:
            print(f"MCP ROUTE: {path} → (no methods)")

print_datamcp_route(data_mcp)      


# ------------------------
# Run server
# ------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10010)
