import os
import logging
import httpx
from dotenv import load_dotenv
from authentication_provider import get_http_client_based_on_authentication, get_http_client_based_on_authentication, get_default_headers_based_on_authentication
#from .agent_executor import MLAgentExecutor  # <-- Make sure this exists
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI

import json
from openai import OpenAI

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
MODEL_NAME = "gpt-4o-mini"
API_SLEEP = 0.5

with open('data/api_key.txt') as f:
    os.environ["OPENAI_API_KEY"] = f.read().strip()
    API_KEY = os.environ["OPENAI_API_KEY"] 
    
client = AsyncOpenAI(api_key=API_KEY) 

class MLAgent:
    """
    ML Agent:
    - Receives A2A request from client via MLAgentExecutor
    - Forwards to MCP_ML (FastAPI service) for training RandomForest
    """

    async def invoke(self, query: str, context_id: str):
            try:
                logger.info(f"MLAgent invoked with query='{query}' | context_id={context_id}")

               
                result = await self.call_llm(query,context_id)
                logger.info(f" LLM response from query : {result}")
                
                return {"status": "success", "source": "MCP_ML", "data": result}

            except httpx.HTTPStatusError as http_err:
                logger.error(f"HTTP error from MCP_ML: {http_err.response.text}")
                raise
                
            except Exception as e:
                logger.exception(f"MLAgent failed: {e}")
                raise

    async def call_llm(self, query: str, context_id: str):
        """
        Basic wrapper to call chat completions. Returns assistant message content.
        """
        messages = []
        try:  
            #prompt = await self.getPrompt()
            prompt = await self.getPromptMulti()
            if query:
                messages.append({"role": "system", "content": prompt})
                messages.append({"role": "user", "content": query})            

            #logger.info("OpenAI Object created")

            completion_content = await self.get_chat_completion(MODEL_NAME, messages)
       

            logger.info(f"LLM Response: {completion_content}")

            return completion_content
        
        except Exception as e:
                logger.exception(f"MLAgent failed: {e}")
                raise

    async def get_chat_completion(self, model_name, messages):
        

        logger.info("Created Async OpenAI Client")
        #client = OpenAI()  
        resp = await client.chat.completions.create(
            model=model_name,
            messages=messages
        )

       
        logger.info("Response returned")
        logger.info(resp)
        #content = resp.choices[0].message.content
        
        content = resp.choices[0].message.content

        logger.info(f"Received response: {content}")
        return content
    
    async def getModel(self):
        default_headers = get_default_headers_based_on_authentication()
        print("Pulling default headers")
        print(default_headers)


        http_client= get_http_client_based_on_authentication(httpx.Client)
        print("Pulling http_client")
        print(http_client)

        http_aclient= get_http_client_based_on_authentication(httpx.AsyncClient)
        print("Pulling http_aclient")
        print(http_aclient)

        self.model = ChatOpenAI(model=os.environ.get('DEVGENAI_MODEL'),
                                base_url=os.environ.get("OPENAI_API_BASE"),
                                api_key="",
                                http_client=http_client,
                                http_async_client=http_aclient,
                                default_headers=default_headers
                                )

        print("Model Created")

    async def getPrompt(self):
        METHOD_SELECTOR_PROMPT = """
        You are an intelligent function selector.

        Your job is to map the user's question to EXACTLY one valid method name from this list:

        - ug_curriculum
        - academic_programs
        - all_curriculum
        - academic_calendar

        RULES:
        - Output ONLY a valid method name.
        - Output MUST be a JSON object with this structure:
        {"method": "<method_name>"}
        - If the query relates to undergraduate syllabus, courses, subjects → ug_curriculum
        - If the query relates to programs, branches, degrees → academic_programs
        - If the query asks for ALL curriculum details or consolidated syllabus → all_curriculum
        - If the query relates to academic calendar dates, events, exams → academic_calendar
        - No explanation. No commentary. Only valid JSON.

        Example:
        User: "When do classes start?"
        Response: {"method": "academic_calendar"}
        """

        return METHOD_SELECTOR_PROMPT
    
    async def getPromptMulti(self):
         METHOD_SELECTOR_PROMPT = """
           You are an intelligent function selector.

            Your job is to map the user's question to one or more valid method names from this list:

            - ug_curriculum
            - academic_programs
            - all_curriculum
            - academic_calendar

            RULES:
            - You may return ONE or MULTIPLE method names.
            - If multiple methods apply, return them as a comma-separated string.
            - Output MUST be a JSON object with this structure:
            {"method": "<method_name1,method_name2,...>"}
            - Valid mapping guidelines:
            - Queries about undergraduate syllabus, courses, subjects → ug_curriculum
            - Queries about programs, branches, degrees → academic_programs
            - Queries asking for ALL curriculum details or consolidated syllabus → all_curriculum
            - Queries about academic calendar dates, events, exams → academic_calendar

            STRICT FORMATTING:
            - Output ONLY valid JSON.
            - No explanation. No commentary. No extra text.

            Example 1:
            User: "When do classes start?"
            Response: {"method": "academic_calendar"}

            Example 2:
            User: "Tell me about all curriculum and programs."
            Response: {"method": "all_curriculum,academic_programs"}
            """
         
         return  METHOD_SELECTOR_PROMPT 
