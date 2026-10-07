"""
Staging Transformation Module.
Creates staging schema tables and executes SQL transformations from raw to staging:
- Type casting
- Whitespace stripping
- Referential filtering
- Business rule enforcement (weights sum to 100%, scores 0.0-5.0)
- PK deduplication
"""
import sys
from pathlib import Path
from typing import Dict

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.db import execute_sql_file, fetch_query
from src.utils.logger import get_logger

logger = get_logger("transform_staging")


def run_staging_transformations() -> Dict[str, int]:
    """Runs DDL and DML transformations for staging schema."""
    logger.info("Executing staging DDL and transformations...")
    sql_dir = Path(__file__).resolve().parent.parent.parent / "sql" / "staging"

    # 1. Create tables
    execute_sql_file(sql_dir / "01_create_staging_tables.sql")

    # 2. Transform and load into staging
    execute_sql_file(sql_dir / "02_transform_staging.sql")

    # Audit counts
    tables = [
        "staging.courses",
        "staging.subjects",
        "staging.students",
        "staging.assessments",
        "staging.grades"
    ]
    counts = {}
    for tbl in tables:
        res = fetch_query(f"SELECT COUNT(*) AS cnt FROM {tbl};")
        cnt = res[0]["cnt"]
        counts[tbl] = cnt
        logger.info(f"Table {tbl:22}: {cnt} rows populated.")

    logger.info("Staging transformation completed successfully.")
    return counts


if __name__ == "__main__":
    run_staging_transformations()
