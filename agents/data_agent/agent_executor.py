import logging
import pprint
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Task, InternalError, InvalidParamsError
from a2a.utils import new_task, new_agent_text_message
from a2a.utils.errors import ServerError
from .data_agent import DataAgent
import json

logger = logging.getLogger(__name__)

class DataAgentExecutor(AgentExecutor):
    """Executes data-related tasks for the Data MCP Agent."""

    def __init__(self):
        super().__init__()
        self.agent = DataAgent()

    async def execute(self, context, event_queue: EventQueue):
        try:
            logger.info("--------------------------------FORWARD LAYER 2 A2A REQUEST TO MCP ------------------------------")
            try:
                logger.info(f"REQUEST CONTEXT: {vars(context)}")
            except Exception:
                logger.info(f"REQUEST CONTEXT (repr): {repr(context)}")

            # Extract query safely
            query = context.get_user_input()

            # Create new task if needed
            task = context.current_task
            if not task:
                task = new_task(context.message)
                event_queue.enqueue_event(task)

            # Invoke your data agent
            result = await self.agent.invoke(query, task.context_id)

            logger.info("--------------------------------BACKWARD LAYER 2 MCP RESPONSE TO A2A -----------------------------")
            logger.info(f"RESPONSE: {result}")

            # Stream result back as A2A event
            
            result_text = json.dumps(result, indent=2)
            await event_queue.enqueue_event(new_agent_text_message(result_text))

            logger.info("--------------------------------BACKWARD LAYER 2 A2A RESPONSE TO CLIENT -----------------------------")
            logger.info("Response streamed successfully to client")

        except Exception as e:
            logger.error(f"Error executing DataAgent task: {e}", exc_info=True)
            raise ServerError(error=InternalError())

    async def cancel(self, request: RequestContext, event_queue: EventQueue):
            logger.info("Cancel requested — no active cancellation logic.")
            return None