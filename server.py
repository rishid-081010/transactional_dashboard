from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import duckdb
import uvicorn
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

class VapiRequest(BaseModel):
    message: dict = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Public Storage URLs for your Parquet files
SALES_URL = "https://qgxgtavkovqklijfpnfl.supabase.co/storage/v1/object/public/dubai_real_estate/Dubai_Sales_10_Years_Residential_Only.parquet"
RENTALS_URL = "https://qgxgtavkovqklijfpnfl.supabase.co/storage/v1/object/public/dubai_real_estate/Dubai_Rentals_10_Years_Residential_Only_zstd.parquet"

# Initialize a global DuckDB connection for speed
conn = duckdb.connect(database=':memory:')
conn.execute("INSTALL httpfs;")
conn.execute("LOAD httpfs;")
conn.execute(f"CREATE OR REPLACE VIEW sales AS SELECT * FROM read_parquet('{SALES_URL}')")
conn.execute(f"CREATE OR REPLACE VIEW rentals AS SELECT * FROM read_parquet('{RENTALS_URL}')")

def query_db(query, dataset="sales"):
    # Since views are already created, we just run the query directly
    # Ensure the query references the correct view if it doesn't already
    if "FROM sales" not in query.upper() and "FROM rentals" not in query.upper():
        query = query.replace("FROM data", f"FROM {dataset}")
        
    result = conn.execute(query).df()
    return result.fillna(0)

@app.get("/api/dashboard")
def get_dashboard_kpis(dataset: str = "sales"):
    q = """
    SELECT 
        COUNT(*) as total_deals,
        SUM(price) as total_volume,
        AVG(price) as avg_deal,
        MEDIAN(price) as median_deal,
        SUM(CASE WHEN property_sub_type IN ('Flat', 'Hotel Apartment') THEN 1 ELSE 0 END) as apt_deals,
        AVG(CASE WHEN property_sub_type IN ('Flat', 'Hotel Apartment') THEN price ELSE NULL END) as apt_avg_price,
        SUM(CASE WHEN property_sub_type = 'Villa' THEN 1 ELSE 0 END) as villa_deals,
        AVG(CASE WHEN property_sub_type = 'Villa' THEN price ELSE NULL END) as villa_avg_price
    FROM sales
    """
    df = query_db(q, dataset)
    if df.empty:
        return {}
    df = df.fillna(0)
    total_deals = int(df['total_deals'].iloc[0] if not df.empty else 0)
    total_vol = float(df['total_volume'].iloc[0] if not df.empty else 0)
    
    # Dynamics (mocked logic for now to match UI design splits)
    pure_sales = int(total_deals * 0.75) if dataset == 'sales' else int(total_deals * 0.95)
    mortgage = total_deals - pure_sales
    off_plan = int(total_deals * 0.52) if dataset == 'sales' else int(total_deals * 0.1)
    ready = total_deals - off_plan

    return {
        "kpis": {
            "total_volume": total_vol,
            "total_deals": total_deals,
            "avg_deal": float(df['avg_deal'].iloc[0] if not df.empty else 0),
            "median_deal": float(df['median_deal'].iloc[0] if not df.empty else 0),
            "apartment_avg": float(df['apt_avg_price'].iloc[0] if not df.empty else 0),
            "apartment_deals": int(df['apt_deals'].iloc[0] if not df.empty else 0),
            "villa_avg": float(df['villa_avg_price'].iloc[0] if not df.empty else 0),
            "villa_deals": int(df['villa_deals'].iloc[0] if not df.empty else 0),
            "off_plan_share_pct": 52.1 if dataset == 'sales' else 10.0,
            "off_plan_inflow": total_vol * (0.521 if dataset == 'sales' else 0.10)
        },
        "dynamics": {
            "total_recorded": total_deals,
            "pure_sales": pure_sales,
            "mortgage": mortgage,
            "off_plan": off_plan,
            "ready": ready
        }
    }

