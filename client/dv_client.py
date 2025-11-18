# client/dv_client.py
import asyncio
import logging
import pprint
from uuid import uuid4
import httpx
import os
from dotenv import load_dotenv
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dv_client")

dv_agent_port = os.getenv("DV_AGENT_PORT", "10300")
base_url = f"http://localhost:{dv_agent_port}"


async def main():
    httpx_client = httpx.AsyncClient(verify=False, timeout=900)
    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
    public_card = await resolver.get_agent_card()
    logger.info("Fetched DV agent card")
    pprint.pp(public_card.model_dump())

    client = A2AClient(httpx_client=httpx_client, agent_card=public_card)
    # You can optionally pass predictions_path via metadata
    payload = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": "visualize predictions"}],
            "metadata": {"predictions_path": "./artifacts/ml_results/predictions.csv"},
            "messageId": uuid4().hex,
        }
    }

    request = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))
    response = await client.send_message(request)
    pprint.pp(response.model_dump(mode="json", exclude_none=True))
    await httpx_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
