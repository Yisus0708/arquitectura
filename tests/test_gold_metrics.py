"""
Test Suite: Gold Analytical Metrics, Star Schema, and Power BI Requirements.
Verifies:
- Gold tables are not empty
- Evaluation weights sum exactly to 100% per subject
- Recalculated weighted final grades equal stored gold final grades
- Pass rate % + Fail rate % = 100% in subject and course performance marts
"""
import pytest
from src.utils.db import fetch_query


def test_gold_tables_not_empty():
    """Verifies that all analytical gold tables and marts contain records."""
    tables = [
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
    for table in tables:
        sql = f"SELECT COUNT(*) AS cnt FROM {table};"
        res = fetch_query(sql)
        cnt = res[0]["cnt"]
        assert cnt > 0, f"Gold table {table} is unexpectedly empty!"


def test_assessment_weights_sum_to_100_in_gold():
    """Verifies that every subject evaluated in gold has total weights summing to 100.0%."""
    sql = """
        SELECT DISTINCT total_evaluated_weight
        FROM gold.final_grade_by_student_subject;
    """
    res = fetch_query(sql)
    for r in res:
        w = float(r["total_evaluated_weight"])
        assert abs(w - 100.0) < 0.01, f"Found subject with total weight {w} != 100.0% in gold"


def test_recalculated_final_grade_equals_gold_final_grade():
    """
    Critical business test:
    Recalculates final grade directly from individual scores: SUM(score * weight / 100.0)
    and compares it against the stored final_grade in gold.final_grade_by_student_subject.
    """
    sql = """
        WITH recalculated AS (
            SELECT
                student_id,
                subject_id,
                ROUND(SUM(score * weight_percentage / 100.0), 2) AS calc_final_grade
            FROM gold.fact_grades
            GROUP BY student_id, subject_id
        )
        SELECT
            g.student_id,
            g.subject_id,
            g.final_grade AS stored_final_grade,
            r.calc_final_grade
        FROM gold.final_grade_by_student_subject g
        INNER JOIN recalculated r
            ON g.student_id = r.student_id AND g.subject_id = r.subject_id
        WHERE ABS(g.final_grade - r.calc_final_grade) > 0.01;
    """
    discrepancies = fetch_query(sql)
    assert len(discrepancies) == 0, f"Found {len(discrepancies)} discrepancies between recalculated and gold grades: {discrepancies}"


def test_subject_performance_pass_plus_fail_rates_equal_100():
    """
    Verifies the mathematical identity:
    pass_rate_percentage + fail_rate_percentage = 100.0%
    for every subject in gold.subject_performance.
    """
    sql = """
        SELECT
            subject_id,
            pass_rate_percentage,
            fail_rate_percentage,
            (pass_rate_percentage + fail_rate_percentage) AS total_rate
        FROM gold.subject_performance;
    """
    res = fetch_query(sql)
    for r in res:
        total = float(r["total_rate"])
        assert abs(total - 100.0) < 0.05, f"Subject {r['subject_id']} rates do not sum to 100%: {total}%"


def test_course_performance_pass_plus_fail_rates_equal_100():
    """
    Verifies that overall_pass_rate_percentage + overall_fail_rate_percentage = 100.0%
    for every course in gold.course_performance.
    """
    sql = """
        SELECT
            course_id,
            overall_pass_rate_percentage,
            overall_fail_rate_percentage,
            (overall_pass_rate_percentage + overall_fail_rate_percentage) AS total_rate
        FROM gold.course_performance;
    """
    res = fetch_query(sql)
    for r in res:
        total = float(r["total_rate"])
        assert abs(total - 100.0) < 0.05, f"Course {r['course_id']} rates do not sum to 100%: {total}%"


def test_student_gpa_within_bounds():
    """Verifies that all overall averages in student_performance are within [0.0 - 5.0]."""
    sql = """
        SELECT COUNT(*) AS invalid_gpa
        FROM gold.student_performance
        WHERE overall_average < 0.0 OR overall_average > 5.0;
    """
    res = fetch_query(sql)
    assert res[0]["invalid_gpa"] == 0, "Found student overall_average outside [0.0 - 5.0]"