@app.get("/api/dashboard/hotspots")
def get_hotspots(dataset: str = "sales"):
    df = query_db("SELECT project as project_name, area as master_location, COUNT(*) as deals, AVG(price) as avg_ticket, SUM(price) as total_inflow FROM sales WHERE project IS NOT NULL AND project != 'nan' GROUP BY project, area ORDER BY total_inflow DESC LIMIT 5", dataset)
    return df.to_dict(orient="records")

@app.get("/api/apartments")
def get_apartments(bhk: str = 'all', dataset: str = "sales", usage: str = 'all'):
    bhk_filter = ""
    if bhk != 'all':
        if bhk == '0':
            bhk_filter = "AND (CAST(bedrooms AS VARCHAR) = '0' OR CAST(bedrooms AS VARCHAR) ILIKE 'studio%')"
        elif bhk == '4':
            bhk_filter = "AND (CAST(bedrooms AS VARCHAR) >= '4' OR CAST(bedrooms AS VARCHAR) LIKE '4%' OR CAST(bedrooms AS VARCHAR) LIKE '5%' OR CAST(bedrooms AS VARCHAR) LIKE '6%')"
        else:
            bhk_filter = f"AND (CAST(bedrooms AS VARCHAR) = '{bhk}' OR CAST(bedrooms AS VARCHAR) LIKE '{bhk} %')"
    usage_filter = ""
    if usage != 'all':
        usage_filter = f"AND usage = '{usage.replace(chr(39), chr(39)*2)}'"
    df_kpis = query_db(f"SELECT COUNT(*) as total_deals, SUM(price) as total_volume, AVG(price) as avg_deal, MEDIAN(price) as median_deal, MEDIAN(price / NULLIF(size_sqft, 0)) as median_sqft, MEDIAN(size_sqft) as median_space FROM sales WHERE property_sub_type IN ('Flat', 'Hotel Apartment') {bhk_filter} {usage_filter}", dataset)
    df_locations = query_db(f"SELECT area, COUNT(*) as deals, AVG(price) as avg_ticket, SUM(price) as total_inflow FROM sales WHERE property_sub_type IN ('Flat', 'Hotel Apartment') {bhk_filter} {usage_filter} GROUP BY area ORDER BY total_inflow DESC LIMIT 10", dataset)
    return {
        "kpis": {
            "total_deals": int(df_kpis['total_deals'][0]), "total_volume": float(df_kpis['total_volume'][0] or 0),
            "avg_deal": float(df_kpis['avg_deal'][0] or 0), "median_deal": float(df_kpis['median_deal'][0] or 0),
            "median_sqft": float(df_kpis['median_sqft'][0] or 0), "median_space": float(df_kpis['median_space'][0] or 0)
        },
        "locations": df_locations.to_dict(orient="records")
    }

@app.get("/api/villas")
def get_villas(dataset: str = "sales", usage: str = 'all'):
    usage_filter = ""
    if usage != 'all':
        usage_filter = f"AND usage = '{usage.replace(chr(39), chr(39)*2)}'"
    df_kpis = query_db(f"SELECT COUNT(*) as total_deals, SUM(price) as total_volume, AVG(price) as avg_deal, MEDIAN(price) as median_deal, MEDIAN(price / NULLIF(size_sqft, 0)) as median_sqft, MEDIAN(size_sqft) as median_space FROM sales WHERE property_sub_type = 'Villa' {usage_filter}", dataset)
    df_communities = query_db(f"SELECT area as community, COUNT(*) as villas_sold, AVG(price) as avg_price, MEDIAN(price) as median_price, SUM(price) as total_inflow FROM sales WHERE property_sub_type = 'Villa' {usage_filter} GROUP BY area ORDER BY total_inflow DESC LIMIT 15", dataset)
    return {
        "kpis": {
            "total_deals": int(df_kpis['total_deals'][0]), "total_volume": float(df_kpis['total_volume'][0] or 0),
            "avg_deal": float(df_kpis['avg_deal'][0] or 0), "median_deal": float(df_kpis['median_deal'][0] or 0),
            "median_sqft": float(df_kpis['median_sqft'][0] or 0), "median_space": float(df_kpis['median_space'][0] or 0)
        },
        "communities": df_communities.to_dict(orient="records")
    }

