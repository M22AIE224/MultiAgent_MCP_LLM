import asyncio
import pprint
from typing import Any
from uuid import uuid4
import httpx
import logging
import os
from dotenv import load_dotenv

# a2a imports
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# -----------------------------------------------------------------------------
# Environment & constants
# -----------------------------------------------------------------------------
data_agent_port = os.getenv("DATA_AGENT_PORT", "10100")
base_url = f"http://localhost:{data_agent_port}"

# -----------------------------------------------------------------------------
# Main async function
# -----------------------------------------------------------------------------
async def main():
    httpx_client = httpx.AsyncClient(verify=False, timeout=900)

    # -------------------------------------------------------------------------
    # 1) Fetch agent card
    # -------------------------------------------------------------------------
    logger.info(f"Trying to fetch agent card from {base_url}/.well-known/agent-card.json")
    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
    public_card = await resolver.get_agent_card()

    logger.info(f"✅ Successfully fetched agent card for DataAgent")
    pprint.pp(public_card.model_dump())

    # -------------------------------------------------------------------------
    # 2) Prepare query
    # -------------------------------------------------------------------------
    data_local_path = os.getenv("DATA_LOCAL_PATH", "./data/source_data.csv")
    data_processed_path = os.getenv("DATA_PROCESSED_PATH", "./artifacts/data_results/processed_data.csv")

    query = (
        f"LOAD path={data_local_path};"
        f"COLUMNS=age,income;"
        f"TARGET=target_col;"
        f"SAVE={data_processed_path}"
    )

    logger.info("----------------------------------FORWARD LAYER 1 CLIENT REQUEST TO A2A -------------------------------")
    logger.info(f"🔹 Query: {query}")

    # -------------------------------------------------------------------------
    # 3) Create client and send message
    # -------------------------------------------------------------------------
    client = A2AClient(httpx_client=httpx_client, agent_card=public_card)

    send_message_payload: dict[str, Any] = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": query}],
            "messageId": uuid4().hex,
        }
    }

    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(**send_message_payload)
    )

    logger.info("Sending message to Data Agent via A2AClient...")

    response = await client.send_message(request)

    logger.info("----------------------------------BACKWARD LAYER 1 A2A RESPONSE TO CLIENT -----------------------------")
    res_json = response.model_dump(mode="json", exclude_none=True)
    pprint.pp(res_json)

    # -------------------------------------------------------------------------
    # 4) Validate and print result
    # -------------------------------------------------------------------------
    if "result" not in res_json:
        logger.error("Full agent response:\n%s", pprint.pformat(res_json))
        raise RuntimeError("Agent returned error. Check server logs.")

    print("\n--- RESPONSE FROM DATA AGENT ---")
    print(res_json["result"]["parts"][-1]["text"])

    await httpx_client.aclose()


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
