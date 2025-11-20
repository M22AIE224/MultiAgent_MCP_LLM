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

# --- Add root directory to sys.path ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from authentication_provider import get_http_client_based_on_authentication
from .agent_executor import MLAgentExecutor  # <-- Make sure this exists

load_dotenv()

logger = logging.getLogger("ml_mcp_agent")
logging.basicConfig(level=logging.INFO)

# --- Create FastAPI app ---
app = FastAPI(title="ML MCP Agent")

@click.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=int(os.getenv("ML_AGENT_PORT", 10200)))
def main(host, port):
    """Run ML MCP Agent."""
    try:
        ml_port = port or int(os.getenv("ML_AGENT_PORT", 10200))
        mcp_ml_port = os.getenv('ML_MCP_PORT', 10020)
        mcp_url = os.getenv("ML_MCP_URL", f"http://localhost:{mcp_ml_port}")

        logger.info(f"Starting ML MCP Agent at http://localhost:{port}")
        logger.info(f"Using MCP ML Trainer at {mcp_url}")

        # --- Capabilities and skills ---
        capabilities = AgentCapabilities(streaming=False, pushNotifications=False)
        skill = AgentSkill(
            id="ml_trainer",
            name="ML Trainer MCP",
            description="Use of LLM to get data for Student.",
            tags=["ml", "mcp", "training", "modeling"],
        )

        # --- Agent metadata ---
        agent_card = AgentCard(
            name="ML MCP Agent",
            description="Use of LLM to get data for Student..",
            url=f"http://localhost:{port}/",
            version="1.0.0",
            defaultInputModes=["text/plain"],
            defaultOutputModes=["text/plain"],
            capabilities=capabilities,
            skills=[skill],
        )

        # --- HTTP client + push config ---
        http_client = get_http_client_based_on_authentication(httpx.AsyncClient)
        #httpx_client = httpx.AsyncClient
        push_config = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(http_client, config_store=push_config)

        # --- Executor and handler ---
        request_handler = DefaultRequestHandler(
            agent_executor=MLAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config,
            push_sender=push_sender,
        )


        # --- Build A2A Starlette app ---
        server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)
        a2a_app = server.build()

        # Discovery endpoint (.well-known)
        @app.get("/.well-known/agent-card.json")
        async def get_agent_card():
            """Expose agent metadata for A2A clients."""
            return agent_card

        # Simpler alias for direct access
        @app.get("/agent.json")
        async def get_agent_json():
            """Alias to agent metadata for backward compatibility."""
            return agent_card

        # Mount A2A JSON-RPC app under `/`
        app.mount("/", a2a_app)

        # --- Run server ---
        uvicorn.run(app, host=host, port=port)

    except Exception as e:
        logger.error(f"Star failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