@app.get("/api/locations/areas")
def get_all_areas(dataset: str = "sales"):
    df = query_db("SELECT DISTINCT area FROM sales WHERE area IS NOT NULL AND area != 'nan' ORDER BY area ASC", dataset)
    return [row['area'] for _, row in df.iterrows()]

@app.get("/api/locations")
def get_location_data(area: str = 'Dubai Marina', dataset: str = "sales"):
    df_kpis = query_db(f"""
        SELECT 
            COUNT(*) as total_deals, SUM(price) as total_volume, AVG(price) as avg_deal, MEDIAN(price) as median_deal,
            SUM(CASE WHEN property_sub_type = 'Villa' THEN 1 ELSE 0 END) as villa_deals,
            AVG(CASE WHEN property_sub_type = 'Villa' THEN price ELSE NULL END) as villa_avg,
            SUM(CASE WHEN property_sub_type IN ('Flat', 'Hotel Apartment') THEN 1 ELSE 0 END) as apt_deals,
            AVG(CASE WHEN property_sub_type IN ('Flat', 'Hotel Apartment') THEN price ELSE NULL END) as apt_avg
        FROM sales WHERE area = '{area.replace("'", "''")}'
    """, dataset)
    df_bhk = query_db(f"""
        SELECT bedrooms as bhk_type, COUNT(*) as deals, AVG(price) as avg_price, MEDIAN(price) as median_price 
        FROM sales WHERE area = '{area.replace("'", "''")}' AND property_sub_type IN ('Flat', 'Hotel Apartment') 
        GROUP BY bedrooms ORDER BY bedrooms ASC LIMIT 6
    """, dataset)
    df_projects = query_db(f"""
        SELECT project as project_name, COUNT(*) as transactions, SUM(price) as total_inflow 
        FROM sales WHERE area = '{area.replace("'", "''")}' AND project IS NOT NULL AND project != 'nan' 
        GROUP BY project ORDER BY total_inflow DESC LIMIT 5
    """, dataset)
    df_all_areas = query_db("""
        SELECT area as community, COUNT(*) as deals, SUM(price) as total_volume, AVG(price) as overall_avg,
        AVG(CASE WHEN property_sub_type = 'Villa' THEN price ELSE NULL END) as villa_avg,
        AVG(CASE WHEN property_sub_type IN ('Flat', 'Hotel Apartment') THEN price ELSE NULL END) as apt_avg,
        AVG(price / NULLIF(size_sqft, 0)) as rate_sqft
        FROM sales GROUP BY area ORDER BY total_volume DESC LIMIT 50
    """, dataset)
    return {
        "kpis": {
            "total_deals": int(df_kpis['total_deals'][0]), "total_volume": float(df_kpis['total_volume'][0] or 0),
            "avg_deal": float(df_kpis['avg_deal'][0] or 0), "median_deal": float(df_kpis['median_deal'][0] or 0),
            "villa_avg": float(df_kpis['villa_avg'][0] or 0), "villa_deals": int(df_kpis['villa_deals'][0] or 0),
            "apt_avg": float(df_kpis['apt_avg'][0] or 0), "apt_deals": int(df_kpis['apt_deals'][0] or 0)
        },
        "bhk_breakdown": df_bhk.to_dict(orient="records"),
        "top_projects": df_projects.to_dict(orient="records"),
        "all_areas": df_all_areas.to_dict(orient="records")
    }

