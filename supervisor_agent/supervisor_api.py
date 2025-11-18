import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from .supervisor_agent import SupervisorAgent
import asyncio
from fastapi.responses import JSONResponse
import logging
app = FastAPI()

supervisor = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class Query(BaseModel):
    question: str



@app.post("/ask")
async def ask_supervisor(payload: Query):
    print("Received question:", payload.question)
    try:
        # bound the pipeline so it can't hang forever
        result = await asyncio.wait_for(supervisor.run_pipeline(payload.question), timeout=300)
        logger.info(f"Combined files : {result}")
        #print("Pipeline returned (raw):", repr(result))

    except asyncio.TimeoutError:
        print("Pipeline timed out")
        return JSONResponse({"error":"pipeline_timeout"}, status_code=504)

    except Exception as e:
        print("Exception inside pipeline:", e, type(e))
        return JSONResponse({"error":"pipeline_exception", "detail": str(e)}, status_code=500)

    # ensure the response is JSON-serializable
    try:
        if hasattr(result, "dict"):   # pydantic model
            result_to_return = result.dict()
        elif isinstance(result, (dict, list, str, int, float, bool, type(None))):
            result_to_return = result
        else:
            # fallback: stringify complex objects
            result_to_return = {"result": str(result)}
    except Exception as e:
        print("Error serializing result:", e)
        result_to_return = {"result": "unserializable_result", "raw": str(result)}

    print("Returning to client:", result_to_return)
    return JSONResponse(result_to_return)



@app.on_event("startup")
async def startup_event():
    global supervisor
    supervisor = await SupervisorAgent.create()

if __name__ == "__main__":
    uvicorn.run("supervisor_agent.supervisor_api:app", host="0.0.0.0", port=10500, reload=False)
