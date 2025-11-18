import uvicorn
import contextlib
import base64
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
import os
import base64
import requests
from dotenv import load_dotenv
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from fastapi import FastAPI

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_data.session_manager.run())
        yield

load_dotenv()
mcp_data = FastMCP("Data downloader MCP Server", stateless_http=True)

app = FastAPI(lifespan=lifespan)
app.mount("/data", mcp_data.streamable_http_app())

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
            print(f"Downloading {name} from {url}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Determine file type and save accordingly
            if url.endswith(".pdf"):
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
                        print(f"Downloaded stylesheet: {css_name}")

                    except Exception as css_err:
                        print(f" Failed to download {css_url}: {css_err}")

                # Save updated HTML
                file_path = os.path.join(preprocessed_folder, f"{name}.html")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(soup))


            # Encode file as base64 for return
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")

            results[name] = encoded
            print(f"Saved {file_path}")

        except Exception as e:
            results[name] = f"Failed to download {url}: {e}"
            print(f"Error downloading {name}: {e}")

    return results
    
@mcp_data.tool()
def download_data() -> dict:
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
    
    os.makedirs(os.path.dirname(preprocessed_folder), exist_ok=True)

    results = {}

    logger.info(f"MCP Data extract invoked or : {urls}")
    for name, url in urls.items():
        try:
            print(f"Downloading {name} from {url}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Determine file type and save accordingly
            if url.endswith(".pdf"):
                file_path = os.path.join(preprocessed_folder, f"{name}.pdf")
                mode = "wb"
                file_data = response.content
            else:
                file_path = os.path.join(preprocessed_folder, f"{name}.html")
                mode = "w"
                file_data = response.text

            # Save file
            with open(file_path, mode) as f:
                f.write(file_data)

            # Encode file as base64 for return
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")

            results[name] = encoded
            print(f"✅ Saved {file_path}")

        except Exception as e:
            results[name] = f"Failed to download {url}: {e}"
            print(f"❌ Error downloading {name}: {e}")

    return results

def download_data_bkp() -> str:
    """Download a CSV dataset and return it as a base64-encoded string."""
    try:
        #constant_data_path = "data/source_data.csv"
        data_local_path = os.getenv("DATA_LOCAL_PATH", "./data/source_data.csv")
        with open(data_local_path, "rb") as f:
            file_content = f.read()
        result = base64.b64encode(file_content).decode("utf-8")
    except Exception as e:
        result = f"Data sending failed due to {e}"
    return result





if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
  
    
    port = int(os.getenv("DATA_MCP_PORT", 10010))
    print(f"ML MCP Server running on http://127.0.0.1:{port}/data")
    uvicorn.run(app, host="127.0.0.1", port=port)
    #uvicorn.run(mcp_data, host="0.0.0.0", port=port)