@app.get("/api/property-types")
def get_property_types(dataset: str = "sales"):
    q = """
    SELECT 
        CASE 
            WHEN property_sub_type IN ('Flat', 'Hotel Apartment') THEN 'Apartment'
            WHEN property_sub_type = 'Villa' THEN 'Villa'
            WHEN usage = 'Commercial' THEN 'Commercial'
            ELSE 'Land/Building'
        END as asset_class,
        COUNT(*) as deals_closed,
        SUM(price) as total_capital,
        AVG(price) as avg_ticket
    FROM sales
    GROUP BY asset_class
    ORDER BY total_capital DESC
    """
    df = query_db(q, dataset)
    return df.to_dict(orient="records")
@app.get("/api/velocity")
def get_velocity(dataset: str = "sales"):
    # Note: DuckDB CAST to DATE for grouping
    q_daily = """
    SELECT 
        CAST(transaction_date AS DATE) as tx_date,
        COUNT(*) as deals,
        SUM(price) as volume,
        AVG(price) as avg_ticket,
        DAYOFWEEK(CAST(transaction_date AS DATE)) as dow
    FROM sales
    WHERE transaction_date IS NOT NULL
    GROUP BY tx_date
    ORDER BY tx_date DESC
    LIMIT 60
    """
    df = query_db(q_daily, dataset)
    if df.empty: return {}

    avg_pace = float(df['volume'].mean())
    avg_deals = int(df['deals'].mean())
    
    peak_vol_idx = df['volume'].idxmax()
    peak_deals_idx = df['deals'].idxmax()
    
    weekend_mask = df['dow'].isin([0, 6]) # 0=Sun, 6=Sat in DuckDB
    weekday_mask = ~weekend_mask
    weekend_avg = float(df[weekend_mask]['volume'].mean() if len(df[weekend_mask]) else 0)
    weekday_avg = float(df[weekday_mask]['volume'].mean() if len(df[weekday_mask]) else 0)
    
    top_5_days = df.nlargest(5, 'volume').copy()
    top_5_days['tx_date'] = top_5_days['tx_date'].astype(str)

    weekly_q = """
    SELECT 
        DATE_TRUNC('week', CAST(transaction_date AS DATE)) as week_start,
        COUNT(*) as deals,
        SUM(price) as volume
    FROM sales
    WHERE transaction_date IS NOT NULL
    GROUP BY week_start
    ORDER BY week_start DESC
    LIMIT 5
    """
    df_weekly = query_db(weekly_q, dataset)
    df_weekly['week_start'] = df_weekly['week_start'].astype(str)

    return {
        "kpis": {
            "avg_daily_pace": avg_pace,
            "avg_daily_deals": avg_deals,
            "peak_capital": float(df.loc[peak_vol_idx, 'volume']),
            "peak_capital_date": str(df.loc[peak_vol_idx, 'tx_date']),
            "peak_deals": int(df.loc[peak_deals_idx, 'deals']),
            "peak_deals_date": str(df.loc[peak_deals_idx, 'tx_date']),
            "weekday_avg": weekday_avg,
            "weekend_avg": weekend_avg
        },
        "weekly_flow": df_weekly.to_dict(orient="records"),
        "top_days": top_5_days.to_dict(orient="records")
    }

@app.get("/api/voice")
def get_voice_logs():
    # Simulate Vapi logs for UI
    import random
    from datetime import datetime, timedelta
    
    logs = []
    now = datetime.now()
    for i in range(15):
        t = now - timedelta(minutes=random.randint(1, 1000))
        logs.append({
            "timestamp": t.strftime("%d/%m/%Y, %H:%M:%S"),
            "event": "Webhook Received",
            "latency": f"{random.randint(120, 250)}ms"
        })
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return logs

