"""
profiler.py
Builds a compact, LLM-friendly profile of a pandas DataFrame.

We never send the *entire* dataset to the LLM (cost + privacy). Instead we
send column-level statistics plus a small sample of rows, which is usually
enough for an LLM to spot data quality issues.
"""
from __future__ import annotations

import json
import pandas as pd
import numpy as np


def _series_profile(col: pd.Series) -> dict:
    profile = {
        "dtype": str(col.dtype),
        "missing_count": int(col.isna().sum()),
        "missing_pct": round(float(col.isna().mean()) * 100, 2),
        "unique_count": int(col.nunique(dropna=True)),
    }

    non_null = col.dropna()

    if pd.api.types.is_numeric_dtype(col):
        if len(non_null) > 0:
            desc = non_null.describe()
            profile.update(
                {
                    "min": float(desc.get("min", np.nan)),
                    "max": float(desc.get("max", np.nan)),
                    "mean": round(float(desc.get("mean", np.nan)), 4),
                    "std": round(float(desc.get("std", np.nan)), 4),
                }
            )
            # simple IQR-based outlier count
            q1, q3 = non_null.quantile(0.25), non_null.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                outliers = non_null[(non_null < lower) | (non_null > upper)]
                profile["outlier_count"] = int(len(outliers))
                profile["outlier_examples"] = outliers.head(5).tolist()
    else:
        # categorical / text / dates-as-strings
        value_counts = non_null.astype(str).value_counts().head(8)
        profile["top_values"] = value_counts.to_dict()
        profile["sample_values"] = non_null.astype(str).unique()[:8].tolist()
        # possible inconsistent casing / whitespace
        stripped_lower = non_null.astype(str).str.strip().str.lower()
        variant_groups = stripped_lower.value_counts()
        raw_variants = non_null.astype(str).value_counts()
        if len(raw_variants) > len(variant_groups):
            profile["possible_case_or_whitespace_dupes"] = True

    return profile


def build_profile(df: pd.DataFrame, sample_rows: int = 8) -> dict:
    """Return a JSON-serializable profile of the dataframe."""
    profile = {
        "n_rows": int(len(df)),
        "n_columns": int(len(df.columns)),
        "duplicate_row_count": int(df.duplicated().sum()),
        "columns": {},
        "sample_rows": json.loads(
            df.head(sample_rows).to_json(orient="records", date_format="iso")
        ),
    }
    for col in df.columns:
        profile["columns"][str(col)] = _series_profile(df[col])
    return profile


def profile_to_prompt_text(profile: dict) -> str:
    """Render the profile dict as compact text for the LLM prompt."""
    return json.dumps(profile, indent=2, default=str)
