import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="Dubai Real Estate Analytics | Executive Master Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Executive CSS with high-density metrics styling
st.markdown("""
<style>
    .main { background-color: #0b1120; }
    .kpi-card {
        background: #1e293b;
        padding: 14px 18px;
        border-radius: 10px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.25);
        margin-bottom: 10px;
    }
    .kpi-card-highlight {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 14px 18px;
        border-radius: 10px;
        border: 1px solid #38bdf8;
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.15);
        margin-bottom: 10px;
    }
    .kpi-title { font-size: 0.75rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
    .kpi-val { font-size: 1.55rem; font-weight: 700; color: #f8fafc; line-height: 1.2; }
    .kpi-sub { font-size: 0.78rem; color: #38bdf8; margin-top: 4px; }
    .gold-accent { color: #f59e0b; }
    .emerald-accent { color: #10b981; }
    .purple-accent { color: #a855f7; }
    .card-box {
        background: #1e293b;
        border-radius: 10px;
        padding: 18px 22px;
        border: 1px solid #334155;
        margin-bottom: 16px;
    }
    .voice-bubble {
        background: #0284c7;
        color: white;
        padding: 14px 18px;
        border-radius: 14px 14px 14px 2px;
        margin-bottom: 12px;
        font-weight: 500;
        font-size: 0.95rem;
    }
    .voice-response {
        background: #1e293b;
        color: #f1f5f9;
        padding: 16px 20px;
        border-radius: 14px 14px 2px 14px;
        margin-bottom: 18px;
        border-left: 4px solid #38bdf8;
        font-size: 0.95rem;
        line-height: 1.55;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    parquet_path = os.path.join(os.path.dirname(__file__), "data", "transactions_cleaned.parquet")
    csv_path = os.path.join(os.path.dirname(__file__), "data", "transactions_cleaned.csv")
    if os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
    elif os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        st.error("Cleaned transaction data not found. Please run data_prep.py first.")
        st.stop()
    
    df["DATE"] = pd.to_datetime(df["DATE"]).dt.date
    return df

df_raw = load_data()

# ─── SIDEBAR GLOBAL FILTERS ──────────────────────────────────────────────────
st.sidebar.title("🏢 Dubai Real Estate")
st.sidebar.caption("Executive Analytical Dashboard")

min_date = df_raw["DATE"].min()
max_date = df_raw["DATE"].max()

st.sidebar.subheader("📅 Date Window (Day-by-Day)")
date_selection = st.sidebar.date_input(
    "Filter by Transaction Date",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_selection, (tuple, list)) and len(date_selection) == 2:
    start_date, end_date = date_selection
else:
    start_date, end_date = min_date, max_date

# Category Filter
all_categories = sorted(df_raw["PROPERTY_CATEGORY"].unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Property Types",
    options=all_categories,
    default=all_categories
)

# Market Stage (Off-plan vs Ready)
all_stages = ["All"] + sorted(df_raw["MARKET_STAGE"].unique().tolist())
selected_stage = st.sidebar.selectbox("Market Stage", all_stages, index=0)

# Transaction Group (Sales, Mortgage, Gifts)
all_groups = ["All"] + sorted(df_raw["TRANSACTION_GROUP"].unique().tolist())
selected_group = st.sidebar.selectbox("Transaction Group", all_groups, index=0)

# Location multi-select
all_locations = sorted(df_raw["LOCATION"].unique().tolist())
selected_locations = st.sidebar.multiselect(
    "Filter Specific Locations",
    options=all_locations,
    default=[]
)

# Apply Global Filters
mask = (
    (df_raw["DATE"] >= start_date) &
    (df_raw["DATE"] <= end_date) &
    (df_raw["PROPERTY_CATEGORY"].isin(selected_categories))
)

if selected_stage != "All":
    mask = mask & (df_raw["MARKET_STAGE"] == selected_stage)

if selected_group != "All":
    mask = mask & (df_raw["TRANSACTION_GROUP"] == selected_group)

if selected_locations:
    mask = mask & (df_raw["LOCATION"].isin(selected_locations))

df = df_raw[mask].copy()

# ─── HEADER ──────────────────────────────────────────────────────────────────
st.title("🏙️ Dubai Real Estate Transaction Intelligence")
st.markdown(f"**Period:** `{start_date}` to `{end_date}` | **Dataset:** `{len(df):,}` transactions displayed ({len(df)/len(df_raw)*100:.1f}% of total database)")

# ─── EXPANDED EXECUTIVE KPI MATRIX (10 KEY METRICS) ──────────────────────────
total_volume = df["TRANS_VALUE"].sum()
total_count = len(df)
overall_avg = df["TRANS_VALUE"].mean() if total_count > 0 else 0
overall_median = df["TRANS_VALUE"].median() if total_count > 0 else 0
max_deal = df["TRANS_VALUE"].max() if total_count > 0 else 0

# Apartment Metrics
apt_df = df[df["PROPERTY_CATEGORY"] == "Apartment"]
apt_vol = apt_df["TRANS_VALUE"].sum()
apt_avg = apt_df["TRANS_VALUE"].mean() if len(apt_df) > 0 else 0
apt_median = apt_df["TRANS_VALUE"].median() if len(apt_df) > 0 else 0
apt_sqft = apt_df["PRICE_PER_SQFT"].median() if len(apt_df) > 0 else 0

# Villa Metrics
villa_df = df[df["PROPERTY_CATEGORY"] == "Villa"]
villa_vol = villa_df["TRANS_VALUE"].sum()
villa_avg = villa_df["TRANS_VALUE"].mean() if len(villa_df) > 0 else 0
villa_median = villa_df["TRANS_VALUE"].median() if len(villa_df) > 0 else 0
villa_sqft = villa_df["PRICE_PER_SQFT"].median() if len(villa_df) > 0 else 0

# Market Velocity Metrics
days_active = df["DATE"].nunique()
daily_avg_vol = (total_volume / days_active) if days_active > 0 else 0
daily_avg_deals = (total_count / days_active) if days_active > 0 else 0

# Off-Plan vs Ready
offplan_count = len(df[df["MARKET_STAGE"] == "Off-Plan"])
offplan_vol = df[df["MARKET_STAGE"] == "Off-Plan"]["TRANS_VALUE"].sum()
offplan_pct = (offplan_count / total_count * 100) if total_count > 0 else 0

# Overall SqFt
median_sqft = df["PRICE_PER_SQFT"].median() if total_count > 0 else 0

# ROW 1: Macro Financials
r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
with r1c1:
    st.markdown(f"""
    <div class="kpi-card-highlight">
        <div class="kpi-title">Total Market Volume</div>
        <div class="kpi-val emerald-accent">AED {total_volume / 1e9:.2f}B</div>
        <div class="kpi-sub">{total_count:,} Total Deals</div>
    </div>
    """, unsafe_allow_html=True)

with r1c2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Overall Avg Deal Value</div>
        <div class="kpi-val">AED {overall_avg:,.0f}</div>
        <div class="kpi-sub">Median: AED {overall_median:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with r1c3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Avg Apartment Price</div>
        <div class="kpi-val gold-accent">AED {apt_avg:,.0f}</div>
        <div class="kpi-sub">Median: AED {apt_median:,.0f} ({len(apt_df):,} Deals)</div>
    </div>
    """, unsafe_allow_html=True)

