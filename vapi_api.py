from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import duckdb
import uvicorn
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Vapi_Backend")

app = FastAPI(title="Vapi Real Estate Webhook API")

# Define the incoming payload from Vapi
class VapiRequest(BaseModel):
    message: dict = {}

# Supabase Public Storage URLs for your Parquet files
SALES_URL = "https://qgxgtavkovqklijfpnfl.supabase.co/storage/v1/object/public/dubai_real_estate/Dubai_Sales_10_Years_Residential_Only.parquet"
RENTALS_URL = "https://qgxgtavkovqklijfpnfl.supabase.co/storage/v1/object/public/dubai_real_estate/Dubai_Rentals_10_Years_Residential_Only_zstd.parquet"

# Initialize DuckDB connection and create views so the AI can use standard table names
logger.info("Initializing DuckDB and mounting Supabase Parquet files...")
conn = duckdb.connect(database=':memory:')
# Install and load the httpfs extension to read files directly from URLs
conn.execute("INSTALL httpfs;")
conn.execute("LOAD httpfs;")

# Create views mapping to the Supabase Parquet files
conn.execute(f"CREATE OR REPLACE VIEW sales AS SELECT * FROM read_parquet('{SALES_URL}')")
conn.execute(f"CREATE OR REPLACE VIEW rentals AS SELECT * FROM read_parquet('{RENTALS_URL}')")
logger.info("Database views created successfully.")

@app.post("/vapi-query")
async def handle_vapi_query(payload: VapiRequest):
    """
    This endpoint receives the function call from Vapi.
    Vapi's LLM will generate a SQL query and send it in the tool calls.
    """
    try:
        # Extract the tool call arguments sent by Vapi
        tool_calls = payload.message.get("toolCalls", [])
        if not tool_calls:
            return {"results": [{"toolCallId": "unknown", "result": "No tool call found in request."}]}
        
        responses = []
        for call in tool_calls:
            call_id = call.get("id")
            function_args = call.get("function", {}).get("arguments", {})
            
            # The AI should pass the SQL query in a parameter called "sql_query"
            sql_query = function_args.get("sql_query")
            
            if not sql_query:
                responses.append({
                    "toolCallId": call_id,
                    "result": "Error: You did not provide a 'sql_query' argument."
                })
                continue
            
            logger.info(f"Executing SQL from Vapi: {sql_query}")
            
            try:
                # Execute the SQL directly against the DuckDB views
                result_df = conn.execute(sql_query).df()
                
                # Convert the dataframe result to a list of dictionaries (JSON)
                json_result = result_df.to_dict(orient="records")
                
                # Send the raw data back to Vapi so it can read it aloud
                responses.append({
                    "toolCallId": call_id,
                    "result": str(json_result)
                })
            except Exception as sql_err:
                logger.error(f"SQL Error: {sql_err}")
                # Return the error politely to Vapi so the AI knows it made a syntax mistake
                responses.append({
                    "toolCallId": call_id,
                    "result": f"Database Error: {str(sql_err)}. Please check your SQL syntax or column names and try again."
                })
                
        return {"results": responses}
        
    except Exception as e:
        logger.error(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run the Vapi backend on a dedicated port
    uvicorn.run(app, host="0.0.0.0", port=8002)
