# 🏙️ Dubai Real Estate Transaction Intelligence Dashboard

Executive-ready analytical dashboard and instant Voice AI retrieval engine built for Dubai residential real estate transaction data.

Designed specifically for:
1. **Client & Agency Presentations**: High-impact macro trends, market health, and investment hotspots.
2. **Real Estate Brokers**: Detailed drilldown into bedroom pricing (BHK), villa vs. apartment comparisons, and price per sq.ft by community.
3. **Mid-Call AI Voice Agents (Retell AI, Vapi, Bland)**: Real-time lookup simulator and REST API to answer live caller pricing questions during calls.

---

## 📊 Core Market Metrics (At a Glance)

*Based on verified analysis of 17,651 recent transactions:*

- **Total Transaction Volume**: **AED 42.52 Billion**
- **Average Transaction Value**: **AED 2,409,086** (Median: **AED 1,227,732**)
- **Average Apartment Price**: **AED 1,669,596** (14,102 deals | Median: **AED 1,058,588**)
- **Average Villa Price**: **AED 3,716,598** (1,513 deals | Median: **AED 2,940,000**)
- **Daily Pace**: **AED 1.25 Billion / day** across an average of **519 transactions daily** (peaking at 963 deals/day)
- **Market Stage**: **52.1% Off-Plan** vs. **47.9% Ready**

---

## 🏆 The "Majority" & Popularity Rankings

### 1. Most Popular Property Type
1. **Apartments / Flats**: **79.9%** (14,102 deals — AED 23.54 Billion)
2. **Villas**: **8.6%** (1,513 deals — AED 5.62 Billion)
3. **Plots / Land**: **8.0%** (1,403 deals — AED 9.69 Billion)
4. **Commercial**: **3.6%** (630 deals — AED 3.65 Billion)

### 2. Most Demanded Bedroom Configurations (BHK)
1. **1 B/R**: **5,405 deals** (Avg: **AED 1.23M** | Median: **AED 1.15M**)
2. **Studio**: **4,554 deals** (Avg: **AED 663K** | Median: **AED 642K**)
3. **2 B/R**: **3,234 deals** (Avg: **AED 2.21M** | Median: **AED 1.88M**)
4. **3 B/R**: **1,436 deals** (Avg: **AED 3.74M** | Median: **AED 2.88M**)
5. **4 B/R**: **687 deals** (Avg: **AED 4.98M** | Median: **AED 3.42M**)
6. **5 B/R**: **134 deals** (Avg: **AED 7.81M** | Median: **AED 5.65M**)

### 3. Top Locations by Capital Inflow
1. **Madinat Al Mataar (Dubai South)**: **AED 2.74 Billion**
2. **Burj Khalifa / Downtown Dubai**: **AED 2.44 Billion**
3. **Business Bay**: **AED 2.33 Billion**
4. **Al Rowaiyah First**: **AED 2.00 Billion**
5. **Palm Jumeirah**: **AED 1.57 Billion**
6. **Dubai Hills**: **AED 1.48 Billion**
7. **Jumeirah Village Circle (JVC)**: **AED 1.44 Billion**
8. **Dubai Marina**: **AED 1.40 Billion**

---

## 🏘️ Villa Averages by Neighborhood (Cheat Sheet)

| Community | Villa Transactions | Average Price (AED) | Median Price (AED) | Total Inflow |
| :--- | :--- | :--- | :--- | :--- |
| **Al Hebiah Sixth** | 127 | **AED 2,910,495** | AED 2,999,500 | AED 369.6M |
| **Madinat Al Mataar** | 127 | **AED 4,599,330** | AED 4,850,000 | AED 584.1M |
| **Al Yelayiss 1** | 125 | **AED 3,167,943** | AED 2,874,240 | AED 396.0M |
| **Al Yufrah 1** | 95 | **AED 2,584,443** | AED 2,480,000 | AED 245.5M |
| **Dubai Investment Park 1** | 88 | **AED 1,966,714** | AED 1,610,959 | AED 173.1M |
| **Emirate Living** | 80 | **AED 3,592,911** | AED 3,598,500 | AED 287.4M |
| **Al Rowaiyah First** | 63 | **AED 4,575,408** | AED 4,400,000 | AED 288.3M |
| **Wadi Al Safa 5** | 63 | **AED 3,416,524** | AED 3,320,000 | AED 215.2M |
| **Villanova** | 62 | **AED 2,523,967** | AED 2,450,000 | AED 156.5M |
| **Mira** | 61 | **AED 2,536,849** | AED 2,700,000 | AED 154.7M |

---

## 🚀 How to Run Locally

```bash
# 1. Navigate to the project directory
cd "c:\Users\Rishi D\.antigravity\extensions\dubai-real-estate-dashboard"

# 2. Run the Streamlit Dashboard
py -m streamlit run app.py
```
Or simply double-click `run.bat`.

---

## 🌐 Deploying to Render (Step-by-Step)

1. **Push to GitHub**:
   Initialize a Git repository and push this folder to your GitHub account:
   ```bash
   git init
   git add .
   git commit -m "Dubai Real Estate Analytics Dashboard"
   git branch -M main
   git remote add origin https://github.com/<your-username>/dubai-real-estate-dashboard.git
   git push -u origin main
   ```
2. **Create New Web Service on Render**:
   - Go to [dashboard.render.com](https://dashboard.render.com).
   - Click **New +** -> **Web Service**.
   - Connect your GitHub repository.
   - Render will automatically detect `render.yaml` or use these settings:
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false`
   - Select the **Free** tier and click **Deploy Web Service**.
3. Your dashboard will be live on a public HTTPS URL (e.g., `https://dubai-real-estate-analytics.onrender.com`).

---

## 🎙️ Voice AI Integration (Retell AI, Vapi, Bland)

To connect your Voice Agent mid-call, launch the FastAPI server or deploy it alongside:
```bash
py api.py
```
- **Lookup Endpoint**: `GET /api/lookup?area=JVC&prop_type=Apartment&bhk=1 B/R`
- Returns instant natural speech text ready to speak into the caller's ear:
  ```json
  {
    "speech": "In Jumeirah Village Circle, based on 820 recent transactions, the average price for a 1 B/R apartment is approximately AED 1,150,000, with median pricing around AED 1,120,000. Prices range from AED 650,000 to AED 2,100,000, with 68% of deals being Off-Plan.",
    "average_aed": 1150000,
    "median_aed": 1120000,
    "deal_count": 820
  }
  ```
