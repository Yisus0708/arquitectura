"""
Tests for FastAPI Web Application Endpoints:
- /api/preview-mapping
- /api/confirm-and-process
- /api/reconciliation-report
- /api/reset-data
- GET / (HTML Dashboard)
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app_web import app

client = TestClient(app)
ROOT_DIR = Path(__file__).resolve().parent.parent
TEST_FILE = ROOT_DIR / "data" / "colegio_test_completo.xlsx"


def test_homepage_html_rendered():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Reconciliación" in response.text
    assert "Previsualizar Mapeo" in response.text


def test_api_preview_mapping():
    assert TEST_FILE.exists(), f"Missing test file: {TEST_FILE}"
    with open(TEST_FILE, "rb") as f:
        response = client.post(
            "/api/preview-mapping",
            files={"file": ("colegio_test_completo.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    preview = data["preview"]
    assert len(preview["sheets"]) == 12
    assert preview["detected_parameters"]["grade_scale"] == "0-5"
    assert preview["detected_parameters"]["min_passing_grade"] == 3.0
    assert preview["detected_parameters"]["weight_grouping_rule"] == "(materia, periodo)"


def test_api_confirm_and_process_and_reconciliation():
    import json
    assert TEST_FILE.exists()
    # 1. First get preview mapping
    with open(TEST_FILE, "rb") as f:
        res_prev = client.post(
            "/api/preview-mapping",
            files={"file": ("colegio_test_completo.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    assert res_prev.status_code == 200
    preview = res_prev.json()["preview"]

    # 2. Confirm and process using serialized mapping_json exactly as browser does
    with open(TEST_FILE, "rb") as f:
        response = client.post(
            "/api/confirm-and-process",
            files={"file": ("colegio_test_completo.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"rejection_threshold_pct": "20.0", "mapping_json": json.dumps(preview)}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"].lower() in ("success", "warning")
    recon = data["reconciliation"]
    assert "overall" in recon
    assert recon["overall"]["total_excel_rows"] > 0
    assert recon["overall"]["total_gold_rows"] > 0
    assert "entities" in recon
    assert "students" in recon["entities"]
    assert "assessments" in recon["entities"]
    assert "grades" in recon["entities"]

    # Test GET /api/reconciliation-report
    res_recon = client.get("/api/reconciliation-report")
    assert res_recon.status_code == 200
    report_data = res_recon.json()
    assert report_data["overall"]["total_excel_rows"] == recon["overall"]["total_excel_rows"]


def test_api_reset_data():
    response = client.post("/api/reset-data")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify metrics return 0 students after reset
    res_metrics = client.get("/api/metrics")
    assert res_metrics.status_code == 200
    metrics_data = res_metrics.json()
    assert metrics_data["kpis"]["total_students"] == 0

    # Restore dataset for subsequent test modules
    if TEST_FILE.exists():
        with open(TEST_FILE, "rb") as f:
            client.post(
                "/api/confirm-and-process",
                files={"file": ("colegio_test_completo.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )
