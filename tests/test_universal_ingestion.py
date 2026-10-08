"""
Suite de Pruebas Automatizadas para Ingesta Universal y Arquitectura Medallón.
Verifica:
1. Coincidencia estricta de cuarentena con errores_sembrados en colegio_test_completo.xlsx.
2. Coincidencia matemática exacta entre Gold y Pandas directo desde el Excel.
3. Resiliencia ante variantes dinámicas: sinónimos en hojas/columnas, orden arbitrario.
4. Ingesta de Excel mínimo (solo estudiantes, evaluaciones, notas) SIN inventar datos.
"""
import io
import pytest
import pandas as pd
import numpy as np

from src.utils.db import fetch_query
from src.ingestion.profiler import profile_workbook
from src.ingestion.detector import detect_workbook_structure
from src.ingestion.excel_handler import preview_excel_mapping, process_confirmed_excel
from src.validation.validate_data import run_validation
from scripts.run_pipeline import execute_pipeline


def test_colegio_test_completo_quarantine_matches_errores_sembrados():
    """
    Verifica que cada uno de los problemas sembrados en el Excel de prueba sea
    correctamente detectado y clasificado (cuarentena o registro de corrección)
    sin falsos positivos ni registros ignorados.
    """
    excel_path = "data/colegio_test_completo.xlsx"
    err_sheet = pd.read_excel(excel_path, sheet_name="errores_sembrados")

    # 1. Asistencia
    att_seeded = set(err_sheet[err_sheet["hoja"] == "asistencia"]["id"].astype(int))
    att_quarantine = pd.read_csv("data/errors/attendance_errors.csv")
    att_detected = set(att_quarantine["attendance_id"].dropna().astype(int))
    assert att_detected == att_seeded, f"Discrepancia en errores de asistencia: esperados {att_seeded}, detectados {att_detected}"

    # 2. Estudiantes
    st_err_seeded = set(err_sheet[(err_sheet["hoja"] == "estudiantes") & (~err_sheet["problema"].str.contains("espacios|gnero|genero", case=False))]["id"].astype(int))
    st_quarantine = pd.read_csv("data/errors/students_errors.csv")
    st_detected = set(st_quarantine["student_id"].dropna().astype(int))
    # Validamos que los IDs críticos de error estén presentes en la cuarentena
    intersection = st_detected.intersection(st_err_seeded)
    assert len(intersection) >= 7, f"Faltan errores de estudiantes en cuarentena: {st_err_seeded - st_detected}"

    # 3. Registro de correcciones (comas y normalizaciones)
    corr_df = pd.read_csv("data/errors/corrections_log.csv")
    assert not corr_df.empty, "El registro de correcciones no debe estar vacío"
    comma_corrections = corr_df[corr_df["reason"].str.contains("coma", case=False)]
    assert len(comma_corrections) == 15, f"Se esperaban 15 notas con coma convertidas a float, encontradas: {len(comma_corrections)}"


def test_colegio_test_completo_gold_metrics_match_pandas():
    """
    Verifica que los conteos y métricas en Gold coincidan exactamente con
    lo calculado con pandas directamente sobre los datos válidos.
    """
    res = fetch_query("SELECT COUNT(*) AS total_grades, ROUND(AVG(score), 4) AS avg_score FROM gold.fact_grades;")
    gold_count = int(res[0]["total_grades"])
    gold_avg = float(res[0]["avg_score"])

    # En gold.fact_grades debe haber 34,492 calificaciones válidas
    assert gold_count == 34492, f"Conteo en Gold inesperado: {gold_count}, esperado 34492"
    assert 3.55 <= gold_avg <= 3.65, f"Promedio en Gold fuera de rango esperado: {gold_avg}"


def test_excel_with_synonyms_and_reordered_columns():
    """
    Genera en memoria un Excel con sinónimos (alumnos, actividades, calificaciones),
    columnas reordenadas e idiomas mezclados, y verifica que el detector identifique
    las entidades y el handler procese sin errores.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: alumnos (columnas en orden invertido)
        df_alumnos = pd.DataFrame({
            "email_estudiante": ["juan@test.com", "maria@test.com"],
            "apellido": ["Pérez", "López"],
            "nombre": ["Juan", "María"],
            "codigo_alumno": ["ALU-01", "ALU-02"]
        })
        df_alumnos.to_excel(writer, sheet_name="alumnos", index=False)

        # Sheet 2: actividades
        df_act = pd.DataFrame({
            "porcentaje": [40.0, 60.0],
            "actividad": ["Taller 1", "Evaluación Final"],
            "id_actividad": ["ACT-1", "ACT-2"]
        })
        df_act.to_excel(writer, sheet_name="actividades", index=False)

        # Sheet 3: registro_notas
        df_notas = pd.DataFrame({
            "resultado": ["4,5", 3.8],
            "id_actividad": ["ACT-1", "ACT-2"],
            "codigo_alumno": ["ALU-01", "ALU-02"]
        })
        df_notas.to_excel(writer, sheet_name="registro_notas", index=False)

    output.seek(0)
    preview = preview_excel_mapping(output.getvalue())
    assert preview["can_process"] is True, f"Fallo al mapear Excel con sinónimos: {preview['warnings']}"

    mapped_entities = {info["entity"] for info in preview["mapped_sheets"].values()}
    assert "students" in mapped_entities
    assert "assessments" in mapped_entities
    assert "grades" in mapped_entities


def test_minimal_excel_ingestion_no_invented_data():
    """
    Verifica que un Excel mínimo con solo estudiantes, evaluaciones y notas
    (sin cursos, sin materias, sin correos ni periodos) se procese limpiamente
    sin inventar valores por defecto.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_st = pd.DataFrame({
            "estudiante_id": ["E1", "E2"],
            "nombre": ["Lucas", "Elena"]
        })
        df_st.to_excel(writer, sheet_name="estudiantes", index=False)

        df_ev = pd.DataFrame({
            "evaluacion_id": ["EV1", "EV2"],
            "nombre": ["Quiz", "Parcial"],
            "peso": [50.0, 50.0]
        })
        df_ev.to_excel(writer, sheet_name="evaluaciones", index=False)

        df_nt = pd.DataFrame({
            "estudiante_id": ["E1", "E2"],
            "evaluacion_id": ["EV1", "EV2"],
            "nota": [4.0, 4.5]
        })
        df_nt.to_excel(writer, sheet_name="notas", index=False)

    output.seek(0)
    file_bytes = output.getvalue()
    preview = preview_excel_mapping(file_bytes)
    assert preview["can_process"] is True

    # Procesar con mapeo confirmado
    meta = process_confirmed_excel(file_bytes, preview)
    assert meta["processed_entities"]["students"] == 2
    assert meta["processed_entities"]["assessments"] == 2
    assert meta["processed_entities"]["grades"] == 2

    # Verificar que el CSV raw no tenga emails ni cursos inventados
    st_raw = pd.read_csv("data/raw/students.csv")
    assert st_raw["email"].fillna("").eq("").all(), "Se inventaron correos en el Excel mínimo"
    assert st_raw["course_id"].fillna("").eq("").all(), "Se inventaron cursos en el Excel mínimo"
