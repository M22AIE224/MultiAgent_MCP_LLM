import asyncio
import json
from data_agent import DataAgent
import pprint
from a2a.types import Role
print(list(Role))

async def main():
    agent = DataAgent()
    
    # Example query (this matches your parser logic)
    #query = "LOAD COLUMNS=age,income; TARGET=label"
    query = "LOAD path=./data/source_data.csv;COLUMNS=age,income;TARGET=target_col;SAVE=./processed/processed_data.csv"

    #query = "LOAD path=./data/source_data.csv;COLUMNS=col1,col2;TARGET=target_col;SAVE=./processed/processed_data.csv"

    print("🔍 Running DataAgent with query:", query)
    
    result = await agent.invoke(query, context_id="test123")
    print("\n✅ DataAgent Output JSON:")
    #print(json.dumps(json.loads(result), indent=2))
  
    pprint.pprint(result)

if __name__ == "__main__":
    asyncio.run(main())
