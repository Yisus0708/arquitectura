"""
Reconciliation and Quality Reporting Module.
Genera el reporte integral de reconciliación por entidad:
Filas en Excel -> Válidas -> Rechazadas (con desglose de motivos) -> Normalizadas -> Cargadas en Gold.
Determina alertas si la carga está vacía o si se supera el umbral de rechazo configurable.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from src.utils.config import RAW_DATA_DIR, PROCESSED_DATA_DIR, ERRORS_DATA_DIR
from src.utils.db import fetch_query
from src.utils.logger import get_logger

logger = get_logger("reconciliation")


def generate_reconciliation_report(rejection_threshold_pct: float = 20.0) -> Dict[str, Any]:
    """
    Genera el reporte de reconciliación comparando Excel, processed, errors y Gold.
    """
    # 1. Metadatos raw
    meta_path = RAW_DATA_DIR / "ingestion_metadata.json"
    raw_counts = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                raw_counts = meta.get("raw_counts", {})
        except Exception:
            pass

    # 2. Correcciones / Normalizaciones
    corr_file = ERRORS_DATA_DIR / "corrections_log.csv"
    corr_by_entity = {}
    if corr_file.exists():
        try:
            df_corr = pd.read_csv(corr_file)
            if not df_corr.empty and "entity" in df_corr.columns:
                corr_by_entity = df_corr["entity"].value_counts().to_dict()
        except Exception:
            pass

    # 3. Gold counts
    gold_counts = {}
    try:
        gold_queries = {
            "students": "SELECT COUNT(*) AS cnt FROM gold.dim_student;",
            "courses": "SELECT COUNT(*) AS cnt FROM gold.dim_course;",
            "subjects": "SELECT COUNT(*) AS cnt FROM gold.dim_subject;",
            "grades": "SELECT COUNT(*) AS cnt FROM gold.fact_grades;",
        }
        for ent, sql in gold_queries.items():
            res = fetch_query(sql)
            gold_counts[ent] = int(res[0]["cnt"])
    except Exception:
        pass

    entities = ["courses", "subjects", "students", "assessments", "grades", "attendance"]
    entities_report = {}
    total_excel = 0
    total_valid = 0
    total_quarantined = 0
    total_normalized = 0

    for ent in entities:
        # Excel raw rows
        raw_f = RAW_DATA_DIR / f"{ent}.csv"
        excel_rows = raw_counts.get(ent)
        if excel_rows is None:
            excel_rows = len(pd.read_csv(raw_f)) if raw_f.exists() else 0

        # Valid rows in processed
        proc_f = PROCESSED_DATA_DIR / f"{ent}.csv"
        valid_rows = len(pd.read_csv(proc_f)) if proc_f.exists() else 0

        # Quarantined rows and reasons
        err_f = ERRORS_DATA_DIR / f"{ent}_errors.csv"
        quarantined_rows = 0
        reasons_breakdown = {}
        if err_f.exists():
            df_err = pd.read_csv(err_f)
            quarantined_rows = len(df_err)
            if not df_err.empty and "error_reason" in df_err.columns:
                reasons_breakdown = df_err["error_reason"].value_counts().to_dict()

        norm_rows = corr_by_entity.get(ent, 0)
        gold_rows = gold_counts.get(ent, valid_rows)

        rej_rate = round((quarantined_rows / excel_rows * 100.0), 2) if excel_rows > 0 else 0.0

        entities_report[ent] = {
            "excel_rows": excel_rows,
            "valid_rows": valid_rows,
            "quarantined_rows": quarantined_rows,
            "normalized_rows": norm_rows,
            "gold_rows": gold_rows,
            "rejection_rate_pct": rej_rate,
            "reasons": reasons_breakdown,
            "quarantine_reasons": reasons_breakdown,
        }

        total_excel += excel_rows
        total_valid += valid_rows
        total_quarantined += quarantined_rows
        total_normalized += norm_rows

    total_gold = sum(e["gold_rows"] for e in entities_report.values())
    overall_rej_rate = round((total_quarantined / total_excel * 100.0), 2) if total_excel > 0 else 0.0
    is_empty_load = (total_excel == 0) or (gold_counts.get("grades", 0) == 0)
    exceeds_threshold = overall_rej_rate > rejection_threshold_pct

    # Determine status and message
    if is_empty_load:
        status = "ERROR"
        message = "La carga quedó vacía o no contiene calificaciones válidas cargadas en Gold."
    elif exceeds_threshold:
        status = "WARNING"
        message = f"Advertencia: la tasa de rechazo global ({overall_rej_rate}%) supera el umbral configurado ({rejection_threshold_pct}%)."
    else:
        status = "SUCCESS"
        message = f"Carga procesada exitosamente con una tasa de calidad del {round(100.0 - overall_rej_rate, 2)}%."

    report = {
        "status": status,
        "message": message,
        "rejection_threshold_pct": rejection_threshold_pct,
        "overall": {
            "total_excel_rows": total_excel,
            "total_valid_rows": total_valid,
            "total_quarantined_rows": total_quarantined,
            "total_normalized_rows": total_normalized,
            "total_gold_rows": total_gold,
            "overall_rejection_rate_pct": overall_rej_rate,
            "is_empty_load": is_empty_load,
            "exceeds_threshold": exceeds_threshold,
        },
        "by_entity": entities_report,
        "entities": entities_report,
    }

    return report
