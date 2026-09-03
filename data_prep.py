import os, sys, pandas as pd, numpy as np
SOURCE_CSV = 'C:/Users/Rishi D/Downloads/transactions-2026-09-03 (1).csv'
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'data')
OUTPUT_PARQUET = os.path.join(OUTPUT_DIR, 'transactions_cleaned.parquet')
OUTPUT_CSV = os.path.join(OUTPUT_DIR, 'transactions_cleaned.csv')

def categorize_property(row):
    sb = str(row.get('PROP_SB_TYPE_EN', '')).strip().lower()
    pt = str(row.get('PROP_TYPE_EN', '')).strip().lower()
    if 'villa' in sb or 'villa' in pt: return 'Villa'
    elif 'flat' in sb or 'hotel apartment' in sb or 'apartment' in sb: return 'Apartment'
    elif 'unit' in pt:
        if any(c in sb for c in ['office', 'shop', 'retail', 'commercial']): return 'Commercial'
        return 'Apartment'
    elif 'land' in sb or 'land' in pt: return 'Land'
    elif 'building' in pt: return 'Building'
    elif any(c in sb for c in ['office', 'shop', 'commercial']): return 'Commercial'
    else: return 'Other'

def clean_bhk(val):
    s = str(val).strip()
    if s in ['Studio', '1 B/R', '2 B/R', '3 B/R', '4 B/R', '5 B/R', '6 B/R']: return s
    elif s in ['7 B/R', '8 B/R', '9 B/R', '10 B/R']: return '6+ B/R'
    elif s in ['Office', 'Shop', 'Commercial']: return 'Commercial Unit'
    elif s == 'PENTHOUSE': return 'Penthouse'
    else: return 'Not Specified'

def clean_area_name(name): return str(name).strip().title()

def main():
    print('Reading raw transactions from:', SOURCE_CSV)
    if not os.path.exists(SOURCE_CSV):
        print('Error: File not found at', SOURCE_CSV); sys.exit(1)
    df = pd.read_csv(SOURCE_CSV)
    print('Loaded records:', len(df))
    df['DATETIME'] = pd.to_datetime(df['INSTANCE_DATE'], errors='coerce')
    df['DATE'] = df['DATETIME'].dt.date.astype(str)
    df['DAY_NAME'] = df['DATETIME'].dt.day_name()
    df['DAY'] = df['DATETIME'].dt.day
    df['MONTH_YEAR'] = df['DATETIME'].dt.strftime('%B %Y')
    df['TRANS_VALUE'] = pd.to_numeric(df['TRANS_VALUE'], errors='coerce').fillna(0.0)
    df['PROPERTY_CATEGORY'] = df.apply(categorize_property, axis=1)
    df['BHK'] = df['ROOMS_EN'].apply(clean_bhk)
    df['LOCATION'] = df['AREA_EN'].apply(clean_area_name)
    df['PROJECT'] = df['PROJECT_EN'].fillna('Independent').str.strip()
    df['MARKET_STAGE'] = df['IS_OFFPLAN_EN'].fillna('Ready').str.strip()
    df['TRANSACTION_GROUP'] = df['GROUP_EN'].fillna('Sales').str.strip()
    df['ACTUAL_AREA_SQM'] = pd.to_numeric(df['ACTUAL_AREA'], errors='coerce').fillna(0.0)
    df['AREA_SQFT'] = df['ACTUAL_AREA_SQM'] * 10.7639
    mask_valid = (df['AREA_SQFT'] > 100) & (df['TRANS_VALUE'] > 10000)
    df['PRICE_PER_SQFT'] = np.where(mask_valid, df['TRANS_VALUE'] / df['AREA_SQFT'], np.nan)
    df['PRICE_PER_SQFT'] = df['PRICE_PER_SQFT'].apply(lambda x: x if (100 <= x <= 25000) else np.nan)
    cols = ['TRANSACTION_NUMBER', 'DATE', 'DATETIME', 'DAY_NAME', 'DAY', 'MONTH_YEAR', 'TRANS_VALUE', 'PROPERTY_CATEGORY', 'PROP_TYPE_EN', 'PROP_SB_TYPE_EN', 'BHK', 'LOCATION', 'PROJECT', 'MARKET_STAGE', 'TRANSACTION_GROUP', 'ACTUAL_AREA_SQM', 'AREA_SQFT', 'PRICE_PER_SQFT']
    clean_df = df[cols].copy()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clean_df.to_parquet(OUTPUT_PARQUET, index=False)
    print('Saved Parquet:', OUTPUT_PARQUET)
    clean_df.to_csv(OUTPUT_CSV, index=False)
    print('Saved CSV:', OUTPUT_CSV)
    print('Total Transactions:', len(clean_df))
    print('Total Volume: AED', round(clean_df['TRANS_VALUE'].sum() / 1e9, 2), 'B')
    print('Overall Avg Deal: AED', round(clean_df['TRANS_VALUE'].mean(), 2))
    for cat in ['Apartment', 'Villa', 'Commercial', 'Land']:
        sub = clean_df[clean_df['PROPERTY_CATEGORY'] == cat]
        print(cat, ':', len(sub), 'deals | Avg AED', round(sub['TRANS_VALUE'].mean(), 2), '| Median AED', round(sub['TRANS_VALUE'].median(), 2))
    print('Data prep complete!')

if __name__ == '__main__': main()
