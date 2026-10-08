"""
Test Suite: PostgreSQL Relational Integrity & Schema Validation.
Verifies table presence, non-null constraints, unique PKs, and check constraints
across staging and silver schemas.
"""
import pytest
from src.utils.db import fetch_query


def test_database_connection_and_schemas():
    """Verifies that database connection is active and all schemas exist."""
    res = fetch_query("SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('raw', 'staging', 'silver', 'gold');")
    found_schemas = {r["schema_name"] for r in res}
    assert found_schemas == {"raw", "staging", "silver", "gold"}, f"Missing schemas: {{'raw', 'staging', 'silver', 'gold'}} - {found_schemas}"


def test_no_duplicate_pks_in_silver():
    """Verifies that all primary keys in silver schema are strictly unique."""
    tables_pks = [
        ("silver.courses", "course_id"),
        ("silver.subjects", "subject_id"),
        ("silver.students", "student_id"),
        ("silver.assessments", "assessment_id"),
        ("silver.grades", "grade_id"),
    ]
    for table, pk in tables_pks:
        sql = f"""
            SELECT {pk}, COUNT(*) AS cnt
            FROM {table}
            GROUP BY {pk}
            HAVING COUNT(*) > 1;
        """
        dups = fetch_query(sql)
        assert len(dups) == 0, f"Duplicate PKs found in {table}: {dups}"


def test_no_unexpected_nulls_in_silver_mandatory_fields():
    """Verifies that mandatory columns in silver contain no nulls."""
    checks = [
        ("silver.courses", ["course_id", "course_name"]),
        ("silver.subjects", ["subject_id", "subject_name"]),
        ("silver.students", ["student_id", "first_name", "last_name"]),
        ("silver.assessments", ["assessment_id", "assessment_name", "weight_percentage"]),
        ("silver.grades", ["grade_id", "assessment_id", "student_id", "score"]),
    ]
    for table, cols in checks:
        for col in cols:
            sql = f"SELECT COUNT(*) AS null_cnt FROM {table} WHERE {col} IS NULL;"
            res = fetch_query(sql)
            null_count = res[0]["null_cnt"]
            assert null_count == 0, f"Found {null_count} nulls in {table}.{col}"


def test_silver_grade_scores_within_range():
    """Verifies that all scores in silver.grades are strictly within [0.0 - 5.0]."""
    sql = """
        SELECT COUNT(*) AS out_of_bounds
        FROM silver.grades
        WHERE score < 0.0 OR score > 5.0;
    """
    res = fetch_query(sql)
    assert res[0]["out_of_bounds"] == 0, "Found scores outside 0.0 - 5.0 in silver.grades"


def test_silver_assessment_weights_within_range():
    """Verifies that all weights in silver.assessments are strictly within [0.0 - 100.0]."""
    sql = """
        SELECT COUNT(*) AS out_of_bounds
        FROM silver.assessments
        WHERE weight_percentage < 0.0 OR weight_percentage > 100.0;
    """
    res = fetch_query(sql)
    assert res[0]["out_of_bounds"] == 0, "Found weights outside 0 - 100 in silver.assessments"
