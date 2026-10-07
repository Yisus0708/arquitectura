"""
Test Suite: Raw Ingestion and Data Quality Validation.
Verifies file presence, metadata, schema conformance, error quarantine,
and processed data sanitation.
"""
import json
from pathlib import Path
import pandas as pd
import pytest

from src.utils.config import RAW_DATA_DIR, PROCESSED_DATA_DIR, ERRORS_DATA_DIR
from src.validation.validate_data import EXPECTED_SCHEMAS


def test_raw_files_and_metadata_exist():
    """Verifies that all raw files and ingestion metadata are present."""
    assert RAW_DATA_DIR.exists(), "Raw data directory does not exist"
    metadata_file = RAW_DATA_DIR / "ingestion_metadata.json"
    assert metadata_file.exists(), "ingestion_metadata.json is missing"

    with open(metadata_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert "files" in meta, "Metadata missing 'files' key"
    assert "random_seed" in meta, "Metadata missing random_seed"

    for fname in EXPECTED_SCHEMAS.keys():
        fpath = RAW_DATA_DIR / fname
        assert fpath.exists(), f"Raw file {fname} does not exist"
        assert fname in meta["files"], f"Metadata missing entry for {fname}"
        assert meta["files"][fname]["row_count"] > 0, f"Raw file {fname} is empty"


def test_expected_columns_in_raw_data():
    """Verifies that each raw CSV contains all mandatory columns."""
    for fname, cols in EXPECTED_SCHEMAS.items():
        df = pd.read_csv(RAW_DATA_DIR / fname)
        for col in cols:
            assert col in df.columns, f"Column {col} missing in {fname}"


def test_error_quarantine_has_reasons():
    """Verifies that quarantined error files exist and contain descriptive error_reason."""
    assert ERRORS_DATA_DIR.exists(), "Errors directory does not exist"
    error_files = list(ERRORS_DATA_DIR.glob("*_errors.csv"))
    assert len(error_files) > 0, "No error files found in data/errors/"

    for ef in error_files:
        df = pd.read_csv(ef)
        if not df.empty:
            assert "error_reason" in df.columns, f"error_reason column missing in {ef.name}"
            assert df["error_reason"].isnull().sum() == 0, f"Found null error_reason in {ef.name}"


def test_processed_grades_in_valid_range():
    """Verifies that processed grades only contain valid scores between 0.0 and 5.0 without nulls."""
    processed_grades_file = PROCESSED_DATA_DIR / "grades.csv"
    assert processed_grades_file.exists(), "processed grades.csv missing"

    df = pd.read_csv(processed_grades_file)
    assert not df.empty, "processed grades.csv is empty"
    assert df["score"].isnull().sum() == 0, "Null scores found in processed grades"
    assert (df["score"] < 0.0).sum() == 0, "Negative scores found in processed grades"
    assert (df["score"] > 5.0).sum() == 0, "Scores > 5.0 found in processed grades"


def test_processed_assessments_weights_sum_to_100():
    """Verifies that all subjects in processed assessments have weights summing exactly to 100%."""
    processed_evals_file = PROCESSED_DATA_DIR / "assessments.csv"
    assert processed_evals_file.exists(), "processed assessments.csv missing"

    df = pd.read_csv(processed_evals_file)
    assert not df.empty, "processed assessments.csv is empty"

    sums = df.groupby("subject_id")["weight_percentage"].sum()
    for s_id, total_w in sums.items():
        assert abs(total_w - 100.0) < 0.01, f"Subject {s_id} has weight sum {total_w} != 100%"
