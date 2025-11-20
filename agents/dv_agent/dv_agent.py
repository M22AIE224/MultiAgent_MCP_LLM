# agents/dv_agent/dv_agent.py
import os
import logging
import httpx
from dotenv import load_dotenv

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


load_dotenv()
DATA_OUTPUT_DIR = os.getenv("DATA_OUTPUT_DIR")

if not DATA_OUTPUT_DIR:
    raise RuntimeError("DATA_OUTPUT_DIR must be set in the .env file")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class DVAgent:
    """
    DV Agent: orchestrates visualization requests to MCP_DV.
    """

    def __init__(self):
        #self.mcp_port = os.getenv("DV_MCP_PORT", "10030")
        # self.mcp_url = f"http://localhost:{self.mcp_port}"
        logger.info("-------------Initilizing Critic-------------")

    async def invoke_bkp(self, query: str, context_id: str, params: dict = None):
        """
        query: textual request/intent (not strictly required)
        params: optional dict to pass to MCP (e.g., {'predictions_path': ..., 'save_prefix': ...})
        """
        try:
            logger.info("DVAgent invoked: query=%s context_id=%s params=%s", query, context_id, params)
            payload = params or {}
            # include context info (optional)
            payload.setdefault("context_id", context_id)
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(f"{self.mcp_url}/visualize/results", json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.exception("DVAgent failed")
            raise

    async def invoke(self, query: str, context_id: str, params: dict = None):
        """
        query: textual request/intent
        params: optional dict such as:
            { 'files': ['output.html', 'graph.pdf'] }
        """
        try:
            response_html = await self.combine_results(params)
            return response_html
        except Exception as e:
            logger.exception("DVAgent failed")
            raise

    def render_html_card(self,title, content):
        return f"""
        <section class="dv-card">
            <h2>{title}</h2>
            {content}
        </section>
        """


    def render_iframe(self, resource_url):
        return f"""
        <iframe src="{resource_url}" class="dv-iframe"></iframe>
        """


    def render_pdf(self,resource_url):
        return f"""
        <embed src="{resource_url}" type="application/pdf" class="dv-pdf" />
        """
    
    async def combine_results(self, payload: dict = None):
       
        if payload is None:
            payload = {}

        try:  

            file_names = os.listdir(DATA_OUTPUT_DIR)
            logger.info(f"File Names in the folder {DATA_OUTPUT_DIR}")
            logger.info(file_names)
            #if "files" not in payload:
             #   raise HTTPException(status_code=400, detail="Payload must include 'files'")

            #file_names = payload["files"]
            combined_html_parts = []


            for name in file_names:
                file_path = os.path.join(DATA_OUTPUT_DIR, name)

                if not os.path.exists(file_path):
                    combined_html_parts.append(
                        f"<div style='color:red'>⚠ File not found: {file_path}</div>"
                    )
                    continue

                ext = os.path.splitext(name)[1].lower()

                resource_url = f"/static/resource/{name}"
                # ---------------------------
                # HTML FILE
                # ---------------------------

                if ext in [".html", ".htm"]:
                    content = self.render_iframe(resource_url)
                    combined_html_parts.append( self.render_html_card(f"HTML Resource: {name}", content))
                    # Instead of reading file content, serve as iframe
                    # resource_url = f"/static/resource/{name}"  # Flask route you will create


                    # wrapped = f"""
                    # <section style="margin-bottom:30px; padding:20px; border:1px solid #ccc; border-radius:8px;">
                    #     <h2>HTML Resource: {name}</h2>
                    #     <iframe src="{resource_url}" 
                    #             style="width:100%; height:600px; border:none;">
                    #     </iframe>
                    # </section>
                    # """
                    # combined_html_parts.append(wrapped)
                # ---------------------------
                # PDF FILE
                # ---------------------------
                elif ext == ".pdf":
                    content = self.render_pdf(resource_url)
                    combined_html_parts.append(self.render_html_card(f"PDF Resource: {name}", content))
                    # wrapped = f"""
                    # <section style="margin-bottom:30px; padding:20px; border:1px solid #ccc; border-radius:8px;">
                    #     <h2>PDF Resource: {name}</h2>
                    #     <embed src="/static/resource/{name}" type="application/pdf" width="100%" height="800px" />
                    # </section>
                    # """
                    # combined_html_parts.append(wrapped)

                # else:
                #     combined_html_parts.append(
                #         f"<p style='color:orange'>Unsupported file type: {name}</p>"
                #     )

            final_page = f"""
            <html>

            <body>
                <h1>Visualization Results</h1>
                {''.join(combined_html_parts)}
            </body>
            </html>
            """
            logger.info(f"Combined files : {final_page}")
            #return HTMLResponse(content=final_page, status_code=200)
            return final_page
                

        except Exception as e:
            logger.exception("Error in combine_results()")
            raise