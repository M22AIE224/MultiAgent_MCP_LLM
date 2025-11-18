import os
import sys
import click
import uvicorn
import httpx
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    InMemoryTaskStore,
    InMemoryPushNotificationConfigStore,
    BasePushNotificationSender,
)
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from dotenv import load_dotenv

# --- Add root directory to sys.path ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from authentication_provider import get_http_client_based_on_authentication
from .agent_executor import DataAgentExecutor

load_dotenv()

logger = logging.getLogger("data_mcp_agent")
logging.basicConfig(level=logging.INFO)

# --- Create FastAPI app ---
app = FastAPI(title="Data MCP Agent")


@click.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=int(os.getenv("DATA_AGENT_PORT", 10100)))
def main(host, port):
    """Run Data MCP Agent."""
    try:
        port = port or int(os.getenv("DATA_AGENT_PORT", 10100))
        mcp_url = os.getenv("DATA_MCP_URL", f"http://localhost:{os.getenv('DATA_MCP_PORT', 10010)}")

        logger.info(f"🚀 Starting Data MCP Agent at http://{host}:{port}")
        logger.info(f"📡 Using MCP Data Downloader at {mcp_url}")

        # --- Capabilities and skills ---
        capabilities = AgentCapabilities(streaming=False, pushNotifications=False)
        skill = AgentSkill(
            id="data_loader",
            name="Data Loader MCP",
            description="Loads data from local path or remote MCP, selects columns, and performs preprocessing.",
            tags=["data", "mcp", "feature-engineering"],
        )

        # --- Agent metadata ---
        agent_card = AgentCard(
            name="Data MCP Agent",
            description="Loads CSV data, performs feature engineering, and returns preprocessed file path.",
            url=f"http://localhost:{port}/",
            version="1.0.0",
            defaultInputModes=["text/plain"],
            defaultOutputModes=["text/plain"],
            capabilities=capabilities,
            skills=[skill],
        )

        # --- HTTP client + push config ---
        http_client = get_http_client_based_on_authentication(httpx.AsyncClient)
        push_config = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(http_client, config_store=push_config)

        # --- Executor and handler ---
        request_handler = DefaultRequestHandler(
            agent_executor=DataAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config,
            push_sender=push_sender,
        )

        # --- Build A2A Starlette app ---
        server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)
        a2a_app = server.build()

        # 1. Discovery endpoint (.well-known)
        @app.get("/.well-known/agent-card.json", response_model=AgentCard)
        async def get_agent_card():
            """Expose agent metadata for A2A clients."""
            return agent_card

        # 2. Simpler alias for direct access
        @app.get("/agent.json", response_model=AgentCard)
        async def get_agent_json():
            """Alias to agent metadata for backward compatibility."""
            return agent_card

        # 3. Mount A2A JSON-RPC app under `/`
        app.mount("/", a2a_app)

        # --- Run server ---
        uvicorn.run(app, host=host, port=port)

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
