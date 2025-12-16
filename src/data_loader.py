"""
Zillow Data Loader Module

Functions to load and preprocess Zillow Research datasets for house flipper analysis.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


# Default data directory
DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "zillow"


def _identify_date_columns(columns: List[str]) -> List[str]:
    """Identify columns that are dates (format YYYY-MM-DD)."""
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    return [col for col in columns if date_pattern.match(str(col))]


def _identify_metadata_columns(columns: List[str]) -> List[str]:
    """Identify non-date columns (metadata)."""
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    return [col for col in columns if not date_pattern.match(str(col))]


def _standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize metadata column names to snake_case."""
    rename_map = {
        'RegionID': 'region_id',
        'RegionName': 'region_name',
        'RegionType': 'region_type',
        'State': 'state',
        'StateName': 'state_name',
        'StateCodeFIPS': 'state_fips',
        'MunicipalCodeFIPS': 'municipal_fips',
        'City': 'city',
        'Metro': 'metro',
        'CountyName': 'county_name',
        'SizeRank': 'size_rank',
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})


def _validate_dataframe(df: pd.DataFrame, name: str) -> Dict:
    """Validate a dataframe and return validation info."""
    date_cols = _identify_date_columns(df.columns.tolist())
    meta_cols = _identify_metadata_columns(df.columns.tolist())

    # Parse dates for date range
    dates = pd.to_datetime(date_cols)

    validation = {
        'name': name,
        'shape': df.shape,
        'num_regions': len(df),
        'num_dates': len(date_cols),
        'date_range': (dates.min(), dates.max()) if len(dates) > 0 else (None, None),
        'metadata_columns': meta_cols,
        'missing_values': df.isnull().sum().sum(),
        'missing_pct': (df.isnull().sum().sum() / df.size) * 100,
    }

    return validation


def load_zhvi_zip(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load ZIP-level Zillow Home Value Index (all homes).

    Returns DataFrame with standardized column names.
    Geographic level: ZIP code
    """
    path = (data_dir or DATA_DIR) / "zhvi_all_homes_zip.csv"
    df = pd.read_csv(path, dtype={'RegionName': str})
    df = _standardize_column_names(df)
    return df


def load_zhvi_bottom_tier_county(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load County-level bottom tier home values.

    Bottom tier represents homes in the 5th-35th percentile of value.
    Geographic level: County
    """
    path = (data_dir or DATA_DIR) / "zhvi_bottom_tier_county.csv"
    df = pd.read_csv(path)
    df = _standardize_column_names(df)
    return df


def load_market_heat_index(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load Metro-level Market Heat Index.

    Higher values indicate hotter (more competitive) markets.
    Scale: Typically 0-100+
    Geographic level: Metro (MSA)
    """
    path = (data_dir or DATA_DIR) / "market_heat_index_metro.csv"
    df = pd.read_csv(path)
    df = _standardize_column_names(df)
    return df


def load_days_to_pending(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load Metro-level Days to Pending.

    Measures how quickly listings go under contract.
    Lower values = faster market velocity.
    Geographic level: Metro (MSA)
    """
    path = (data_dir or DATA_DIR) / "days_to_pending_metro.csv"
    df = pd.read_csv(path)
    df = _standardize_column_names(df)
    return df


def load_price_cuts(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load Metro-level Price Cuts percentage.

    Percentage of listings with a price cut.
    Higher values may indicate distress or overpricing.
    Geographic level: Metro (MSA)
    """
    path = (data_dir or DATA_DIR) / "price_cuts_metro.csv"
    df = pd.read_csv(path)
    df = _standardize_column_names(df)
    return df


def load_sale_to_list(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load Metro-level Sale-to-List ratio.

    Ratio of sale price to list price.
    Values > 1.0 indicate homes selling above asking.
    Values < 1.0 indicate homes selling below asking.
    Geographic level: Metro (MSA)
    Note: This dataset is WEEKLY (not monthly like others).
    """
    path = (data_dir or DATA_DIR) / "sale_to_list_metro.csv"
    df = pd.read_csv(path)
    df = _standardize_column_names(df)
    return df


def load_all_datasets(data_dir: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
    """
    Load all Zillow datasets into a dictionary.

    Returns:
        Dict with keys: 'zhvi_zip', 'zhvi_bottom_tier', 'market_heat',
                       'days_to_pending', 'price_cuts', 'sale_to_list'
    """
    return {
        'zhvi_zip': load_zhvi_zip(data_dir),
        'zhvi_bottom_tier': load_zhvi_bottom_tier_county(data_dir),
        'market_heat': load_market_heat_index(data_dir),
        'days_to_pending': load_days_to_pending(data_dir),
        'price_cuts': load_price_cuts(data_dir),
        'sale_to_list': load_sale_to_list(data_dir),
    }


def get_date_columns(df: pd.DataFrame) -> List[str]:
    """Get list of date columns from a dataframe."""
    return _identify_date_columns(df.columns.tolist())


def get_metadata_columns(df: pd.DataFrame) -> List[str]:
    """Get list of metadata (non-date) columns from a dataframe."""
    return _identify_metadata_columns(df.columns.tolist())


def get_date_range(df: pd.DataFrame) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """Get the date range covered by a dataframe."""
    date_cols = get_date_columns(df)
    dates = pd.to_datetime(date_cols)
    return dates.min(), dates.max()


def validate_all_datasets(datasets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Validate all datasets and return summary DataFrame.
    """
    validations = []
    for name, df in datasets.items():
        val = _validate_dataframe(df, name)
        validations.append(val)

    summary = pd.DataFrame(validations)
    summary['date_start'] = summary['date_range'].apply(lambda x: x[0])
    summary['date_end'] = summary['date_range'].apply(lambda x: x[1])
    summary = summary.drop(columns=['date_range'])

    return summary


def melt_to_long_format(df: pd.DataFrame, value_name: str = 'value') -> pd.DataFrame:
    """
    Convert wide-format Zillow data to long format.

    Transforms date columns from wide to long, creating 'date' and value columns.
    """
    date_cols = get_date_columns(df)
    meta_cols = get_metadata_columns(df)

    df_long = df.melt(
        id_vars=meta_cols,
        value_vars=date_cols,
        var_name='date',
        value_name=value_name
    )
    df_long['date'] = pd.to_datetime(df_long['date'])

    return df_long


if __name__ == "__main__":
    # Quick test
    print("Loading all datasets...")
    datasets = load_all_datasets()

    print("\nValidation Summary:")
    summary = validate_all_datasets(datasets)
    print(summary.to_string())
