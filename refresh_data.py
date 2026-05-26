"""
Refresh Zillow Research datasets.

Downloads the latest published CSVs directly from Zillow Research public data
and replaces the local copies. Run this monthly after Zillow publishes new data
(typically around the 16th of each month).

Usage:
    python refresh_data.py

Data source: https://www.zillow.com/research/data/
"""

import shutil
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "raw" / "zillow"
BACKUP_DIR = Path(__file__).parent / "data" / "raw" / "zillow_backup"

# Public download URLs from Zillow Research.
# Verify or update at: https://www.zillow.com/research/data/
DATASET_URLS = {
    "zhvi_all_homes_zip.csv": (
        "https://files.zillowstatic.com/research/public_csvs/zhvi/"
        "Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    ),
    "zhvi_bottom_tier_county.csv": (
        "https://files.zillowstatic.com/research/public_csvs/zhvi/"
        "County_zhvi_uc_sfrcondo_tier_0.0_0.33_sm_sa_month.csv"
    ),
    "market_heat_index_metro.csv": (
        "https://files.zillowstatic.com/research/public_csvs/market_temp_index/"
        "Metro_market_temp_index_uc_sfrcondo_month.csv"
    ),
    "days_to_pending_metro.csv": (
        "https://files.zillowstatic.com/research/public_csvs/days_to_pending/"
        "Metro_days_to_pending_uc_sfrcondo_month.csv"
    ),
    "price_cuts_metro.csv": (
        "https://files.zillowstatic.com/research/public_csvs/perc_listings_price_cut/"
        "Metro_perc_listings_price_cut_uc_sfrcondo_month.csv"
    ),
    "sale_to_list_metro.csv": (
        "https://files.zillowstatic.com/research/public_csvs/sale_to_list/"
        "Metro_median_sale_to_list_uc_sfrcondo_sm_week.csv"
    ),
}


def backup_existing(data_dir: Path, backup_dir: Path) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / timestamp
    if data_dir.exists():
        shutil.copytree(data_dir, dest)
        print(f"  Backed up existing data to {dest}")


def download_dataset(filename: str, url: str, data_dir: Path) -> bool:
    dest = data_dir / filename
    print(f"  Downloading {filename}...", end=" ", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as response:
            content = response.read()
        dest.write_bytes(content)
        size_mb = len(content) / 1_000_000
        print(f"done ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"FAILED\n    Error: {e}")
        return False


def show_data_summary(data_dir: Path) -> None:
    import pandas as pd

    print("\nData summary after refresh:")
    zhvi_path = data_dir / "zhvi_all_homes_zip.csv"
    if zhvi_path.exists():
        df = pd.read_csv(zhvi_path, dtype={"RegionName": str})
        date_cols = [c for c in df.columns if c.count("-") == 2 and c[:4].isdigit()]
        if date_cols:
            print(f"  ZHVI ZIP: {len(df):,} ZIPs, data through {date_cols[-1]}")


def main() -> None:
    print("FlipIQ — Zillow Research Data Refresh")
    print("=" * 40)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    print("\nBacking up existing data...")
    backup_existing(DATA_DIR, BACKUP_DIR)

    print("\nDownloading latest datasets from Zillow Research...")
    results = {}
    for filename, url in DATASET_URLS.items():
        results[filename] = download_dataset(filename, url, DATA_DIR)

    succeeded = sum(results.values())
    failed = len(results) - succeeded

    print(f"\nRefresh complete: {succeeded}/{len(results)} datasets updated")

    if failed > 0:
        failed_files = [f for f, ok in results.items() if not ok]
        print(f"\nFailed downloads ({failed}):")
        for f in failed_files:
            print(f"  - {f}")
        print("\nIf downloads fail, verify URLs at: https://www.zillow.com/research/data/")
        print("Download manually and place files in: data/raw/zillow/")

    try:
        show_data_summary(DATA_DIR)
    except Exception:
        pass

    if failed > 0:
        sys.exit(1)

    print("\nRestart the Streamlit app to load the new data.")


if __name__ == "__main__":
    main()
