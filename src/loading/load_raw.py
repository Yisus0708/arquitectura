"""
Raw Data Loader Module.
Carga datos CSV raw en PostgreSQL esquema raw con tipos TEXT,
metadatos de auditoría (_loaded_at, _source_file) y soporte para columna 'extra'.
Utiliza inserción por lotes de alto rendimiento (execute_values) e idempotencia total.
"""
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import RAW_DATA_DIR
from src.utils.db import get_connection, execute_sql_file
from src.utils.logger import get_logger

logger = get_logger("load_raw")

RAW_TABLE_CONFIGS = [
    ("courses.csv", "raw.courses", ["course_id", "course_name", "grade_level", "academic_year", "extra"]),
    ("subjects.csv", "raw.subjects", ["subject_id", "subject_name", "course_id", "department", "extra"]),
    ("students.csv", "raw.students", ["student_id", "document_number", "first_name", "last_name", "gender", "birth_date", "email", "course_id", "enrollment_date", "status", "extra"]),
    ("assessments.csv", "raw.assessments", ["assessment_id", "course_id", "subject_id", "period_id", "assessment_name", "assessment_type", "weight_percentage", "assessment_date", "extra"]),
    ("grades.csv", "raw.grades", ["grade_id", "assessment_id", "student_id", "score", "submission_date", "feedback", "extra"]),
    ("periods.csv", "raw.periods", ["period_id", "period_name", "start_date", "end_date", "weight", "extra"]),
    ("attendance.csv", "raw.attendance", ["attendance_id", "student_id", "course_id", "period_id", "total_classes", "absences", "extra"]),
]


def create_raw_tables() -> None:
    """Crea o reinicia las tablas raw mediante el script DDL oficial."""
    ddl_path = Path(__file__).resolve().parent.parent.parent / "sql" / "raw" / "01_create_raw_tables.sql"
    execute_sql_file(ddl_path)
    logger.info("Tablas del esquema RAW creadas y verificadas exitosamente.")


def load_csv_to_raw_table(conn, filename: str, table_name: str, columns: list) -> int:
    file_path = RAW_DATA_DIR / filename
    if not file_path.exists():
        # Archivo opcional no presente: ignorar silenciosamente
        return 0

    df = pd.read_csv(file_path, dtype=str)
    if df.empty:
        return 0

    cur = conn.cursor()
    cur.execute(f"TRUNCATE TABLE {table_name};")

    col_names = ", ".join(columns) + ", _source_file"
    insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES %s"

    rows_to_insert = []
    for _, row in df.iterrows():
        row_values = [str(row[col]) if (col in df.columns and pd.notnull(row[col]) and str(row[col]).strip() not in ("", "nan", "None")) else None for col in columns]
        row_values.append(filename)
        rows_to_insert.append(tuple(row_values))

    # Carga de alto rendimiento con execute_values en lotes de 5000
    execute_values(cur, insert_sql, rows_to_insert, page_size=5000)
    inserted_count = len(rows_to_insert)
    cur.close()

    logger.info(f"Cargados {inserted_count} registros en {table_name} desde {filename}")
    return inserted_count


def load_all_raw() -> Dict[str, int]:
    logger.info("Iniciando carga limpia a PostgreSQL esquema raw...")
    create_raw_tables()

    conn = get_connection()
    results = {}
    try:
        for filename, table_name, columns in RAW_TABLE_CONFIGS:
            count = load_csv_to_raw_table(conn, filename, table_name, columns)
            results[table_name] = count
        conn.commit()
        logger.info("Todas las tablas raw fueron cargadas y la transacción confirmada.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error cargando datos raw: {e}")
        raise
    finally:
        conn.close()

    return results


if __name__ == "__main__":
    res = load_all_raw()
    print("Resultado carga raw:", res)
