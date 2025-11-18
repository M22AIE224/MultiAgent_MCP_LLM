# agent_main.py
import asyncio
import logging
from supervisor_agent import SupervisorAgent

# -----------------------------------------------------------------------------
# Setup Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Main async entrypoint
# -----------------------------------------------------------------------------
async def main():
    logger.info("🚀 Starting Supervisor Agent...")

    # Initialize Supervisor (factory pattern)
    supervisor = await SupervisorAgent.create()
    logger.info("✅ Supervisor Agent initialized successfully.")

    try:
        logger.info("▶️ Running pipeline execution...")
        result = await supervisor.run_pipeline()
        logger.info("🏁 Pipeline execution completed.")
        logger.info(f"Pipeline result: {result}")

    except Exception as e:
        logger.exception(f"Error during SupervisorAgent run: {e}")

    
# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Shutting down...")
