"""
fixer.py
Applies structured fix_action dicts (as produced by llm_analyzer) to a
pandas DataFrame. Every function returns a *new* dataframe and a short log
string describing what changed, so actions are auditable.
"""
from __future__ import annotations

import pandas as pd


def apply_fix(df: pd.DataFrame, issue: dict) -> tuple[pd.DataFrame, str]:
    action = issue.get("fix_action", {})
    a_type = action.get("type")
    params = action.get("params", {}) or {}
    col = issue.get("column")

    df = df.copy()

    if a_type == "drop_duplicates":
        before = len(df)
        df = df.drop_duplicates()
        return df, f"Dropped {before - len(df)} duplicate row(s)."

    if a_type == "fill_missing":
        if col not in df.columns:
            return df, f"Skipped: column '{col}' not found."
        strategy = params.get("strategy", "mode")
        n_missing = int(df[col].isna().sum())
        if strategy == "mean":
            fill_value = df[col].mean()
        elif strategy == "median":
            fill_value = df[col].median()
        elif strategy == "mode":
            mode = df[col].mode(dropna=True)
            fill_value = mode.iloc[0] if not mode.empty else None
        else:  # constant
            fill_value = params.get("value")
        df[col] = df[col].fillna(fill_value)
        return df, f"Filled {n_missing} missing value(s) in '{col}' with {fill_value!r}."

    if a_type == "strip_whitespace":
        if col not in df.columns:
            return df, f"Skipped: column '{col}' not found."
        df[col] = df[col].astype(str).str.strip()
        return df, f"Stripped whitespace in '{col}'."

    if a_type == "standardize_case":
        if col not in df.columns:
            return df, f"Skipped: column '{col}' not found."
        case = params.get("case", "lower")
        s = df[col].astype(str).str.strip()
        df[col] = getattr(s.str, case)() if case in ("lower", "upper", "title") else s
        return df, f"Standardized casing in '{col}' to {case}."

    if a_type == "convert_dtype":
        if col not in df.columns:
            return df, f"Skipped: column '{col}' not found."
        to = params.get("to")
        try:
            if to == "int":
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            elif to == "float":
                df[col] = pd.to_numeric(df[col], errors="coerce")
            elif to == "datetime":
                df[col] = pd.to_datetime(df[col], errors="coerce")
            elif to == "string":
                df[col] = df[col].astype(str)
        except Exception as e:
            return df, f"Failed to convert '{col}' to {to}: {e}"
        return df, f"Converted '{col}' to {to}."

    if a_type == "clip_outliers":
        if col not in df.columns:
            return df, f"Skipped: column '{col}' not found."
        lower, upper = params.get("lower"), params.get("upper")
        df[col] = df[col].clip(lower=lower, upper=upper)
        return df, f"Clipped '{col}' to range [{lower}, {upper}]."

    if a_type == "drop_column":
        if col not in df.columns:
            return df, f"Skipped: column '{col}' not found."
        df = df.drop(columns=[col])
        return df, f"Dropped column '{col}'."

    if a_type == "rename_values":
        if col not in df.columns:
            return df, f"Skipped: column '{col}' not found."
        mapping = params.get("mapping", {})
        df[col] = df[col].replace(mapping)
        return df, f"Standardized {len(mapping)} value(s) in '{col}'."

    return df, f"No automatic fix available for action type '{a_type}' (manual review needed)."
