"""
Utilities for loading and validating experimental data.
"""

from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import numpy as np


REQUIRED_COLUMNS = {
    "energy": ["Energy_MeV", "energy_MeV", "E_MeV", "energy"],
    "ks": ["k_s", "ks", "recombination_factor", "collection_efficiency"],
    "dose_rate_air": ["dose_rate_air_Gy_s", "dose_rate_air", "doserate_air_Gy_s"],
    "dose_rate_water": ["dose_rate_water_Gy_s", "dose_rate_water", "doserate_water_Gy_s"],
}


def find_column(df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
    """
    Find a column in DataFrame by trying multiple possible names.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to search
    possible_names : List[str]
        List of possible column names
        
    Returns
    -------
    Optional[str]
        Found column name or None
    """
    for name in possible_names:
        if name in df.columns:
            return name
    return None


def validate_experimental_data(
    df: pd.DataFrame,
    energy_column: str,
    ks_column: str,
    dose_rate_column: str,
) -> tuple[bool, List[str]]:
    """
    Validate experimental data DataFrame.
    
    Parameters
    ----------
    df : pd.DataFrame
        Experimental data DataFrame
    energy_column : str
        Name of energy column
    ks_column : str
        Name of k_s column
    dose_rate_column : str
        Name of dose rate column
        
    Returns
    -------
    Tuple[bool, List[str]]
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required columns exist
    required = [energy_column, ks_column, dose_rate_column]
    missing = [col for col in required if col not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {missing}")
        return False, errors
    
    # Check for empty DataFrame
    if len(df) == 0:
        errors.append("DataFrame is empty")
        return False, errors
    
    # Check for NaN values in required columns
    for col in required:
        nan_count = df[col].isna().sum()
        if nan_count > 0:
            errors.append(f"Column '{col}' contains {nan_count} NaN values")
    
    # Check data types and ranges
    if not pd.api.types.is_numeric_dtype(df[energy_column]):
        errors.append(f"Column '{energy_column}' must be numeric")
    else:
        if (df[energy_column] <= 0).any():
            errors.append(f"Column '{energy_column}' contains non-positive values")
    
    if not pd.api.types.is_numeric_dtype(df[ks_column]):
        errors.append(f"Column '{ks_column}' must be numeric")
    else:
        if (df[ks_column] <= 0).any():
            errors.append(f"Column '{ks_column}' contains non-positive values")
    
    if not pd.api.types.is_numeric_dtype(df[dose_rate_column]):
        errors.append(f"Column '{dose_rate_column}' must be numeric")
    else:
        if (df[dose_rate_column] < 0).any():
            errors.append(f"Column '{dose_rate_column}' contains negative values")
    
    return len(errors) == 0, errors


def load_experimental_data(
    data_path: Path,
    energy_column: Optional[str] = None,
    ks_column: Optional[str] = None,
    dose_rate_column: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load and validate experimental data from CSV file.
    
    Parameters
    ----------
    data_path : Path
        Path to CSV file with experimental data
    energy_column : Optional[str]
        Name of energy column (auto-detected if None)
    ks_column : Optional[str]
        Name of k_s column (auto-detected if None)
    dose_rate_column : Optional[str]
        Name of dose rate column (auto-detected if None)
        
    Returns
    -------
    pd.DataFrame
        Loaded and validated experimental data
        
    Raises
    ------
    FileNotFoundError
        If data file doesn't exist
    ValueError
        If data validation fails
    """
    data_path = Path(data_path)
    
    if not data_path.exists():
        raise FileNotFoundError(f"Experimental data file not found: {data_path}")
    
    # Load CSV
    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        raise ValueError(f"Failed to load CSV file: {e}")
    
    # Auto-detect columns if not specified
    if energy_column is None:
        energy_column = find_column(df, REQUIRED_COLUMNS["energy"])
        if energy_column is None:
            raise ValueError(
                f"Could not find energy column. Tried: {REQUIRED_COLUMNS['energy']}"
            )
    
    if ks_column is None:
        ks_column = find_column(df, REQUIRED_COLUMNS["ks"])
        if ks_column is None:
            raise ValueError(
                f"Could not find k_s column. Tried: {REQUIRED_COLUMNS['ks']}"
            )
    
    if dose_rate_column is None:
        # Try air first, then water
        dose_rate_column = find_column(df, REQUIRED_COLUMNS["dose_rate_air"])
        if dose_rate_column is None:
            dose_rate_column = find_column(df, REQUIRED_COLUMNS["dose_rate_water"])
        if dose_rate_column is None:
            raise ValueError(
                f"Could not find dose rate column. Tried: "
                f"{REQUIRED_COLUMNS['dose_rate_air'] + REQUIRED_COLUMNS['dose_rate_water']}"
            )
    
    # Validate data
    is_valid, errors = validate_experimental_data(
        df, energy_column, ks_column, dose_rate_column
    )
    
    if not is_valid:
        error_msg = "Data validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)
    
    # Standardize column names for internal use
    df = df.copy()
    df.rename(
        columns={
            energy_column: "Energy_MeV",
            ks_column: "k_s",
            dose_rate_column: "dose_rate_Gy_s",
        },
        inplace=True,
    )
    
    # Convert dose rate to Gy/min if needed (for continuous beam calculations)
    if "dose_rate_Gy_min" not in df.columns:
        df["dose_rate_Gy_min"] = df["dose_rate_Gy_s"] * 60
    
    print(f"✓ Loaded {len(df)} experimental measurements")
    print(f"  Energy column: {energy_column} → Energy_MeV")
    print(f"  k_s column: {ks_column} → k_s")
    print(f"  Dose rate column: {dose_rate_column} → dose_rate_Gy_s")
    print(f"  Energies: {sorted(df['Energy_MeV'].unique())} MeV")
    
    return df

