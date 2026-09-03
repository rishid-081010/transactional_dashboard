import os
import pandas as pd
import numpy as np
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

app = FastAPI(
    title="Dubai Real Estate Voice AI Intelligence API",
    description="Mid-call fast retrieval endpoint for AI Voice Agents (Retell AI, Vapi, Bland) and Brokers.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "transactions_cleaned.parquet")
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "transactions_cleaned.csv")

def get_df():
    if os.path.exists(DATA_PATH):
        return pd.read_parquet(DATA_PATH)
    elif os.path.exists(CSV_PATH):
        return pd.read_csv(CSV_PATH)
    raise FileNotFoundError("Transactions data file not found.")

df_cache = get_df()

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Dubai Real Estate Voice AI API",
        "total_records": len(df_cache)
    }

@app.get("/api/summary")
def get_summary():
    df = df_cache
    total_vol = float(df["TRANS_VALUE"].sum())
    total_deals = int(len(df))
    avg_price = float(df["TRANS_VALUE"].mean())
    med_price = float(df["TRANS_VALUE"].median())

    apts = df[df["PROPERTY_CATEGORY"] == "Apartment"]
    villas = df[df["PROPERTY_CATEGORY"] == "Villa"]

    top_loc = df.groupby("LOCATION")["TRANS_VALUE"].sum().idxmax()
    top_bhk = df[~df["BHK"].isin(["Not Specified", "Commercial Unit"])]["BHK"].value_counts().idxmax()

    offplan_cnt = int((df["MARKET_STAGE"] == "Off-Plan").sum())

    return {
        "total_volume_aed": total_vol,
        "total_volume_billions": round(total_vol / 1e9, 2),
        "total_deals": total_deals,
        "overall_average_aed": round(avg_price, 2),
        "overall_median_aed": round(med_price, 2),
        "apartment_stats": {
            "deals": len(apts),
            "average_aed": round(float(apts["TRANS_VALUE"].mean()), 2),
            "median_aed": round(float(apts["TRANS_VALUE"].median()), 2)
        },
        "villa_stats": {
            "deals": len(villas),
            "average_aed": round(float(villas["TRANS_VALUE"].mean()), 2),
            "median_aed": round(float(villas["TRANS_VALUE"].median()), 2)
        },
        "market_share": {
            "offplan_percentage": round((offplan_cnt / total_deals) * 100, 1),
            "ready_percentage": round(((total_deals - offplan_cnt) / total_deals) * 100, 1)
        },
        "top_investment_location": top_loc,
        "most_demanded_bhk": top_bhk
    }

@app.get("/api/lookup")
def lookup_market_data(
    area: Optional[str] = Query(None, description="Location name, e.g. Jumeirah Village Circle, Business Bay"),
    prop_type: Optional[str] = Query(None, description="Apartment, Villa, Commercial, Land"),
    bhk: Optional[str] = Query(None, description="Studio, 1 B/R, 2 B/R, 3 B/R, 4 B/R, 5 B/R")
):
    sub = df_cache.copy()

    if area:
        sub = sub[sub["LOCATION"].str.contains(area.strip(), case=False, na=False)]
    if prop_type and prop_type != "All":
        sub = sub[sub["PROPERTY_CATEGORY"].str.contains(prop_type.strip(), case=False, na=False)]
    if bhk and bhk != "Any BHK":
        sub = sub[sub["BHK"].str.contains(bhk.strip(), case=False, na=False)]

    count = len(sub)
    if count == 0:
        return {
            "query": {"area": area, "property_type": prop_type, "bhk": bhk},
            "found": False,
            "deal_count": 0,
            "speech": f"We do not have recent recorded transactions matching {bhk or ''} {prop_type or 'properties'} in {area or 'Dubai'}."
        }

    avg_val = float(sub["TRANS_VALUE"].mean())
    med_val = float(sub["TRANS_VALUE"].median())
    min_val = float(sub["TRANS_VALUE"].min())
    max_val = float(sub["TRANS_VALUE"].max())
    offplan_pct = float((sub["MARKET_STAGE"] == "Off-Plan").sum() / count * 100)

    area_label = area or "Dubai"
    type_label = prop_type or "residential properties"
    bhk_label = f"{bhk} " if bhk else ""

    speech = (
        f"In {area_label}, based on {count:,} recent transactions, the average price for {bhk_label}{type_label.lower()} "
        f"is approximately AED {avg_val:,.0f}, with median prices around AED {med_val:,.0f}. "
        f"Price range is from AED {min_val:,.0f} to AED {max_val:,.0f}, with {offplan_pct:.0f}% being Off-Plan."
    )

    return {
        "query": {"area": area, "property_type": prop_type, "bhk": bhk},
        "found": True,
        "deal_count": count,
        "average_aed": round(avg_val, 2),
        "median_aed": round(med_val, 2),
        "min_aed": round(min_val, 2),
        "max_aed": round(max_val, 2),
        "offplan_percentage": round(offplan_pct, 1),
        "speech": speech
    }

@app.get("/api/villas")
def get_villa_areas(limit: int = 15):
    villas = df_cache[df_cache["PROPERTY_CATEGORY"] == "Villa"]
    grp = villas.groupby("LOCATION").agg(
        deals=("TRANS_VALUE", "count"),
        average_aed=("TRANS_VALUE", "mean"),
        median_aed=("TRANS_VALUE", "median"),
        total_volume_aed=("TRANS_VALUE", "sum")
    ).sort_values("deals", ascending=False).head(limit).reset_index()

    result = []
    for _, r in grp.iterrows():
        result.append({
            "location": r["LOCATION"],
            "deals": int(r["deals"]),
            "average_aed": round(float(r["average_aed"]), 2),
            "median_aed": round(float(r["median_aed"]), 2),
            "total_volume_m": round(float(r["total_volume_aed"]) / 1e6, 2)
        })
    return {"top_villa_locations": result}

@app.get("/api/apartments")
def get_apartment_areas(limit: int = 15):
    apts = df_cache[df_cache["PROPERTY_CATEGORY"] == "Apartment"]
    grp = apts.groupby("LOCATION").agg(
        deals=("TRANS_VALUE", "count"),
        average_aed=("TRANS_VALUE", "mean"),
        median_aed=("TRANS_VALUE", "median"),
        total_volume_aed=("TRANS_VALUE", "sum")
    ).sort_values("deals", ascending=False).head(limit).reset_index()

    result = []
    for _, r in grp.iterrows():
        result.append({
            "location": r["LOCATION"],
            "deals": int(r["deals"]),
            "average_aed": round(float(r["average_aed"]), 2),
            "median_aed": round(float(r["median_aed"]), 2),
            "total_volume_m": round(float(r["total_volume_aed"]) / 1e6, 2)
        })
    return {"top_apartment_locations": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