@app.get("/api/transactions")
def get_transactions(dataset: str = "sales", page: int = 1, limit: int = 50, search: str = "", prop_type: str = "all", usage: str = "all", sort: str = "date_desc", price_tier: str = "all"):
    offset = (page - 1) * limit
    
    conditions = []
    if search:
        s = search.replace("'", "''").lower()
        conditions.append(f"(LOWER(project) LIKE '%{s}%' OR LOWER(area) LIKE '%{s}%')")
    if prop_type == 'apartment':
        conditions.append("property_sub_type IN ('Flat', 'Hotel Apartment')")
    elif prop_type == 'villa':
        conditions.append("property_sub_type = 'Villa'")
    elif prop_type == 'commercial':
        conditions.append("usage = 'Commercial'")
    elif prop_type == 'land':
        conditions.append("property_type IN ('Land', 'Building')")
    if usage != 'all':
        conditions.append(f"usage = '{usage.replace(chr(39), chr(39)*2)}'")
    if price_tier == 'under1m':
        conditions.append("price < 1000000")
    elif price_tier == '1m5m':
        conditions.append("price >= 1000000 AND price < 5000000")
    elif price_tier == '5m10m':
        conditions.append("price >= 5000000 AND price < 10000000")
    elif price_tier == 'above10m':
        conditions.append("price >= 10000000")
    
    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    
    order = "transaction_date DESC"
    if sort == "price_desc":
        order = "price DESC"
    elif sort == "price_asc":
        order = "price ASC"
    elif sort == "date_asc":
        order = "transaction_date ASC"
    
    # Get count and summary
    count_q = f"SELECT COUNT(*) as cnt, COALESCE(SUM(price),0) as vol, COALESCE(AVG(price),0) as avg_price FROM sales {where_clause}"
    df_count = query_db(count_q, dataset)
    total_deals = int(df_count['cnt'][0])
    total_vol = float(df_count['vol'][0])
    avg_price = float(df_count['avg_price'][0])
        
    q = f"""
    SELECT 
        transaction_date as date_time,
        area as community,
        project,
        property_sub_type as type,
        bedrooms,
        usage as stage,
        price
    FROM sales
    {where_clause}
    ORDER BY {order}
    LIMIT {limit} OFFSET {offset}
    """
    df = query_db(q, dataset)
    
    return {
        "total": total_deals,
        "total_volume": total_vol,
        "avg_price": avg_price,
        "page": page,
        "limit": limit,
        "data": df.fillna("").to_dict(orient="records")
    }

@app.get("/api/scraper/status")
def get_scraper_status():
    import os, json
    status_file = "data/scraper_status.json"
    if os.path.exists(status_file):
        try:
            with open(status_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "status": "Offline / Waiting for heartbeat...",
        "last_ping_time": None,
        "next_ping_time": None,
        "latest_rental": None,
        "latest_sale": None,
        "total_rentals_session": 0,
        "total_sales_session": 0
    }


@app.get("/")
def serve_dashboard():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/{filename:path}")
def serve_static(filename: str):
    filepath = os.path.join(BASE_DIR, filename)
    if os.path.isfile(filepath):
        return FileResponse(filepath)
    return {"detail": "Not Found"}


@app.post("/vapi-query")
async def handle_vapi_query(payload: VapiRequest):
    try:
        tool_calls = payload.message.get("toolCalls", [])
        if not tool_calls:
            return {"results": [{"toolCallId": "unknown", "result": "No tool call found in request."}]}
        
        responses = []
        for call in tool_calls:
            call_id = call.get("id")
            function_args = call.get("function", {}).get("arguments", {})
            sql_query = function_args.get("sql_query")
            
            if not sql_query:
                responses.append({"toolCallId": call_id, "result": "Error: Missing sql_query argument."})
                continue
            
            print(f"\n[VAPI INTERCEPT] AI asked SQL Query: {sql_query}")
            
            try:
                result_df = conn.execute(sql_query).df()
                json_result = result_df.to_dict(orient="records")
                print(f"[VAPI INTERCEPT] Database returned: {json_result}\n")
                responses.append({"toolCallId": call_id, "result": str(json_result)})
            except Exception as sql_err:
                responses.append({"toolCallId": call_id, "result": f"Database Error: {str(sql_err)}"})
                
        return {"results": responses}
    except Exception as e:
        return {"results": [{"toolCallId": "unknown", "result": f"Server Error: {str(e)}"}]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
