import os
import pandas as pd
import numpy as np
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

app = FastAPI(
    title="Asquared AI - Dubai Real Estate Analytics",
    description="Executive Real Estate Intelligence Dashboard & Voice AI Engine",
    version="2.0.0"
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
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

def load_data():
    if os.path.exists(DATA_PATH):
        df = pd.read_parquet(DATA_PATH)
    elif os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
    else:
        raise FileNotFoundError("Transactions cleaned data not found.")
    df["TRANS_VALUE"] = pd.to_numeric(df["TRANS_VALUE"], errors="coerce").fillna(0.0)
    return df

df_cache = load_data()

# ─── API ENDPOINTS ───────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    df = df_cache
    total_vol = float(df["TRANS_VALUE"].sum())
    total_deals = int(len(df))
    avg_price = float(df["TRANS_VALUE"].mean())
    med_price = float(df["TRANS_VALUE"].median())
    max_deal = float(df["TRANS_VALUE"].max())

    apts = df[df["PROPERTY_CATEGORY"] == "Apartment"]
    villas = df[df["PROPERTY_CATEGORY"] == "Villa"]

    offplan_cnt = int((df["MARKET_STAGE"] == "Off-Plan").sum())
    offplan_vol = float(df[df["MARKET_STAGE"] == "Off-Plan"]["TRANS_VALUE"].sum())
    ready_vol = float(df[df["MARKET_STAGE"] == "Ready"]["TRANS_VALUE"].sum())

    days_cnt = df["DATE"].nunique()
    daily_vol = total_vol / days_cnt if days_cnt > 0 else 0
    daily_deals = total_deals / days_cnt if days_cnt > 0 else 0

    return {
        "total_volume_aed": total_vol,
        "total_volume_formatted": f"AED {total_vol / 1e9:.2f}B",
        "total_deals": total_deals,
        "total_deals_formatted": f"{total_deals:,}",
        "overall_avg_aed": round(avg_price),
        "overall_avg_formatted": f"AED {avg_price:,.0f}",
        "overall_median_aed": round(med_price),
        "overall_median_formatted": f"AED {med_price:,.0f}",
        "max_deal_aed": max_deal,
        "max_deal_formatted": f"AED {max_deal / 1e6:.1f}M",
        "apartment": {
            "deals": len(apts),
            "volume_aed": float(apts["TRANS_VALUE"].sum()),
            "avg_price": round(float(apts["TRANS_VALUE"].mean())),
            "median_price": round(float(apts["TRANS_VALUE"].median())),
            "avg_price_formatted": f"AED {apts['TRANS_VALUE'].mean():,.0f}",
            "median_price_formatted": f"AED {apts['TRANS_VALUE'].median():,.0f}"
        },
        "villa": {
            "deals": len(villas),
            "volume_aed": float(villas["TRANS_VALUE"].sum()),
            "avg_price": round(float(villas["TRANS_VALUE"].mean())),
            "median_price": round(float(villas["TRANS_VALUE"].median())),
            "avg_price_formatted": f"AED {villas['TRANS_VALUE'].mean():,.0f}",
            "median_price_formatted": f"AED {villas['TRANS_VALUE'].median():,.0f}"
        },
        "market_stage": {
            "offplan_deals": offplan_cnt,
            "ready_deals": total_deals - offplan_cnt,
            "offplan_pct": round((offplan_cnt / total_deals) * 100, 1),
            "ready_pct": round(((total_deals - offplan_cnt) / total_deals) * 100, 1),
            "offplan_volume_formatted": f"AED {offplan_vol / 1e9:.2f}B",
            "ready_volume_formatted": f"AED {ready_vol / 1e9:.2f}B"
        },
        "velocity": {
            "daily_volume_formatted": f"AED {daily_vol / 1e6:.0f}M/day",
            "daily_deals_avg": round(daily_deals),
            "days_active": days_cnt
        },
        "median_sqft": round(float(df["PRICE_PER_SQFT"].median())) if df["PRICE_PER_SQFT"].notnull().any() else 0
    }

@app.get("/api/pipeline")
def get_pipeline():
    df = df_cache
    total_deals = len(df)
    sales = len(df[df["TRANSACTION_GROUP"] == "Sales"])
    mortgage = len(df[df["TRANSACTION_GROUP"] == "Mortgage"])
    gifts = len(df[df["TRANSACTION_GROUP"] == "Gifts"])
    offplan = int((df["MARKET_STAGE"] == "Off-Plan").sum())
    ready = total_deals - offplan

    return {
        "total_deals": total_deals,
        "pure_sales": sales,
        "mortgages": mortgage,
        "gifts": gifts,
        "offplan_deals": offplan,
        "ready_deals": ready
    }

@app.get("/api/property-types")
def get_property_types():
    df = df_cache
    grp = df.groupby("PROPERTY_CATEGORY").agg(
        deals=("TRANS_VALUE", "count"),
        volume=("TRANS_VALUE", "sum"),
        avg_price=("TRANS_VALUE", "mean"),
        median_price=("TRANS_VALUE", "median")
    ).sort_values("deals", ascending=False).reset_index()

    labels = grp["PROPERTY_CATEGORY"].tolist()
    counts = grp["deals"].tolist()
    volumes = [round(v / 1e9, 2) for v in grp["volume"]]
    avg_prices = [round(p) for p in grp["avg_price"]]

    return {
        "labels": labels,
        "counts": counts,
        "volumes_b": volumes,
        "avg_prices": avg_prices
    }

@app.get("/api/top-hotspots")
def get_top_hotspots():
    df = df_cache
    # Top Projects
    proj = df[df["PROJECT"] != "Independent"].groupby(["PROJECT", "LOCATION"]).agg(
        deals=("TRANS_VALUE", "count"),
        volume=("TRANS_VALUE", "sum"),
        avg_price=("TRANS_VALUE", "mean")
    ).sort_values("volume", ascending=False).head(8).reset_index()

    results = []
    for _, r in proj.iterrows():
        results.append({
            "project": r["PROJECT"],
            "location": r["LOCATION"],
            "deals": int(r["deals"]),
            "volume_formatted": f"AED {r['volume'] / 1e6:.1f}M",
            "avg_price_formatted": f"AED {r['avg_price']:,.0f}",
            "status": "HOT" if r["deals"] > 50 else "ACTIVE"
        })
    return results

@app.get("/api/locations")
def get_locations():
    df = df_cache
    grp = df.groupby("LOCATION").apply(lambda g: pd.Series({
        "deals": len(g),
        "volume_m": round(g["TRANS_VALUE"].sum() / 1e6, 1),
        "avg_price": round(g["TRANS_VALUE"].mean()),
        "villa_avg": round(g[g["PROPERTY_CATEGORY"] == "Villa"]["TRANS_VALUE"].mean()) if len(g[g["PROPERTY_CATEGORY"] == "Villa"]) > 0 else 0,
        "apartment_avg": round(g[g["PROPERTY_CATEGORY"] == "Apartment"]["TRANS_VALUE"].mean()) if len(g[g["PROPERTY_CATEGORY"] == "Apartment"]) > 0 else 0,
        "median_sqft": round(g["PRICE_PER_SQFT"].median()) if pd.notnull(g["PRICE_PER_SQFT"].median()) else 0,
        "offplan_pct": round((g["MARKET_STAGE"] == "Off-Plan").sum() / len(g) * 100)
    }), include_groups=False).reset_index().sort_values("deals", ascending=False)

    return grp.to_dict(orient="records")

@app.get("/api/location-detail")
def get_location_detail(area: str):
    df = df_cache
    sub = df[df["LOCATION"].str.lower() == area.strip().lower()]
    if len(sub) == 0:
        return {"error": "Location not found"}

    deals = len(sub)
    volume = float(sub["TRANS_VALUE"].sum())
    avg_price = float(sub["TRANS_VALUE"].mean())
    med_price = float(sub["TRANS_VALUE"].median())
    v_sub = sub[sub["PROPERTY_CATEGORY"] == "Villa"]
    a_sub = sub[sub["PROPERTY_CATEGORY"] == "Apartment"]

    bhk_grp = sub[~sub["BHK"].isin(["Not Specified", "Commercial Unit"])].groupby("BHK").agg(
        deals=("TRANS_VALUE", "count"),
        avg_price=("TRANS_VALUE", "mean"),
        median_price=("TRANS_VALUE", "median")
    ).sort_values("deals", ascending=False).reset_index()

    top_proj = sub[sub["PROJECT"] != "Independent"].groupby("PROJECT").agg(
        deals=("TRANS_VALUE", "count"),
        volume=("TRANS_VALUE", "sum")
    ).sort_values("volume", ascending=False).head(5).reset_index()

    return {
        "location": area,
        "deals": deals,
        "volume_formatted": f"AED {volume / 1e6:.1f}M",
        "avg_price_formatted": f"AED {avg_price:,.0f}",
        "med_price_formatted": f"AED {med_price:,.0f}",
        "villa_deals": len(v_sub),
        "villa_avg_formatted": f"AED {v_sub['TRANS_VALUE'].mean():,.0f}" if len(v_sub) > 0 else "N/A",
        "apartment_deals": len(a_sub),
        "apartment_avg_formatted": f"AED {a_sub['TRANS_VALUE'].mean():,.0f}" if len(a_sub) > 0 else "N/A",
        "bhk_breakdown": [
            {
                "bhk": r["BHK"],
                "deals": int(r["deals"]),
                "avg_price_formatted": f"AED {r['avg_price']:,.0f}",
                "median_price_formatted": f"AED {r['median_price']:,.0f}"
            }
            for _, r in bhk_grp.iterrows()
        ],
        "top_projects": [
            {
                "project": r["PROJECT"],
                "deals": int(r["deals"]),
                "volume_formatted": f"AED {r['volume'] / 1e6:.1f}M"
            }
            for _, r in top_proj.iterrows()
        ]
    }

@app.get("/api/apartments-summary")
def get_apartments_summary(bhk: Optional[str] = "All", stage: Optional[str] = "All"):
    df = df_cache[df_cache["PROPERTY_CATEGORY"] == "Apartment"].copy()
    if bhk and bhk != "All":
        df = df[df["BHK"] == bhk]
    if stage and stage != "All":
        df = df[df["MARKET_STAGE"] == stage]

    count = len(df)
    volume = float(df["TRANS_VALUE"].sum())
    avg_price = float(df["TRANS_VALUE"].mean()) if count > 0 else 0
    med_price = float(df["TRANS_VALUE"].median()) if count > 0 else 0

    top_locs = df.groupby("LOCATION")["TRANS_VALUE"].agg(["count", "sum", "mean"]).sort_values("count", ascending=False).head(10).reset_index()

    return {
        "deals": count,
        "volume_formatted": f"AED {volume / 1e9:.2f}B",
        "avg_price_formatted": f"AED {avg_price:,.0f}",
        "med_price_formatted": f"AED {med_price:,.0f}",
        "top_locations": [
            {
                "location": r["LOCATION"],
                "deals": int(r["count"]),
                "avg_price_formatted": f"AED {r['mean']:,.0f}",
                "volume_formatted": f"AED {r['sum'] / 1e6:.1f}M"
            }
            for _, r in top_locs.iterrows()
        ]
    }

@app.get("/api/villas-summary")
def get_villas_summary():
    df = df_cache[df_cache["PROPERTY_CATEGORY"] == "Villa"].copy()
    top_comms = df.groupby("LOCATION").agg(
        deals=("TRANS_VALUE", "count"),
        volume=("TRANS_VALUE", "sum"),
        avg_price=("TRANS_VALUE", "mean"),
        median_price=("TRANS_VALUE", "median")
    ).sort_values("deals", ascending=False).head(15).reset_index()

    bhk_grp = df[~df["BHK"].isin(["Not Specified", "Commercial Unit"])].groupby("BHK").agg(
        deals=("TRANS_VALUE", "count"),
        avg_price=("TRANS_VALUE", "mean")
    ).sort_values("deals", ascending=False).head(5).reset_index()

    return {
        "total_deals": len(df),
        "total_volume_formatted": f"AED {df['TRANS_VALUE'].sum() / 1e9:.2f}B",
        "avg_price_formatted": f"AED {df['TRANS_VALUE'].mean():,.0f}",
        "median_price_formatted": f"AED {df['TRANS_VALUE'].median():,.0f}",
        "top_communities": [
            {
                "location": r["LOCATION"],
                "deals": int(r["deals"]),
                "avg_price_formatted": f"AED {r['avg_price']:,.0f}",
                "median_price_formatted": f"AED {r['median_price']:,.0f}",
                "volume_formatted": f"AED {r['volume'] / 1e6:.1f}M"
            }
            for _, r in top_comms.iterrows()
        ],
        "bhk_summary": [
            {
                "bhk": r["BHK"],
                "deals": int(r["deals"]),
                "avg_price_formatted": f"AED {r['avg_price']:,.0f}"
            }
            for _, r in bhk_grp.iterrows()
        ]
    }

@app.get("/api/daily-velocity")
def get_daily_velocity():
    df = df_cache.copy()
    df["DATETIME_PARSED"] = pd.to_datetime(df["DATE"])
    
    daily = df.groupby(["DATE", "DATETIME_PARSED"]).agg(
        volume=("TRANS_VALUE", "sum"),
        deals=("TRANS_VALUE", "count"),
        avg_price=("TRANS_VALUE", "mean")
    ).reset_index().sort_values("DATETIME_PARSED")
    
    daily["volume_m"] = round(daily["volume"] / 1e6, 1)
    daily["date_clean"] = daily["DATETIME_PARSED"].dt.strftime("%b %d")
    daily["date_str"] = daily["DATETIME_PARSED"].dt.strftime("%b %d, %Y")

    # Last 14 days
    last_14 = daily.tail(14)

    # Weekly Aggregation
    df["WEEK"] = df["DATETIME_PARSED"].dt.to_period("W").astype(str)
    week_map = {
        "2026-07-27/2026-08-02": "Aug 1 - 2 (W1)",
        "2026-08-03/2026-08-09": "Aug 3 - 9 (W2)",
        "2026-08-10/2026-08-16": "Aug 10 - 16 (W3)",
        "2026-08-17/2026-08-23": "Aug 17 - 23 (W4)",
        "2026-08-24/2026-08-30": "Aug 24 - 30 (W5)",
        "2026-08-31/2026-09-06": "Aug 31 - Sep 3 (W6)"
    }
    weekly = df.groupby("WEEK").agg(
        volume=("TRANS_VALUE", "sum"),
        deals=("TRANS_VALUE", "count")
    ).reset_index()
    weekly["label"] = weekly["WEEK"].map(lambda w: week_map.get(w, w))
    weekly["volume_b"] = round(weekly["volume"] / 1e9, 2)
    weekly["volume_m"] = round(weekly["volume"] / 1e6, 1)

    # Day of Week
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow = df.groupby("DAY_NAME").agg(
        volume=("TRANS_VALUE", "sum"),
        deals=("TRANS_VALUE", "count")
    ).reindex(day_order).dropna().reset_index()
    dow["volume_b"] = round(dow["volume"] / 1e9, 2)

    # Top 5 Peak Trading Days
    top_5 = daily.sort_values("volume", ascending=False).head(5)
    top_days = [
        {
            "date": r["date_str"],
            "volume_m": f"AED {r['volume_m']:.1f}M",
            "deals": int(r["deals"]),
            "avg_price": f"AED {r['avg_price']:,.0f}"
        }
        for _, r in top_5.iterrows()
    ]

    # Stats
    peak_vol_row = daily.sort_values("volume", ascending=False).iloc[0]
    peak_deals_row = daily.sort_values("deals", ascending=False).iloc[0]
    
    # Weekday vs Weekend
    is_weekend = df["DAY_NAME"].isin(["Saturday", "Sunday"])
    weekday_vol = df[~is_weekend]["TRANS_VALUE"].sum() / df[~is_weekend]["DATE"].nunique()
    weekend_vol = df[is_weekend]["TRANS_VALUE"].sum() / max(1, df[is_weekend]["DATE"].nunique())

    return {
        "daily": {
            "dates": daily["date_clean"].tolist(),
            "raw_dates": daily["date_str"].tolist(),
            "volumes_m": daily["volume_m"].tolist(),
            "deals": daily["deals"].tolist()
        },
        "last_14": {
            "dates": last_14["date_clean"].tolist(),
            "raw_dates": last_14["date_str"].tolist(),
            "volumes_m": last_14["volume_m"].tolist(),
            "deals": last_14["deals"].tolist()
        },
        "weekly": {
            "labels": weekly["label"].tolist(),
            "volumes_b": weekly["volume_b"].tolist(),
            "volumes_m": weekly["volume_m"].tolist(),
            "deals": weekly["deals"].tolist()
        },
        "dow": {
            "labels": dow["DAY_NAME"].tolist(),
            "volumes_b": dow["volume_b"].tolist(),
            "deals": dow["deals"].tolist()
        },
        "top_days": top_days,
        "stats": {
            "avg_daily_vol": f"AED {daily['volume'].mean() / 1e6:.0f}M",
            "peak_vol_date": peak_vol_row["date_str"],
            "peak_vol_amount": f"AED {peak_vol_row['volume'] / 1e9:.2f}B",
            "peak_deals_date": peak_deals_row["date_str"],
            "peak_deals_count": f"{int(peak_deals_row['deals']):,} deals",
            "weekday_avg": f"AED {weekday_vol / 1e9:.2f}B / day",
            "weekend_avg": f"AED {weekend_vol / 1e6:.0f}M / day"
        }
    }

@app.get("/api/live-stream")
def get_live_stream(limit: int = 15):
    df = df_cache
    recent = df.sort_values("DATETIME", ascending=False).head(limit)
    logs = []
    for _, r in recent.iterrows():
        dt_str = str(r["DATETIME"])
        time_part = dt_str.split(" ")[1][:8] if " " in dt_str else dt_str
        logs.append({
            "time": time_part,
            "date": str(r["DATE"]),
            "trans_no": str(r["TRANSACTION_NUMBER"]),
            "location": str(r["LOCATION"]),
            "type": str(r["PROPERTY_CATEGORY"]),
            "bhk": str(r["BHK"]),
            "stage": str(r["MARKET_STAGE"]),
            "value_formatted": f"AED {float(r['TRANS_VALUE']):,.0f}",
            "project": str(r["PROJECT"]) if r["PROJECT"] != "Independent" else "Residential Unit"
        })
    return logs

@app.get("/api/lookup")
def lookup_market_data(
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    bhk: Optional[str] = Query(None)
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
            "found": False,
            "deal_count": 0,
            "speech": f"No recent closed transactions recorded matching {bhk or ''} {prop_type or 'properties'} in {area or 'Dubai'}."
        }

    avg_val = float(sub["TRANS_VALUE"].mean())
    med_val = float(sub["TRANS_VALUE"].median())
    min_val = float(sub["TRANS_VALUE"].min())
    max_val = float(sub["TRANS_VALUE"].max())
    offplan_pct = float((sub["MARKET_STAGE"] == "Off-Plan").sum() / count * 100)

    speech = (
        f"In {area or 'Dubai'}, based on {count:,} recent transactions, the average price for {bhk or ''} {prop_type or 'residential units'} "
        f"is approximately AED {avg_val:,.0f}, with median pricing around AED {med_val:,.0f}. "
        f"Prices range from AED {min_val:,.0f} to AED {max_val:,.0f}, with {offplan_pct:.0f}% being Off-Plan."
    )

    return {
        "found": True,
        "deal_count": count,
        "average_formatted": f"AED {avg_val:,.0f}",
        "median_formatted": f"AED {med_val:,.0f}",
        "offplan_pct": round(offplan_pct, 1),
        "speech": speech
    }

@app.get("/api/all-transactions")
def get_all_transactions():
    json_path = os.path.join(BASE_DIR, "api", "all_transactions.json")
    if os.path.exists(json_path):
        return FileResponse(json_path, media_type="application/json")
    return []

# ─── SERVE FRONTEND ──────────────────────────────────────────────────────────
@app.get("/")
async def read_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
