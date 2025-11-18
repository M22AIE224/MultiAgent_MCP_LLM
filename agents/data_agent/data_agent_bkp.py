import os
import io
import json
import base64
import httpx
import pandas as pd
import logging
from dotenv import load_dotenv
from a2a.types import Message, Part, Role
import uuid


# ============ Setup Logging ============ #
load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class DataAgent:
    """
    DataAgent (MCP Client):
    - Loads local CSV if available, else fetches remote data from MCP.
    - Performs feature engineering and saves a preprocessed dataset.
    
    Example Query:
        LOAD path=./data/source_data.csv;
             COLUMNS=col1,col2;
             TARGET=target_col;
             SAVE=./artifacts/data_results/processed_data.csv
    """

    @staticmethod
    def extract_query_from_task(task) -> str | None:
        """Safely extract query text from a2a RequestContext or dict-based task"""
        try:
            # Case 1: Already a string
            if isinstance(task, str):
                return task.strip()

            # Case 2: Dict or JSON structure
            if isinstance(task, dict):
                msg = task.get("params", {}).get("message", {})
                parts = msg.get("parts", [])
                for p in parts:
                    if isinstance(p, dict):
                        # Support both direct text or root.text
                        if "text" in p:
                            return p["text"]
                        if "root" in p and isinstance(p["root"], dict) and "text" in p["root"]:
                            return p["root"]["text"]
                return None

            # Case 3: A2A RequestContext (your actual case)
            if hasattr(task, "message") and hasattr(task.message, "parts"):
                for p in task.message.parts:
                    # p is a Part(root=TextPart(...))
                    if hasattr(p, "root") and hasattr(p.root, "text"):
                        return getattr(p.root, "text", None)
                    elif hasattr(p, "text"):
                        return getattr(p, "text", None)

            return None
        except Exception as e:
            logger.exception(f"Error extracting query from task: {e}")
            return None


    async def invoke(self, query: str, context_id: str) -> str:
        try:
            logger.info(f"Invoked DataAgent with query: {repr(query)} and context_id={context_id}")

            # ============ Validate Query ============ #
            logger.info("==== DEEP TASK INSPECTION ====")
            try:
                logger.info(f"Type: {type(query)}")
                for attr in dir(query):
                    if attr.startswith("_"):
                        continue
                    try:
                        value = getattr(query, attr)
                        logger.info(f"  • query.{attr} = {repr(value)}")
                        # Dive into nested request/params if found
                        if attr in ("request", "params") or "param" in attr:
                            if hasattr(value, "__dict__"):
                                logger.info(f"    ⤷ {attr}.__dict__ = {json.dumps(value.__dict__, default=str, indent=2)}")
                    except Exception as inner:
                        logger.warning(f"Could not read attr {attr}: {inner}")
            except Exception as dump_err:
                logger.exception(f"Failed to introspect task: {dump_err}")
            logger.info("===================================")

            # Automatically unwrap query if it's embedded in a RequestContext or dict
            if not isinstance(query, str) or not query.strip():
                logger.info("Query is not a plain string, attempting to extract from task...")
                extracted_query = DataAgent.extract_query_from_task(query)
                logger.info(f"Extracted query: {extracted_query}")
                query = extracted_query
                
            # Validate after unwrapping
            if not query or not isinstance(query, str) or not query.strip():
                raise ValueError("Invalid or empty query provided to DataAgent.invoke()")

            logger.info(f"DataAgent invoked with query: {query!r}")

            # ============ Default Configuration ============ #
            local_path = os.getenv("DATA_LOCAL_PATH", "./data/source_data.csv")
            remote_port = os.getenv("DATA_MCP_PORT", "10010")
            mcp_url = f"http://localhost:{remote_port}/load_data"
            out_dir = os.getenv("DATA_OUTPUT_DIR", "./artifacts/data_results")
            data_processed_path = os.getenv("DATA_PROCESSED_PATH", "./artifacts/data_results/processed_data.csv")
            #os.makedirs(out_dir, exist_ok=True)
            os.makedirs(os.path.dirname(out_dir), exist_ok=True)


            logger.info(f"Using MCP URL: {mcp_url}")
            logger.info(f"Using output directory: {out_dir}")

            # ============ Parse Query ============ #
            #kv = {}
            #for part in query.split(";"):
            #    if "=" in part:
            #        k, v = part.split("=", 1)
            #        kv[k.strip().upper()] = v.strip()

            kv = {}
            for part in query.split(";"):
                part = part.strip()
                if not part:
                    continue
                if part.upper().startswith("LOAD "):
                    part = part[len("LOAD "):]
                if "=" in part:
                    k, v = part.split("=", 1)
                    kv[k.strip().upper()] = v.strip()

            logger.info(f"Parsed query parameters: {kv}")

            # Extract parameters safely
            path = kv.get("PATH", local_path)
            cols = kv.get("COLUMNS")
            target = kv.get("TARGET")
            save_path = kv.get("SAVE", data_processed_path)

            logger.info(f"SAVE PATH in Query - {kv.get('SAVE')}")
            logger.info(f"Parsed query params: {json.dumps(kv, indent=2)}")
            logger.info(f"Input path: {path} | Output path: {save_path}")


            logger.info(f"SAVE PATH derived - {save_path}")
            
            columns = [c.strip() for c in cols.split(",")] if cols else None
            df = None

            logger.info("--------------------------------FORWARD LAYER 3 MCP to Data Access ------------------------------")
            logger.info(f"REQUEST : \n {path} ")

            refresh_folder = False

            # ============ Load Data ============ #
            if os.path.exists(out_dir) and os.path.isdir(out_dir):
                files = [f for f in os.listdir(out_dir) if os.path.isfile(os.path.join(out_dir, f))]
                if files:
                    refresh_folder= False
                else:
                    refresh_folder = True
            else:
                refresh_folder = True

            if refresh_folder:
                logger.warning(f"Local file not found at {path}. Fetching from MCP: {mcp_url}")
                async with httpx.AsyncClient(verify=False, timeout=120) as client:
                    # ✅ Use GET instead of POST
                    response = await client.get(mcp_url)
                    response.raise_for_status()
                    

            #logger.info(f"Processed data saved at {save_path}")

            logger.info("--------------------------------FORWARD LAYER 3 Preprocessing data  ------------------------------")
            #logger.info(f"DATA SAVED : \n {save_path} ")


            summary = {
                "rows": "",
                "columns":"",
                "target": "",
                "source": "local" if not refresh_folder else  "remote_mcp",
                "processed_path": os.path.abspath(save_path),
            }

            #logger.info("DataAgent finished successfully.")
            logger.info("Data Agent execution completed successfully with result:")
            logger.info(summary)

            # Wrap result properly in A2A Message object
            #message = Message(
            #    messageId=str(uuid.uuid4()),  # required
            #    role=Role.agent,
            #    parts=[Part(kind="text", text=json.dumps(summary, indent=2))]
            #)
           
            #response = message.model_dump()
            #logger.info("Data Agent execution completed successfully with structured JSON:")
            #logger.info(json.dumps(response, indent=2)) 
            #return message.model_dump()

            #logger.info("DataAgent finished successfully. Returning structured summary.")
            #logger.info(json.dumps(summary, indent=2))

            logger.info("--------------------------------BACKWARD LAYER 3 SENDING RESPONSE TO A2A  ------------------------------")
            logger.info(f"RESPONSE : \n {json.dumps(summary, indent=2)} ")

            # Return plain dict so the A2A executor can wrap it properly
            return summary
        except Exception as e:
            logger.exception(f"DataAgent invoke failed: {e}")
            raise
