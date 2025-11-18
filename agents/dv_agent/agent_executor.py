# agents/dv_agent/agent_executor.py
import logging
import json
from a2a.server.agent_execution import AgentExecutor
from a2a.server.events import EventQueue
from a2a.utils import new_task, new_agent_text_message
from a2a.types import InternalError
from a2a.utils.errors import ServerError

from .dv_agent import DVAgent

logger = logging.getLogger(__name__)

class DVAgentExecutor(AgentExecutor):
    def __init__(self):
        super().__init__()
        self.agent = DVAgent()

    async def execute(self, context, event_queue: EventQueue):
        try:
            logger.info("----- DVAgentExecutor: forward A2A request to MCP_DV -----")
            query = context.get_user_input()
            task = context.current_task or new_task(context.message)
            # notify client
            #await event_queue.enqueue_event(new_agent_text_message("Starting visualization..."))

            # allow client to pass params in metadata if present
            params = {}
            # e.g., context.message.metadata could contain {"predictions_path": "..."}
            if hasattr(context.message, "metadata") and context.message.metadata:
                params = dict(context.message.metadata)

            result = await self.agent.invoke(query, task.context_id, params=params)

            if isinstance(result, dict) and result.get("type") == "html":
                result_text = result["content"]   # raw HTML
            else:
                result_text = result #json.dumps(result, indent=2)

            await event_queue.enqueue_event(new_agent_text_message(result_text))
            logger.info("----- DVAgentExecutor: visualization response streamed back -----")

        except Exception as e:
            logger.exception("DVAgentExecutor failed")
            raise ServerError(error=InternalError())

    async def cancel(self, request, event_queue: EventQueue):
        logger.info("DVAgentExecutor: cancellation requested (no-op).")
        return None
