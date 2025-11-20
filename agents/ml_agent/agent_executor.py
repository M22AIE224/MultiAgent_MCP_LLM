import logging
import json
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import InternalError

from a2a.utils import new_task, new_agent_text_message
from a2a.utils.errors import ServerError
from .ml_agent import MLAgent

logger = logging.getLogger(__name__)

class MLAgentExecutor(AgentExecutor):
    """Executes ML training tasks via the ML MCP service."""

    def __init__(self):
        super().__init__()
        self.agent = MLAgent()

    async def execute_bkp(self, context: RequestContext, event_queue: EventQueue):
        try:
            logger.info("----------- FORWARD LAYER 2: A2A REQUEST → MCP (ML) -----------")
            logger.info(f"REQUEST CONTEXT: {vars(context)}")

            query = context.get_user_input()
            logger.info(f"User Query in ML Agent Execute Start: {query}")

            task = context.current_task
            if not task:
                task = new_task(context.message)
                event_queue.enqueue_event(task)

           
            # Optionally notify client that training has started
            #await event_queue.enqueue_event(new_agent_text_message("Starting ML training..."))

            # Invoke your data agent
            result = await self.agent.invoke(query, task.context_id)

            logger.info("----------- BACKWARD LAYER 2: MCP RESPONSE → A2A (ML) -----------")
            logger.info(f"RESPONSE: {json.dumps(result, indent=2)}")

            if not isinstance(result, str):
                result = json.dumps(result, indent=2)

            await event_queue.enqueue_event(new_agent_text_message(result))
            logger.info("Response streamed successfully to client (ML).")

        except Exception as e:
            logger.error(f"Error executing MLAgent task: {e}", exc_info=True)
            raise ServerError(error=InternalError())

    #
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        try:
            logger.info("----------- FORWARD LAYER 2: A2A REQUEST → MCP (ML) -----------")
            logger.info(f"REQUEST CONTEXT: {vars(context)}")

            query = context.get_user_input()
            logger.info(f"User Query in ML Agent Execute Start: {query}")

            task = context.current_task
            if not task:
                task = new_task(context.message)
                event_queue.enqueue_event(task)

           
            # Optionally notify client that training has started
            #await event_queue.enqueue_event(new_agent_text_message("Starting ML training..."))

            # Invoke your data agent
            result = await self.agent.invoke(query, task.context_id)

            logger.info("----------- BACKWARD LAYER 2: MCP RESPONSE → A2A (ML) -----------")
            logger.info(f"RESPONSE: {json.dumps(result, indent=2)}")

            if not isinstance(result, str):
                result = json.dumps(result, indent=2)

            await event_queue.enqueue_event(new_agent_text_message(result))
            logger.info("Response streamed successfully to client (ML).")

        except Exception as e:
            logger.error(f"Error executing MLAgent task: {e}", exc_info=True)
            raise ServerError(error=InternalError())

    async def cancel(self, request: RequestContext, event_queue: EventQueue):
        logger.info("Cancel requested — no active cancellation logic for ML Agent.")
        return None

