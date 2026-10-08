"""
Módulo de perfilado de archivos Excel para ingesta académica.
Analiza hojas, columnas, tipos de datos inferidos, nulos, unicidad, rangos y fechas.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import re
from datetime import datetime, date


def _to_float_if_possible(val: Any) -> Optional[float]:
    if pd.isna(val):
        return None
    if isinstance(val, (int, float, np.integer, np.floating)):
        return float(val)
    if isinstance(val, str):
        v = val.strip().replace(",", ".")
        try:
            return float(v)
        except ValueError:
            return None
    return None


def infer_column_profile(series: pd.Series) -> Dict[str, Any]:
    total_rows = len(series)
    non_null_mask = series.notna() & (series.astype(str).str.strip().ne("")) & (series.astype(str).ne("nan"))
    valid_series = series[non_null_mask]
    null_count = total_rows - len(valid_series)
    null_pct = round((null_count / total_rows * 100.0), 2) if total_rows > 0 else 0.0

    if len(valid_series) == 0:
        return {
            "name": str(series.name),
            "inferred_type": "empty",
            "total_rows": total_rows,
            "null_count": null_count,
            "null_percentage": null_pct,
            "unique_count": 0,
            "is_unique": False,
            "min_val": None,
            "max_val": None,
            "sample_values": [],
            "has_comma_floats": False,
        }

    # Detect comma floats across entire series
    str_series = valid_series.astype(str).str.strip()
    comma_mask = str_series.str.contains(r"^-?\d+,\d+$", regex=True)
    has_comma_floats = bool(comma_mask.any())

    # Sample check / conversion for type detection
    # If series is large, sample up to 1000 items + all comma matches for robust type checking
    if len(valid_series) > 1000:
        sample_for_type = pd.concat([valid_series.iloc[:1000], valid_series[comma_mask]])
    else:
        sample_for_type = valid_series

    numeric_count = 0
    date_count = 0
    bool_count = 0
    normalized_numeric_vals = []
    normalized_date_vals = []

    for v in sample_for_type:
        if isinstance(v, (bool, np.bool_)):
            bool_count += 1
        elif isinstance(v, (datetime, date, pd.Timestamp)):
            date_count += 1
            normalized_date_vals.append(pd.to_datetime(v))
        else:
            num = _to_float_if_possible(v)
            if num is not None:
                numeric_count += 1
                normalized_numeric_vals.append(num)
            else:
                v_str = str(v).strip()
                if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", v_str) or re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}", v_str):
                    try:
                        d = pd.to_datetime(v_str, errors="raise")
                        date_count += 1
                        normalized_date_vals.append(d)
                        continue
                    except Exception:
                        pass

    n_sample = len(sample_for_type)
    inferred_type = "string"
    min_val = None
    max_val = None

    if numeric_count / n_sample >= 0.8:
        # Numeric
        all_int = all(float(x).is_integer() for x in normalized_numeric_vals) if normalized_numeric_vals else False
        inferred_type = "integer" if all_int else "float"
        # Calculate min and max across all series converting safely
        converted_series = valid_series.apply(_to_float_if_possible).dropna()
        if len(converted_series) > 0:
            min_val = float(converted_series.min())
            max_val = float(converted_series.max())
    elif date_count / n_sample >= 0.8:
        inferred_type = "date"
        try:
            converted_dates = pd.to_datetime(valid_series, errors="coerce").dropna()
            if len(converted_dates) > 0:
                min_val = str(converted_dates.min().date())
                max_val = str(converted_dates.max().date())
        except Exception:
            pass
    elif bool_count / n_sample >= 0.8:
        inferred_type = "boolean"

    unique_vals = valid_series.drop_duplicates()
    unique_count = len(unique_vals)
    is_unique = (unique_count == len(valid_series)) and (len(valid_series) > 0)

    # Samples (up to 5)
    sample_list = [str(x) for x in unique_vals.iloc[:5].tolist()]

    return {
        "name": str(series.name),
        "inferred_type": inferred_type,
        "total_rows": total_rows,
        "null_count": null_count,
        "null_percentage": null_pct,
        "unique_count": unique_count,
        "is_unique": is_unique,
        "min_val": min_val,
        "max_val": max_val,
        "sample_values": sample_list,
        "has_comma_floats": has_comma_floats,
    }


def profile_dataframe(df: pd.DataFrame, sheet_name: str = "Sheet1") -> Dict[str, Any]:
    columns_profile = {}
    for col in df.columns:
        col_str = str(col).strip()
        columns_profile[col_str] = infer_column_profile(df[col])

    return {
        "sheet_name": sheet_name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns_profile,
    }


def profile_workbook(file_path_or_buffer: Any) -> Dict[str, Any]:
    """
    Lee un archivo Excel y perfila cada una de sus hojas.
    """
    excel_file = pd.ExcelFile(file_path_or_buffer)
    sheets_profile = {}

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        sheets_profile[sheet_name] = profile_dataframe(df, sheet_name=sheet_name)

    return {
        "sheet_names": excel_file.sheet_names,
        "sheet_count": len(excel_file.sheet_names),
        "sheets": sheets_profile,
    }
