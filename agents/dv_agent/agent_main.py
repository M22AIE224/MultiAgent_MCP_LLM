# agents/dv_agent/agent_main.py
import os
import sys
import click
import uvicorn
import httpx
import logging
from fastapi import FastAPI
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    InMemoryTaskStore,
    InMemoryPushNotificationConfigStore,
    BasePushNotificationSender,
)
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

# add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from authentication_provider import get_http_client_based_on_authentication
from .agent_executor import DVAgentExecutor

load_dotenv()
logger = logging.getLogger("dv_agent")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="DV Agent")

@click.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=int(os.getenv("DV_AGENT_PORT", 10300)))
def main(host, port):
    try:
        logger.info(f"Starting DV Agent at http://{host}:{port}")

        capabilities = AgentCapabilities(streaming=False, pushNotifications=False)
        skill = AgentSkill(
            id="visualization",
            name="Visualization MCP",
            description="Generates plots from ML predictions and saves artifacts.",
            tags=["viz", "plots", "mcp"],
        )

        agent_card = AgentCard(
            name="DV Agent",
            description="Agent that triggers MCP_DV to create visualizations.",
            url=f"http://localhost:{port}/",
            version="1.0.0",
            defaultInputModes=["text/plain"],
            defaultOutputModes=["application/json"],
            capabilities=capabilities,
            skills=[skill],
        )

        http_client = get_http_client_based_on_authentication(httpx.AsyncClient)
        push_config = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(http_client, config_store=push_config)

        request_handler = DefaultRequestHandler(
            agent_executor=DVAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config,
            push_sender=push_sender,
        )

        server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)
        a2a_app = server.build()

        @app.get("/.well-known/agent-card.json", response_model=AgentCard)
        async def get_agent_card():
            return agent_card

        @app.get("/agent.json", response_model=AgentCard)
        async def get_agent_json():
            return agent_card

        app.mount("/", a2a_app)
        uvicorn.run(app, host=host, port=port)

    except Exception as e:
        logger.exception("DV Agent startup failed")
        raise

if __name__ == "__main__":
    main()
