import asyncio
import logging
import pprint
import os 
import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest
from uuid import uuid4
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


ml_agent_port = os.getenv("ML_AGENT_PORT", "10200")
base_url = f"http://localhost:{ml_agent_port}"


async def main():
    httpx_client = httpx.AsyncClient(verify=False, timeout=900)
    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
    public_card = await resolver.get_agent_card()

    client = A2AClient(httpx_client=httpx_client, agent_card=public_card)
    payload = {
        "message": {
            "role": "user",
            "parts": [
                {"kind": "text", "text": "train random forest model on processed data"}
            ],
            "metadata": {"action": "train", "params": {"squared": False}},
            "messageId": uuid4().hex,
        }
    }

    request = SendMessageRequest(
        id=str(uuid4()), params=MessageSendParams(**payload)
    )
    response = await client.send_message(request)
    pprint.pp(response.model_dump(mode="json", exclude_none=True))

if __name__ == "__main__":
    asyncio.run(main())
