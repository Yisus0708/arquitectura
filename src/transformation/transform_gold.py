"""
Gold Layer Transformation Module.
Builds the analytical star schema and business marts in PostgreSQL:
- Dimensions: dim_student, dim_course, dim_subject, dim_date
- Fact: fact_grades
- Marts:
  * final_grade_by_student_subject
  * subject_performance
  * student_performance
  * course_performance
  * assessment_type_performance
  * top_bottom_students
  * subjects_highest_failure
"""
import sys
from pathlib import Path
from typing import Dict

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.db import execute_sql_file, fetch_query
from src.utils.logger import get_logger

logger = get_logger("transform_gold")


def run_gold_transformations() -> Dict[str, int]:
    """Runs DDL and population for the gold layer."""
    logger.info("Executing gold layer star schema and analytical marts...")
    sql_dir = Path(__file__).resolve().parent.parent.parent / "sql" / "gold"

    # 1. DDL Star Schema
    execute_sql_file(sql_dir / "01_create_gold_star_schema.sql")

    # 2. Marts and Facts Population
    execute_sql_file(sql_dir / "02_create_gold_analytical_marts.sql")

    # Audit counts
    gold_entities = [
        "gold.dim_student",
        "gold.dim_course",
        "gold.dim_subject",
        "gold.dim_date",
        "gold.fact_grades",
        "gold.final_grade_by_student_subject",
        "gold.subject_performance",
        "gold.student_performance",
        "gold.course_performance",
        "gold.assessment_type_performance",
        "gold.top_bottom_students",
        "gold.subjects_highest_failure",
    ]

    counts = {}
    for tbl in gold_entities:
        res = fetch_query(f"SELECT COUNT(*) AS cnt FROM {tbl};")
        cnt = res[0]["cnt"]
        counts[tbl] = cnt
        logger.info(f"Gold table/mart {tbl:36}: {cnt:5} records.")

    logger.info("Gold analytical layer successfully populated and ready for BI consumption.")
    return counts


if __name__ == "__main__":
    run_gold_transformations()
