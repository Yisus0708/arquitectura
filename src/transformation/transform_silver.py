"""
Silver Layer Transformation Module.
Executes relational modeling DDL with PK, FK, NOT NULL, and CHECK constraints,
and idempotently populates silver layer tables using UPSERT (ON CONFLICT DO UPDATE).
"""
import sys
from pathlib import Path
from typing import Dict

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.db import execute_sql_file, fetch_query
from src.utils.logger import get_logger

logger = get_logger("transform_silver")


def run_silver_transformations() -> Dict[str, int]:
    """Runs DDL and DML transformations for the silver relational layer."""
    logger.info("Executing silver layer DDL and population...")
    sql_dir = Path(__file__).resolve().parent.parent.parent / "sql" / "silver"

    # 1. DDL with constraints
    execute_sql_file(sql_dir / "01_create_silver_tables.sql")

    # 2. Population with UPSERT
    execute_sql_file(sql_dir / "02_populate_silver.sql")

    # Audit counts
    tables = [
        "silver.courses",
        "silver.subjects",
        "silver.students",
        "silver.assessments",
        "silver.grades"
    ]
    counts = {}
    for tbl in tables:
        res = fetch_query(f"SELECT COUNT(*) AS cnt FROM {tbl};")
        cnt = res[0]["cnt"]
        counts[tbl] = cnt
        logger.info(f"Table {tbl:22}: {cnt} validated records.")

    logger.info("Silver layer populated and relational constraints active.")
    return counts


if __name__ == "__main__":
    run_silver_transformations()