with r1c4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Avg Villa Price</div>
        <div class="kpi-val gold-accent">AED {villa_avg:,.0f}</div>
        <div class="kpi-sub">Median: AED {villa_median:,.0f} ({len(villa_df):,} Deals)</div>
    </div>
    """, unsafe_allow_html=True)

with r1c5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Highest Single Deal</div>
        <div class="kpi-val purple-accent">AED {max_deal / 1e6:.1f}M</div>
        <div class="kpi-sub">Luxury Benchmark Deal</div>
    </div>
    """, unsafe_allow_html=True)

# ROW 2: Pace, Price/SqFt & Stage
r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
with r2c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Daily Market Velocity</div>
        <div class="kpi-val">AED {daily_avg_vol / 1e6:.0f}M<span style="font-size:0.9rem">/day</span></div>
        <div class="kpi-sub">Avg {daily_avg_deals:.0f} deals closed daily</div>
    </div>
    """, unsafe_allow_html=True)

with r2c2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Median Price / Sq.Ft</div>
        <div class="kpi-val">AED {median_sqft:,.0f}</div>
        <div class="kpi-sub">Apt: AED {apt_sqft:,.0f} | Villa: AED {villa_sqft:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with r2c3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Total Apartment Volume</div>
        <div class="kpi-val">AED {apt_vol / 1e9:.2f}B</div>
        <div class="kpi-sub">{(apt_vol / total_volume * 100) if total_volume > 0 else 0:.1f}% of market volume</div>
    </div>
    """, unsafe_allow_html=True)

