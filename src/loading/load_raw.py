"""
Raw Data Loader Module.
Loads raw CSV data into PostgreSQL raw schema tables faithfully as TEXT columns,
adding ingestion metadata (_loaded_at, _source_file).
Ensures idempotency by executing within transactions and clearing prior batch data.
"""
import sys
from pathlib import Path
from typing import Dict
import pandas as pd
import psycopg2

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import RAW_DATA_DIR, SQL_DIR
from src.utils.db import get_connection, execute_sql_file
from src.utils.logger import get_logger

logger = get_logger("load_raw")

RAW_TABLES = [
    ("courses.csv", "raw.courses", ["course_id", "course_name", "grade_level", "academic_year"]),
    ("subjects.csv", "raw.subjects", ["subject_id", "subject_name", "course_id", "department"]),
    ("students.csv", "raw.students", ["student_id", "first_name", "last_name", "email", "course_id", "enrollment_date", "status"]),
    ("assessments.csv", "raw.assessments", ["assessment_id", "subject_id", "assessment_name", "assessment_type", "weight_percentage", "assessment_date"]),
    ("grades.csv", "raw.grades", ["grade_id", "assessment_id", "student_id", "score", "submission_date", "feedback"]),
]


def create_raw_tables() -> None:
    """Creates the raw schema tables via DDL script."""
    ddl_path = Path(__file__).resolve().parent.parent.parent / "sql" / "raw" / "01_create_raw_tables.sql"
    execute_sql_file(ddl_path)
    logger.info("Raw schema tables created/verified successfully.")


def load_csv_to_raw_table(conn, filename: str, table_name: str, columns: list) -> int:
    """Loads a single CSV file into a raw table using batch insert."""
    file_path = RAW_DATA_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Raw file not found: {file_path}")

    df = pd.read_csv(file_path, dtype=str)  # Read all as string for faithful raw copy

    cur = conn.cursor()
    # Idempotent load: truncate table before inserting new raw batch
    cur.execute(f"TRUNCATE TABLE {table_name};")

    col_names = ", ".join(columns) + ", _source_file"
    placeholders = ", ".join(["%s"] * (len(columns) + 1))
    insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"

    rows_to_insert = []
    for _, row in df.iterrows():
        row_values = [row.get(col) if pd.notnull(row.get(col)) else None for col in columns]
        row_values.append(filename)
        rows_to_insert.append(tuple(row_values))

    cur.executemany(insert_sql, rows_to_insert)
    inserted_count = len(rows_to_insert)
    cur.close()

    logger.info(f"Loaded {inserted_count} records into {table_name} from {filename}")
    return inserted_count


def load_all_raw() -> Dict[str, int]:
    """Runs end-to-end raw loading pipeline."""
    logger.info("Starting ingestion into PostgreSQL raw schema...")
    create_raw_tables()

    conn = get_connection()
    results = {}
    try:
        for filename, table_name, columns in RAW_TABLES:
            count = load_csv_to_raw_table(conn, filename, table_name, columns)
            results[table_name] = count
        conn.commit()
        logger.info("All raw tables loaded and transaction committed successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading raw data into database: {e}")
        raise
    finally:
        conn.close()

    return results


if __name__ == "__main__":
    load_all_raw()
