"""
Airflow DAG: School Grades Medallion Data Pipeline
Orchestrates the end-to-end flow:
generate_data -> validate_raw -> load_raw -> transform_staging -> build_silver -> build_gold -> run_quality_tests -> pipeline_success

Features:
- Structured task dependencies
- Retries and backoff policies
- Execution timeouts
- Comprehensive step-by-step logging
"""
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to sys.path so Airflow workers can locate src modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    try:
        from airflow.operators.empty import EmptyOperator
    except ImportError:
        from airflow.operators.dummy import DummyOperator as EmptyOperator
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False


def task_generate_data():
    from src.ingestion.generate_data import main as generate_main
    generate_main()


def task_validate_raw():
    from src.validation.validate_data import run_validation
    summary = run_validation()
    if not summary:
        raise ValueError("Validation failed to produce summary metrics.")


def task_load_raw():
    from src.loading.load_raw import load_all_raw
    load_all_raw()


def task_transform_staging():
    from src.transformation.transform_staging import run_staging_transformations
    run_staging_transformations()


def task_build_silver():
    from src.transformation.transform_silver import run_silver_transformations
    run_silver_transformations()


def task_build_gold():
    from src.transformation.transform_gold import run_gold_transformations
    run_gold_transformations()


def task_run_quality_tests():
    import pytest
    tests_dir = str(PROJECT_ROOT / "tests")
    exit_code = pytest.main(["-v", tests_dir])
    if exit_code != 0:
        raise RuntimeError(f"Quality assurance pytest suite failed with exit code {exit_code}")


default_args = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=15),
}

if AIRFLOW_AVAILABLE:
    with DAG(
        dag_id="school_grades_data_pipeline",
        default_args=default_args,
        description="End-to-end Medallion School Grading Pipeline (Raw -> Staging -> Silver -> Gold)",
        schedule_interval="@daily",
        catchup=False,
        tags=["school", "grades", "medallion", "postgresql", "portfolio"],
    ) as dag:

        generate_step = PythonOperator(
            task_id="generate_data",
            python_callable=task_generate_data,
        )

        validate_step = PythonOperator(
            task_id="validate_raw",
            python_callable=task_validate_raw,
        )

        load_raw_step = PythonOperator(
            task_id="load_raw",
            python_callable=task_load_raw,
        )

        staging_step = PythonOperator(
            task_id="transform_staging",
            python_callable=task_transform_staging,
        )

        silver_step = PythonOperator(
            task_id="build_silver",
            python_callable=task_build_silver,
        )

        gold_step = PythonOperator(
            task_id="build_gold",
            python_callable=task_build_gold,
        )

        quality_tests_step = PythonOperator(
            task_id="run_quality_tests",
            python_callable=task_run_quality_tests,
        )

        pipeline_success = EmptyOperator(
            task_id="pipeline_success",
        )

        # Pipeline DAG linear orchestration flow
        (
            generate_step
            >> validate_step
            >> load_raw_step
            >> staging_step
            >> silver_step
            >> gold_step
            >> quality_tests_step
            >> pipeline_success
        )