with r2c4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Total Villa Volume</div>
        <div class="kpi-val">AED {villa_vol / 1e9:.2f}B</div>
        <div class="kpi-sub">{(villa_vol / total_volume * 100) if total_volume > 0 else 0:.1f}% of market volume</div>
    </div>
    """, unsafe_allow_html=True)

with r2c5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Off-Plan vs Ready</div>
        <div class="kpi-val">{offplan_pct:.1f}%<span style="font-size:0.9rem; color:#94a3b8"> Off-Plan</span></div>
        <div class="kpi-sub">AED {offplan_vol / 1e9:.2f}B Inflow ({offplan_count:,} deals)</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ─── SUBTABS NAVIGATION ───────────────────────────────────────────────────────
tab_loc, tab_apt, tab_villa, tab_prop, tab_time, tab_voice = st.tabs([
    "📍 Locations Deep-Dive",
    "🏢 Apartments Deep-Dive",
    "🏡 Villas Deep-Dive",
    "📊 Property Types & Majority",
    "📅 Daily Velocity & Time Series",
    "🎙️ Voice AI & Mid-Call Broker Engine"
])

# ─────────────────────────────────────────────────────────────────────────────
# SUBTAB 1: LOCATIONS DEEP-DIVE
# ─────────────────────────────────────────────────────────────────────────────
with tab_loc:
    st.subheader("📍 Location Intelligence: Every Detail by Neighborhood")
    st.markdown("Filter and drill into any specific Dubai community to inspect transaction volume, villa vs apartment pricing, BHK splits, and top projects.")

    top_active_areas = df["LOCATION"].value_counts().head(50).index.tolist()
    
    loc_col1, loc_col2 = st.columns([2, 1])
    with loc_col1:
        loc_choice = st.selectbox("Select Neighborhood to Analyze:", top_active_areas, index=0, key="loc_choice")
    with loc_col2:
        loc_compare = st.selectbox("Optional: Compare Side-by-Side with:", ["None"] + [a for a in top_active_areas if a != loc_choice], index=0, key="loc_compare")

    loc_df = df[df["LOCATION"] == loc_choice]
    loc_deals = len(loc_df)
    loc_vol = loc_df["TRANS_VALUE"].sum()
    loc_avg = loc_df["TRANS_VALUE"].mean() if loc_deals > 0 else 0
    loc_med = loc_df["TRANS_VALUE"].median() if loc_deals > 0 else 0
    loc_sqft = loc_df["PRICE_PER_SQFT"].median() if loc_deals > 0 else 0
    loc_offplan = (loc_df["MARKET_STAGE"] == "Off-Plan").sum()

    # Location Specific KPIs
    lk1, lk2, lk3, lk4, lk5, lk6 = st.columns(6)
    with lk1:
        st.metric(f"Total Volume in {loc_choice}", f"AED {loc_vol/1e6:.1f}M", f"{(loc_vol/total_volume*100):.1f}% Dubai Share")
    with lk2:
        st.metric("Total Deals Closed", f"{loc_deals:,}", f"{loc_offplan} Off-Plan deals")
    with lk3:
        st.metric("Average Deal Price", f"AED {loc_avg:,.0f}", f"Median: AED {loc_med:,.0f}")
    with lk4:
        v_sub = loc_df[loc_df["PROPERTY_CATEGORY"] == "Villa"]
        v_str = f"AED {v_sub['TRANS_VALUE'].mean():,.0f}" if len(v_sub) > 0 else "No Villas"
        st.metric("Avg Villa Price", v_str, f"{len(v_sub)} deals")
    with lk5:
        a_sub = loc_df[loc_df["PROPERTY_CATEGORY"] == "Apartment"]
        a_str = f"AED {a_sub['TRANS_VALUE'].mean():,.0f}" if len(a_sub) > 0 else "No Apartments"
        st.metric("Avg Apartment Price", a_str, f"{len(a_sub)} deals")
    with lk6:
        st.metric("Median Price / Sq.Ft", f"AED {loc_sqft:,.0f}" if pd.notnull(loc_sqft) and loc_sqft > 0 else "N/A", "Calculated Area")

    # Side-by-side comparison if selected
    if loc_compare != "None":
        st.markdown(f"### ⚖️ Head-to-Head: **{loc_choice}** vs **{loc_compare}**")
        comp_df = df[df["LOCATION"] == loc_compare]
        c_deals = len(comp_df)
        c_vol = comp_df["TRANS_VALUE"].sum()
        c_avg = comp_df["TRANS_VALUE"].mean() if c_deals > 0 else 0
        c_med = comp_df["TRANS_VALUE"].median() if c_deals > 0 else 0
        c_sqft = comp_df["PRICE_PER_SQFT"].median() if c_deals > 0 else 0

        comp_matrix = pd.DataFrame({
            "Metric": ["Total Volume", "Transactions Closed", "Average Price", "Median Price", "Median Price / Sq.Ft", "Off-Plan Share %"],
            loc_choice: [
                f"AED {loc_vol/1e6:.1f}M",
                f"{loc_deals:,}",
                f"AED {loc_avg:,.0f}",
                f"AED {loc_med:,.0f}",
                f"AED {loc_sqft:,.0f}/sqft" if loc_sqft > 0 else "N/A",
                f"{(loc_offplan/loc_deals*100) if loc_deals > 0 else 0:.1f}%"
            ],
            loc_compare: [
                f"AED {c_vol/1e6:.1f}M",
                f"{c_deals:,}",
                f"AED {c_avg:,.0f}",
                f"AED {c_med:,.0f}",
                f"AED {c_sqft:,.0f}/sqft" if c_sqft > 0 else "N/A",
                f"{(comp_df['MARKET_STAGE']=='Off-Plan').sum()/c_deals*100 if c_deals > 0 else 0:.1f}%"
            ]
        })
        st.table(comp_matrix)

    c_bhk, c_proj = st.columns(2)
    with c_bhk:
        st.markdown(f"#### 🛏️ Bedroom (BHK) Breakdown in **{loc_choice}**")
        loc_bhk = loc_df[~loc_df["BHK"].isin(["Not Specified", "Commercial Unit"])].groupby("BHK").agg(
            Deals=("TRANS_VALUE", "count"),
            Avg_Price=("TRANS_VALUE", "mean"),
            Median_Price=("TRANS_VALUE", "median"),
            Min_Price=("TRANS_VALUE", "min"),
            Max_Price=("TRANS_VALUE", "max")
        ).sort_values("Deals", ascending=False).reset_index()

        if len(loc_bhk) > 0:
            loc_bhk["Avg_Price"] = loc_bhk["Avg_Price"].apply(lambda x: f"AED {x:,.0f}")
            loc_bhk["Median_Price"] = loc_bhk["Median_Price"].apply(lambda x: f"AED {x:,.0f}")
            loc_bhk["Price_Range"] = loc_bhk.apply(lambda r: f"AED {r['Min_Price']/1e3:.0f}K - AED {r['Max_Price']/1e6:.2f}M", axis=1)
            st.dataframe(loc_bhk[["BHK", "Deals", "Avg_Price", "Median_Price", "Price_Range"]], use_container_width=True, hide_index=True)
        else:
            st.info(f"No specific bedroom breakdown records for {loc_choice}.")

    with c_proj:
        st.markdown(f"#### 🏗️ Top Selling Projects in **{loc_choice}**")
        loc_proj = loc_df[loc_df["PROJECT"] != "Independent"].groupby("PROJECT").agg(
            Deals=("TRANS_VALUE", "count"),
            Total_Volume=("TRANS_VALUE", "sum"),
            Avg_Price=("TRANS_VALUE", "mean")
        ).sort_values("Total_Volume", ascending=False).head(8).reset_index()

        if len(loc_proj) > 0:
            loc_proj["Total_Volume"] = loc_proj["Total_Volume"].apply(lambda x: f"AED {x/1e6:.1f}M")
            loc_proj["Avg_Price"] = loc_proj["Avg_Price"].apply(lambda x: f"AED {x:,.0f}")
            st.dataframe(loc_proj.rename(columns={"PROJECT": "Project Name", "Total_Volume": "Volume Inflow", "Avg_Price": "Average Ticket"}), use_container_width=True, hide_index=True)
        else:
            st.info(f"No registered master projects with multiple deals in {loc_choice}.")

    st.markdown("---")
    st.markdown("#### 📑 Master Location Comparison Table (All Dubai Communities)")
    master_loc_table = df.groupby("LOCATION").apply(lambda g: pd.Series({
        "Total Deals": len(g),
        "Total Volume (AED M)": round(g["TRANS_VALUE"].sum() / 1e6, 1),
        "Overall Avg Price": f"AED {g['TRANS_VALUE'].mean():,.0f}",
        "Villa Avg Price": f"AED {g[g['PROPERTY_CATEGORY']=='Villa']['TRANS_VALUE'].mean():,.0f}" if len(g[g['PROPERTY_CATEGORY']=='Villa']) > 0 else "-",
        "Apartment Avg Price": f"AED {g[g['PROPERTY_CATEGORY']=='Apartment']['TRANS_VALUE'].mean():,.0f}" if len(g[g['PROPERTY_CATEGORY']=='Apartment']) > 0 else "-",
        "Median Price/SqFt": f"AED {g['PRICE_PER_SQFT'].median():,.0f}" if pd.notnull(g['PRICE_PER_SQFT'].median()) else "-",
        "Off-Plan %": f"{(g['MARKET_STAGE']=='Off-Plan').sum()/len(g)*100:.0f}%"
    }), include_groups=False).reset_index().sort_values("Total Deals", ascending=False)
    st.dataframe(master_loc_table, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# SUBTAB 2: APARTMENTS DEEP-DIVE
# ─────────────────────────────────────────────────────────────────────────────
with tab_apt:
    st.subheader("🏢 Apartments Deep-Dive: Demand, Pricing & Unit Sizes")
    st.markdown("Detailed breakdown of Dubai's dominant residential asset class (79.9% of all transactions).")

    # Apartment KPI Ribbon
    ak1, ak2, ak3, ak4, ak5, ak6 = st.columns(6)
    with ak1:
        st.metric("Total Apartment Volume", f"AED {apt_vol/1e9:.2f}B", f"{len(apt_df):,} Units Sold")
    with ak2:
        st.metric("Avg Apartment Ticket", f"AED {apt_avg:,.0f}", f"Median: AED {apt_median:,.0f}")
    with ak3:
        st.metric("Median Price / Sq.Ft", f"AED {apt_sqft:,.0f}", "Across verified flats")
    with ak4:
        apt_offplan = (apt_df["MARKET_STAGE"] == "Off-Plan").sum()
        st.metric("Off-Plan Apartments", f"{apt_offplan:,}", f"{(apt_offplan/len(apt_df)*100) if len(apt_df)>0 else 0:.1f}% Market Share")
    with ak5:
        apt_avg_area = apt_df["AREA_SQFT"].median()
        st.metric("Median Unit Size", f"{apt_avg_area:,.0f} sq.ft", "Typical living space")
    with ak6:
        apt_max = apt_df["TRANS_VALUE"].max()
        st.metric("Highest Apartment Sale", f"AED {apt_max/1e6:.1f}M", "Luxury penthouse deal")

    # Sub-filters for Apartments
    st.markdown("#### 🔍 Filter Apartment Inventory")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        apt_bhk_filter = st.selectbox("Select Bedroom (BHK):", ["All BHKs", "Studio", "1 B/R", "2 B/R", "3 B/R", "4 B/R", "5 B/R"], index=0)
    with fc2:
        apt_stage_filter = st.selectbox("Market Stage (Apartments):", ["All", "Off-Plan", "Ready"], index=0)
    with fc3:
        apt_tier_filter = st.selectbox("Ticket Size Tier:", ["All Prices", "Under 1M AED", "1M - 2M AED", "2M - 5M AED", "5M+ AED"], index=0)

    filtered_apt = apt_df.copy()
    if apt_bhk_filter != "All BHKs":
        filtered_apt = filtered_apt[filtered_apt["BHK"] == apt_bhk_filter]
    if apt_stage_filter != "All":
        filtered_apt = filtered_apt[filtered_apt["MARKET_STAGE"] == apt_stage_filter]
    if apt_tier_filter == "Under 1M AED":
        filtered_apt = filtered_apt[filtered_apt["TRANS_VALUE"] < 1e6]
    elif apt_tier_filter == "1M - 2M AED":
        filtered_apt = filtered_apt[(filtered_apt["TRANS_VALUE"] >= 1e6) & (filtered_apt["TRANS_VALUE"] < 2e6)]
    elif apt_tier_filter == "2M - 5M AED":
        filtered_apt = filtered_apt[(filtered_apt["TRANS_VALUE"] >= 2e6) & (filtered_apt["TRANS_VALUE"] < 5e6)]
    elif apt_tier_filter == "5M+ AED":
        filtered_apt = filtered_apt[filtered_apt["TRANS_VALUE"] >= 5e6]

    st.write(f"Displaying **{len(filtered_apt):,}** filtered apartment deals totaling **AED {filtered_apt['TRANS_VALUE'].sum()/1e6:.1f}M** (Average: **AED {filtered_apt['TRANS_VALUE'].mean():,.0f}** | Median: **AED {filtered_apt['TRANS_VALUE'].median():,.0f}**).")

    ac1, ac2 = st.columns(2)
    with ac1:
        st.markdown("#### 📍 Top 10 Apartment Locations by Deal Volume")
        top_apt_locs = apt_df.groupby("LOCATION")["TRANS_VALUE"].agg(["count", "sum", "mean"]).sort_values("count", ascending=False).head(10).reset_index()
        fig_apt_loc = px.bar(
            top_apt_locs.sort_values("count", ascending=True),
            x="count",
            y="LOCATION",
            orientation="h",
            text="count",
            color="count",
            color_continuous_scale="Teal",
            template="plotly_dark",
            labels={"count": "Apartments Sold", "LOCATION": ""}
        )
        fig_apt_loc.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_apt_loc.update_layout(height=380, coloraxis_showscale=False, margin=dict(l=10, r=40, t=10, b=10))
        st.plotly_chart(fig_apt_loc, use_container_width=True)

    with ac2:
        st.markdown("#### 🛏️ Apartment BHK Pricing Comparison (Avg vs Median)")
        apt_bhk_grp = apt_df[~apt_df["BHK"].isin(["Not Specified", "Commercial Unit"])].groupby("BHK").agg(
            Avg=("TRANS_VALUE", "mean"),
            Median=("TRANS_VALUE", "median"),
            Deals=("TRANS_VALUE", "count")
        ).sort_values("Deals", ascending=False).head(5).reset_index()

        fig_bhk_comp = go.Figure()
        fig_bhk_comp.add_trace(go.Bar(
            x=apt_bhk_grp["BHK"],
            y=apt_bhk_grp["Avg"] / 1e6,
            name="Average Price (AED M)",
            marker_color="#38bdf8"
        ))
        fig_bhk_comp.add_trace(go.Bar(
            x=apt_bhk_grp["BHK"],
            y=apt_bhk_grp["Median"] / 1e6,
            name="Median Price (AED M)",
            marker_color="#f59e0b"
        ))
        fig_bhk_comp.update_layout(
            barmode="group",
            template="plotly_dark",
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
            yaxis=dict(title="Price (AED Millions)")
        )
        st.plotly_chart(fig_bhk_comp, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# SUBTAB 3: VILLAS DEEP-DIVE
# ─────────────────────────────────────────────────────────────────────────────
with tab_villa:
    st.subheader("🏡 Villas Deep-Dive: Communities, Luxury & Bedroom Pricing")
    st.markdown("Complete analysis of the 1,513 villa and townhouse transactions across Dubai.")

    # Villa KPI Ribbon
    vk1, vk2, vk3, vk4, vk5, vk6 = st.columns(6)
    with vk1:
        st.metric("Total Villa Volume", f"AED {villa_vol/1e9:.2f}B", f"{len(villa_df):,} Villas Sold")
    with vk2:
        st.metric("Avg Villa Ticket", f"AED {villa_avg:,.0f}", f"Median: AED {villa_median:,.0f}")
    with vk3:
        st.metric("Median Price / Sq.Ft", f"AED {villa_sqft:,.0f}", "Villa built-up rate")
    with vk4:
        v_offplan = (villa_df["MARKET_STAGE"] == "Off-Plan").sum()
        st.metric("Off-Plan Villas", f"{v_offplan:,}", f"{(v_offplan/len(villa_df)*100) if len(villa_df)>0 else 0:.1f}% Off-Plan Share")
    with vk5:
        v_med_area = villa_df["AREA_SQFT"].median()
        st.metric("Median Villa Area", f"{v_med_area:,.0f} sq.ft", "Spacious floorplans")
    with vk6:
        v_max = villa_df["TRANS_VALUE"].max()
        st.metric("Peak Villa Deal", f"AED {v_max/1e6:.1f}M", "Prime luxury villa")

    st.markdown("#### 🏘️ Top 15 Villa Communities (Ranked by Sales Volume & Averages)")
    top_villa_table = villa_df.groupby("LOCATION").agg(
        Deals=("TRANS_VALUE", "count"),
        Total_Volume=("TRANS_VALUE", "sum"),
        Avg_Price=("TRANS_VALUE", "mean"),
        Median_Price=("TRANS_VALUE", "median"),
        Min_Price=("TRANS_VALUE", "min"),
        Max_Price=("TRANS_VALUE", "max"),
        Median_SqFt=("PRICE_PER_SQFT", "median")
    ).sort_values("Deals", ascending=False).head(15).reset_index()

    top_villa_table["Total Volume"] = top_villa_table["Total_Volume"].apply(lambda x: f"AED {x/1e6:.1f}M")
    top_villa_table["Avg Villa Price"] = top_villa_table["Avg_Price"].apply(lambda x: f"AED {x:,.0f}")
    top_villa_table["Median Villa Price"] = top_villa_table["Median_Price"].apply(lambda x: f"AED {x:,.0f}")
    top_villa_table["Price Range"] = top_villa_table.apply(lambda r: f"AED {r['Min_Price']/1e6:.2f}M - AED {r['Max_Price']/1e6:.2f}M", axis=1)
    top_villa_table["Median Rate / SqFt"] = top_villa_table["Median_SqFt"].apply(lambda x: f"AED {x:,.0f}" if pd.notnull(x) else "-")

    st.dataframe(
        top_villa_table[["LOCATION", "Deals", "Total Volume", "Avg Villa Price", "Median Villa Price", "Price Range", "Median Rate / SqFt"]].rename(
            columns={"LOCATION": "Villa Community / Neighborhood"}
        ),
        use_container_width=True,
        hide_index=True
    )

    vc1, vc2 = st.columns(2)
    with vc1:
        st.markdown("#### 💰 Top Villa Inflow Hotspots")
        fig_v_vol = px.bar(
            top_villa_table.head(10).sort_values("Deals", ascending=True),
            x="Deals",
            y="LOCATION",
            orientation="h",
            text="Deals",
            color="Avg_Price",
            color_continuous_scale="Purples",
            template="plotly_dark",
            labels={"Deals": "Villas Sold", "LOCATION": "", "Avg_Price": "Avg Price (AED)"}
        )
        fig_v_vol.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_v_vol.update_layout(height=380, margin=dict(l=10, r=40, t=10, b=10))
        st.plotly_chart(fig_v_vol, use_container_width=True)

    with vc2:
        st.markdown("#### 🛏️ Villa Bedroom Breakdown")
        v_bhk = villa_df[~villa_df["BHK"].isin(["Not Specified", "Commercial Unit"])].groupby("BHK").agg(
            Deals=("TRANS_VALUE", "count"),
            Avg_Price=("TRANS_VALUE", "mean"),
            Median_Price=("TRANS_VALUE", "median")
        ).sort_values("Deals", ascending=False).head(5).reset_index()

        fig_v_bhk = px.bar(
            v_bhk,
            x="BHK",
            y="Deals",
            color="Avg_Price",
            text="Deals",
            color_continuous_scale="Viridis",
            template="plotly_dark",
            labels={"Deals": "Villas Sold", "Avg_Price": "Avg Price"}
        )
        fig_v_bhk.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_v_bhk.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_v_bhk, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# SUBTAB 4: PROPERTY TYPES & MAJORITY
# ─────────────────────────────────────────────────────────────────────────────
with tab_prop:
    st.subheader("📊 Property Types & The Majority: Market Composition")
    st.markdown("Complete multi-asset class analysis comparing Apartments, Villas, Commercial, and Land side-by-side.")

    # Property Type Selector Dropdown
    selected_prop_type = st.selectbox(
        "Select Property Type for Full Detail Profile:",
        ["Apartment", "Villa", "Land", "Commercial", "All Property Types"],
        index=0
    )

    if selected_prop_type != "All Property Types":
        p_sub = df[df["PROPERTY_CATEGORY"] == selected_prop_type]
        p_vol = p_sub["TRANS_VALUE"].sum()
        p_cnt = len(p_sub)
        p_avg = p_sub["TRANS_VALUE"].mean() if p_cnt > 0 else 0
        p_med = p_sub["TRANS_VALUE"].median() if p_cnt > 0 else 0
        p_min = p_sub["TRANS_VALUE"].min() if p_cnt > 0 else 0
        p_max = p_sub["TRANS_VALUE"].max() if p_cnt > 0 else 0
        p_sqft = p_sub["PRICE_PER_SQFT"].median() if p_cnt > 0 else 0

        pk1, pk2, pk3, pk4, pk5 = st.columns(5)
        with pk1:
            st.metric(f"{selected_prop_type} Total Volume", f"AED {p_vol/1e9:.2f}B", f"{(p_vol/total_volume*100):.1f}% of Total Volume")
        with pk2:
            st.metric("Total Deals Closed", f"{p_cnt:,}", f"{(p_cnt/total_count*100):.1f}% of Total Deals")
        with pk3:
            st.metric("Average Deal Price", f"AED {p_avg:,.0f}", f"Median: AED {p_med:,.0f}")
        with pk4:
            st.metric("Price Range", f"AED {p_min/1e3:.0f}K", f"Max: AED {p_max/1e6:.1f}M")
        with pk5:
            st.metric("Median Rate / Sq.Ft", f"AED {p_sqft:,.0f}" if p_sqft > 0 else "N/A", "Verified Size")

    st.markdown("#### ⚖️ Complete Property Type Comparison Matrix")
    prop_comparison = df.groupby("PROPERTY_CATEGORY").agg(
        Deals=("TRANS_VALUE", "count"),
        Total_Volume=("TRANS_VALUE", "sum"),
        Avg_Price=("TRANS_VALUE", "mean"),
        Median_Price=("TRANS_VALUE", "median"),
        Min_Price=("TRANS_VALUE", "min"),
        Max_Price=("TRANS_VALUE", "max"),
        Median_SqFt=("PRICE_PER_SQFT", "median")
    ).sort_values("Deals", ascending=False).reset_index()

    prop_comparison["Market Share %"] = prop_comparison["Deals"].apply(lambda x: f"{(x/total_count*100):.1f}%")
    prop_comparison["Total Volume (AED B)"] = prop_comparison["Total_Volume"].apply(lambda x: f"AED {x/1e9:.2f}B")
    prop_comparison["Average Price"] = prop_comparison["Avg_Price"].apply(lambda x: f"AED {x:,.0f}")
    prop_comparison["Median Price"] = prop_comparison["Median_Price"].apply(lambda x: f"AED {x:,.0f}")
    prop_comparison["Rate / SqFt"] = prop_comparison["Median_SqFt"].apply(lambda x: f"AED {x:,.0f}" if pd.notnull(x) else "-")

    st.dataframe(
        prop_comparison[["PROPERTY_CATEGORY", "Deals", "Market Share %", "Total Volume (AED B)", "Average Price", "Median Price", "Rate / SqFt"]].rename(
            columns={"PROPERTY_CATEGORY": "Property Asset Class"}
        ),
        use_container_width=True,
        hide_index=True
    )

    ptc1, ptc2 = st.columns(2)
    with ptc1:
        st.markdown("#### 🥧 Capital Volume Allocation by Asset Class")
        fig_p_pie = px.pie(
            prop_comparison,
            names="PROPERTY_CATEGORY",
            values="Total_Volume",
            hole=0.55,
            color_discrete_sequence=px.colors.qualitative.Bold,
            template="plotly_dark"
        )
        fig_p_pie.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_p_pie, use_container_width=True)

    with ptc2:
        st.markdown("#### 📊 Deal Volume Dominance (Majority)")
        fig_p_bar = px.bar(
            prop_comparison,
            x="PROPERTY_CATEGORY",
            y="Deals",
            text="Deals",
            color="PROPERTY_CATEGORY",
            template="plotly_dark",
            labels={"PROPERTY_CATEGORY": "Property Class", "Deals": "Transactions"}
        )
        fig_p_bar.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_p_bar.update_layout(height=360, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_p_bar, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# SUBTAB 5: DAILY VELOCITY & TIME SERIES
# ─────────────────────────────────────────────────────────────────────────────
with tab_time:
    st.subheader("📅 Daily Transaction Velocity & Day-by-Day Analysis")
    st.markdown("Day-by-day progression tracking cash absorption and contract closing speeds.")

    daily_df = df.groupby("DATE").agg(
        Total_Volume=("TRANS_VALUE", "sum"),
        Deal_Count=("TRANS_VALUE", "count"),
        Avg_Price=("TRANS_VALUE", "mean")
    ).reset_index()
    daily_df["Volume_Millions"] = daily_df["Total_Volume"] / 1e6
    daily_df["DATE_STR"] = daily_df["DATE"].astype(str)

    # Time series chart
    fig_daily = go.Figure()
    fig_daily.add_trace(go.Bar(
        x=daily_df["DATE_STR"],
        y=daily_df["Volume_Millions"],
        name="Total Volume (AED Millions)",
        marker_color="#38bdf8",
        opacity=0.85,
        yaxis="y1",
        hovertemplate="<b>Date:</b> %{x}<br><b>Volume:</b> AED %{y:.1f}M<extra></extra>"
    ))
    fig_daily.add_trace(go.Scatter(
        x=daily_df["DATE_STR"],
        y=daily_df["Deal_Count"],
        name="Deal Count (Transactions)",
        mode="lines+markers",
        line=dict(color="#f59e0b", width=3),
        marker=dict(size=6),
        yaxis="y2",
        hovertemplate="<b>Date:</b> %{x}<br><b>Deals:</b> %{y:,}<extra></extra>"
    ))
    fig_daily.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Volume (AED Millions)", showgrid=True, gridcolor="#1e293b"),
        yaxis2=dict(title="Number of Deals", overlaying="y", side="right", showgrid=False)
    )
    st.plotly_chart(fig_daily, use_container_width=True)

    tc1, tc2 = st.columns(2)
    with tc1:
        st.markdown("#### 🗓️ Day-of-Week Closing Distribution")
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_df = df.groupby("DAY_NAME").agg(
            Volume=("TRANS_VALUE", "sum"),
            Deals=("TRANS_VALUE", "count")
        ).reindex(day_order).dropna().reset_index()
        dow_df["Volume_B"] = dow_df["Volume"] / 1e9

        fig_dow = px.bar(
            dow_df,
            x="DAY_NAME",
            y="Volume_B",
            text="Volume_B",
            color="Volume_B",
            color_continuous_scale="Blues",
            labels={"DAY_NAME": "Day of Week", "Volume_B": "Volume (AED Billions)"},
            template="plotly_dark"
        )
        fig_dow.update_traces(texttemplate="AED %{text:.2f}B", textposition="outside")
        fig_dow.update_layout(height=340, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_dow, use_container_width=True)

    with tc2:
        st.markdown("#### ⚡ Peak Volume Days")
        peak_days = daily_df.sort_values("Total_Volume", ascending=False).head(5).copy()
        peak_days["Volume"] = peak_days["Volume_Millions"].apply(lambda x: f"AED {x:.1f}M")
        peak_days["Deals"] = peak_days["Deal_Count"].apply(lambda x: f"{x:,}")
        peak_days["Avg Deal"] = peak_days["Avg_Price"].apply(lambda x: f"AED {x:,.0f}")
        st.dataframe(
            peak_days[["DATE_STR", "Volume", "Deals", "Avg Deal"]].rename(columns={"DATE_STR": "Date"}),
            use_container_width=True,
            hide_index=True
        )

# ─────────────────────────────────────────────────────────────────────────────
# SUBTAB 6: VOICE AI & BROKER MID-CALL ENGINE
# ─────────────────────────────────────────────────────────────────────────────
with tab_voice:
    st.subheader("🎙️ Mid-Call Voice AI & Broker Fast Intelligence")
    st.markdown("""
    *Designed for instant response generation during live client phone calls or automated Voice Agent responses (Retell AI, Bland, Vapi).*
    """)

    col_q1, col_q2 = st.columns(2)
    with col_q1:
        st.markdown("#### 🔍 Live Call Lookup Simulator")
        q_loc = st.selectbox("Caller asks about Area:", ["Jumeirah Village Circle", "Business Bay", "Downtown Dubai", "Dubai Marina", "Madinat Al Mataar", "Palm Jumeirah", "Dubai Hills", "Al Hebiah Sixth", "Al Yelayiss 1"], index=0, key="v_loc")
        q_type = st.selectbox("Property Type:", ["Apartment", "Villa", "All"], index=0, key="v_type")
        q_bhk = st.selectbox("Configuration / BHK:", ["Any BHK", "Studio", "1 B/R", "2 B/R", "3 B/R", "4 B/R", "5 B/R"], index=2, key="v_bhk")

        sub_q = df_raw[df_raw["LOCATION"].str.lower() == q_loc.lower()]
        if q_type != "All":
            sub_q = sub_q[sub_q["PROPERTY_CATEGORY"] == q_type]
        if q_bhk != "Any BHK":
            sub_q = sub_q[sub_q["BHK"] == q_bhk]

        count_q = len(sub_q)
        avg_q = sub_q["TRANS_VALUE"].mean() if count_q > 0 else 0
        med_q = sub_q["TRANS_VALUE"].median() if count_q > 0 else 0
        min_q = sub_q["TRANS_VALUE"].min() if count_q > 0 else 0
        max_q = sub_q["TRANS_VALUE"].max() if count_q > 0 else 0
        offplan_q = len(sub_q[sub_q["MARKET_STAGE"] == "Off-Plan"])
        offplan_rate = (offplan_q / count_q * 100) if count_q > 0 else 0

        if count_q > 0:
            agent_speech = (
                f"In {q_loc}, based on {count_q:,} recent transactions, the average price for a {q_bhk if q_bhk != 'Any BHK' else ''} "
                f"{q_type.lower()} is approximately AED {avg_q:,.0f}, with median pricing around AED {med_q:,.0f}. "
                f"Prices range from AED {min_q:,.0f} to AED {max_q:,.0f}, with {offplan_rate:.0f}% of deals being Off-Plan."
            )
        else:
            agent_speech = f"We currently see no closed transactions for a {q_bhk} {q_type.lower()} in {q_loc} in this period. Overall average for this area is AED {df_raw[df_raw['LOCATION'].str.lower() == q_loc.lower()]['TRANS_VALUE'].mean():,.0f}."

        st.markdown(f"<div class='voice-bubble'>🗣️ <b>Customer Asks:</b> \"What is the price of a {q_bhk} {q_type.lower()} in {q_loc}?\"</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='voice-response'>🤖 <b>Voice Agent Recommended Answer:</b><br><br>{agent_speech}</div>", unsafe_allow_html=True)

    with col_q2:
        st.markdown("#### ⚡ Quick Cheat Sheet (Top 5 Client Questions)")
        with st.expander("1. What is the current average price of a Villa in Dubai?", expanded=True):
            st.write(f"**Answer:** Across 1,513 villa transactions, the average price is **AED {villa_avg:,.0f}** (Median: **AED {villa_median:,.0f}**). Top high-volume villa communities are **Al Hebiah Sixth** (Avg AED 2.91M), **Al Yelayiss 1** (Avg AED 3.17M), and **Madinat Al Mataar** (Avg AED 4.60M).")
            
        with st.expander("2. Where did the most investments happen in Dubai?", expanded=False):
            st.write("**Answer:** By total capital inflow, the #1 hotspot is **Madinat Al Mataar (Dubai South)** with **AED 2.74B**, followed by **Burj Khalifa / Downtown** (AED 2.44B), **Business Bay** (AED 2.33B), and **Palm Jumeirah** (AED 1.57B).")
            
        with st.expander("3. What is the most popular property type and bedroom type?", expanded=False):
            st.write("**Answer:** **Apartments** represent **79.9%** of all residential transactions. The most popular configuration is **1 Bedroom** (5,405 deals, Avg AED 1.23M), followed by **Studios** (4,554 deals, Avg AED 663K) and **2 Bedrooms** (3,234 deals, Avg AED 2.21M).")
            
        with st.expander("4. Is the market dominated by Off-Plan or Ready properties?", expanded=False):
            st.write(f"**Answer:** **Off-Plan** leads slightly with **{offplan_pct:.1f}%** of transactions ({offplan_count:,} deals), while Ready properties account for **{100-offplan_pct:.1f}%**.")
            
        with st.expander("5. What is the daily market volume?", expanded=False):
            st.write(f"**Answer:** Dubai is currently averaging **AED 1.25 Billion per day** in transactional residential volume, with an average of **519 transactions closed every single day**.")

st.markdown("---")
st.caption("Dubai Real Estate Transaction Analytics Engine | Built for Client Presentations & Mid-Call Voice AI Retrieval | Render Deployment Ready")
