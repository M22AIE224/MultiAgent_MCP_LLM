import os
import asyncio
import logging
from uuid import uuid4
from typing import Any, Literal, TypedDict
import json
import httpx
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.graph import StateGraph
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import SendMessageRequest, MessageSendParams
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH, EXTENDED_AGENT_CARD_PATH

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PipelineState(TypedDict, total=False):
    messages: list
    data_results: dict
    ml_result: dict
    dv_result: dict


class SupervisorAgent:
    def __init__(self):
        self.graph = None
        self.agent_cards = {}
        self.httpx_client = httpx.AsyncClient(timeout=900)

    @classmethod
    async def create(cls):
        """Async initializer for SupervisorAgent."""
        self = cls()
        await self.get_a2a_agent_cards()  # now awaited properly
        self.build_graph()
        return self

    async def get_a2a_agent_cards(self):
        agents = {
            "data_agent": f"http://localhost:{os.getenv('DATA_AGENT_PORT', '10100')}",
            "ml_agent": f"http://localhost:{os.getenv('ML_AGENT_PORT', '10200')}",
            "dv_agent": f"http://localhost:{os.getenv('DV_AGENT_PORT', '10300')}",
        }

        for name, base_url in agents.items():
            resolver = A2ACardResolver(httpx_client=self.httpx_client, base_url=base_url)
            try:
                logger.info(f"Fetching agent card from {base_url}{AGENT_CARD_WELL_KNOWN_PATH}")
                public_card = await resolver.get_agent_card()
                client = A2AClient(httpx_client=self.httpx_client, agent_card=public_card)
                self.agent_cards[name] = {"client": client, "card": public_card}
                logger.info(f"{name} card fetched successfully.")
            except Exception as e:
                logger.exception(f"Failed to fetch agent card for {name}: {e}")
                raise RuntimeError("Failed to fetch one or more agent cards") from e

    def build_graph_bkp(self):
        """Builds LangGraph pipeline."""
        builder = StateGraph(PipelineState)
        builder.add_node("data_stage", self.data_stage)
        builder.add_node("ml_stage", self.ml_stage)
        builder.add_node("dv_stage", self.dv_stage)

        builder.add_edge("data_stage", "ml_stage")
        builder.add_edge("ml_stage", "dv_stage")
        builder.add_edge("dv_stage", "__end__")
        builder.set_entry_point("data_stage")

        self.graph = builder.compile()

    def build_graph(self):
        """Builds LangGraph pipeline."""
        builder = StateGraph(PipelineState)
        builder.add_node("ml_stage", self.ml_stage)
        builder.add_node("data_stage", self.data_stage)
        builder.add_node("dv_stage", self.dv_stage)

        builder.add_edge("ml_stage", "data_stage")
        builder.add_edge("data_stage", "dv_stage")
        builder.add_edge("dv_stage", "__end__")
        builder.set_entry_point("ml_stage")

        self.graph = builder.compile()

    async def data_stage(self, state: PipelineState):

        #data_local_path = os.getenv("DATA_LOCAL_PATH", "./data/source_data.csv")
        #data_processed_path = os.getenv("DATA_PROCESSED_PATH", "./artifacts/data_results/processed_data.csv")
      

        # query = (
        #     f"LOAD path={data_local_path};"
        #     f"COLUMNS=age,income;"
        #     f"TARGET=target_col;"
        #     f"SAVE={data_processed_path}"
        # )
        #msg = "What is the calander for 2026?"
        

        ml_output = state.get("ml_result") or {}


        logger.info(f"ML OUTPUT IN Data STAGE: {ml_output!r}")

        try:
            raw_text = ml_output["result"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Could not extract ML text: {e}")
            raw_text = "{}"

        logger.info(f"RAW ML TEXT: {raw_text}")


        # Step 2: First-level JSON parse → returns dict containing "data" (as string)
        try:
            level1 = json.loads(raw_text)
        except Exception as e:
            logger.error(f"JSON parse error (level 1): {e}")
            level1 = {}

        # Step 3: Extract "data" (inner JSON string)
        inner_json_str = level1.get("data", "{}")

        # Step 4: Parse the inner JSON (this contains method)
        try:
            parsed = json.loads(inner_json_str)
        except Exception as e:
            logger.error(f"JSON parse error (inner level): {e}")
            parsed = {}

        # Step 5: Extract the method
        method = parsed.get("method")


        query = (
                    f"STMESSAGE={method};"
                )

        logger.info(f"Extracted method: {method}")


        logger.info("----------------------------------FORWARD LAYER 1 CLIENT REQUEST TO A2A -------------------------------")
        logger.info(f"Query: {query}")

       
        logger.info("Calling data planner agent via A2AClient...")
        client = self.agent_cards["data_agent"]["client"]
        req = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(
                message={
                    "role": "user",
                    "parts": [{"kind": "text", "text": query}],
                    "messageId": uuid4().hex,
                }
            ),
        )
        response = await client.send_message(req)
        logger.info(f"Data Agent Response: {response.model_dump(mode='json', exclude_none=True)}")
        return {"data_results": response.model_dump(mode="json", exclude_none=True)}

    async def ml_stage(self, state: PipelineState):
        logger.info("Calling planner agent via A2AClient...")
        client = self.agent_cards["ml_agent"]["client"]
    
        query = state.get("messages", [{}])[0].get("content", "")
        req = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(
                message={
                    "role": "user",
                    "parts": [{"kind": "text", "text": f"{query}"}],
                    "messageId": uuid4().hex,
                }
            ),
        )
        response = await client.send_message(req)
        return {"ml_result": response.model_dump(mode="json", exclude_none=True)}

    async def dv_stage(self, state: PipelineState):
        """Generate final visualization HTML from ML-stage output."""
        logger.info("DV Stage: Calling dv_agent...")

        try:
            ml_output = state.get("ml_result") or {}

            # Convert ML output to JSON for prompting
            ml_json = json.dumps(ml_output, indent=2)

            # A strong visualization instruction prompt
            dv_prompt = (
                "You are the Data Visualization Agent.\n\n"
                "Your job:\n"
                "1. Read the processed ML output below.\n"
                "2. Generate visualizations OR combined HTML content.\n"
                "3. ALWAYS return pure HTML only. No markdown.\n\n"
                "ML Output:\n"
                f"{ml_json}"
            )

            logger.info("DV Promt: " )
            logger.info(dv_prompt)
            # Build DV request
            req = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(
                    message={
                        "role": "user",
                        "parts": [{"kind": "text", "text": dv_prompt}],
                        "messageId": uuid4().hex,
                    }
                ),
            )

            client = self.agent_cards["dv_agent"]["client"]
            response = await client.send_message(req)

            # This gives structured A2A response
            dv_json = response.model_dump(mode="json", exclude_none=True)

            # Extract text message (HTML expected)
            logger.info("DV JSON response:")
            logger.info(dv_json)
            dv_html = ""
            try:
                #dv_html = dv_json["message"]["parts"][0]["text"]
                dv_html = dv_json["result"]["parts"][0]["text"]
                logger.info(f"DV HTML : {dv_html}")
            except:
                logger.warning("DV Agent did not return expected HTML. Full response returned.")

            logger.info("DV Stage complete.")
            return {
                "dv_result": dv_json,
                "dv_html": dv_html
            }

        except Exception as e:
            logger.exception("DV Stage failed.")
            raise
        
    async def dv_stage_bkp(self, state: PipelineState):
        logger.info("Calling dv_agent via A2AClient...")
        client = self.agent_cards["dv_agent"]["client"]
        prev_ml = state.get("ml_result", {})
        req = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(
                message={
                    "role": "user",
                    "parts": [{"kind": "text", "text": f"Generate visualizations for {prev_ml}"}],
                    "messageId": uuid4().hex,
                }
            ),
        )
        response = await client.send_message(req)
        return {"dv_result": response.model_dump(mode="json", exclude_none=True)}

    async def run_pipeline_bkp(self):
        logger.info("Running pipeline via LangGraph...")
        result = await self.graph.ainvoke({"messages": [HumanMessage(content="Start pipeline")]})
        logger.info(f"Pipeline combined Result : {result}")
        logger.info("Pipeline finished.")
        return result
    
    async def run_pipeline(self, question: str):

        logger.info("Running pipeline via LangGraph...")

        result = await self.graph.ainvoke({
            "messages": [{"role": "user", "content": question}]
        })

        logger.info("Pipeline finished.")
        logger.info(result)
        return result
