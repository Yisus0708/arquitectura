"""
Excel Handler Module.
Provides functionality to:
1. Generate an official, structured Excel template (.xlsx) for courses, subjects, students, assessments, and grades.
2. Ingest uploaded Excel workbooks, validate sheet schemas, export to data/raw/, and trigger the end-to-end pipeline.
"""
import io
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from src.utils.config import RAW_DATA_DIR, BASE_DIR
from src.utils.hashing import calculate_file_sha256
from src.utils.logger import get_logger

logger = get_logger("excel_handler")

SHEET_MAPPINGS = {
    "cursos": "courses.csv",
    "materias": "subjects.csv",
    "estudiantes": "students.csv",
    "evaluaciones": "assessments.csv",
    "calificaciones": "grades.csv",
    # English aliases in case user uploads with English names
    "courses": "courses.csv",
    "subjects": "subjects.csv",
    "students": "students.csv",
    "assessments": "assessments.csv",
    "grades": "grades.csv",
}

EXPECTED_COLUMNS = {
    "courses.csv": ["course_id", "course_name", "grade_level", "academic_year"],
    "subjects.csv": ["subject_id", "subject_name", "course_id", "department"],
    "students.csv": ["student_id", "first_name", "last_name", "email", "course_id", "enrollment_date", "status"],
    "assessments.csv": ["assessment_id", "subject_id", "assessment_name", "assessment_type", "weight_percentage", "assessment_date"],
    "grades.csv": ["grade_id", "assessment_id", "student_id", "score", "submission_date", "feedback"]
}


def create_excel_template() -> bytes:
    """
    Generates a beautifully styled Excel workbook template (.xlsx) in memory
    containing the 5 required sheets with headers, instructions, and sample rows.
    """
    output = io.BytesIO()
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    sample_data = {
        "cursos": [
            ["course_id", "course_name", "grade_level", "academic_year"],
            ["CUR-10A", "Grado 10-A", 10, 2026],
            ["CUR-10B", "Grado 10-B", 10, 2026],
            ["CUR-11A", "Grado 11-A", 11, 2026],
            ["CUR-11B", "Grado 11-B", 11, 2026],
        ],
        "materias": [
            ["subject_id", "subject_name", "course_id", "department"],
            ["SUB-MAT-10A", "Matemáticas 10°", "CUR-10A", "Ciencias Exactas"],
            ["SUB-FIS-10A", "Física 10°", "CUR-10A", "Ciencias Naturales"],
            ["SUB-ESP-10A", "Español y Literatura 10°", "CUR-10A", "Humanidades"],
            ["SUB-ING-10A", "Inglés 10°", "CUR-10A", "Idiomas"],
        ],
        "estudiantes": [
            ["student_id", "first_name", "last_name", "email", "course_id", "enrollment_date", "status"],
            ["EST-001", "Mateo", "Gómez", "mateo.gomez@colegio.edu.co", "CUR-10A", "2026-01-15", "ACTIVO"],
            ["EST-002", "Sofía", "Rodríguez", "sofia.rodriguez@colegio.edu.co", "CUR-10A", "2026-01-15", "ACTIVO"],
            ["EST-003", "Alejandro", "Vargas", "alejandro.vargas@colegio.edu.co", "CUR-10A", "2026-01-15", "ACTIVO"],
        ],
        "evaluaciones": [
            ["assessment_id", "subject_id", "assessment_name", "assessment_type", "weight_percentage", "assessment_date"],
            ["EVAL-SUB-MAT-10A-01", "SUB-MAT-10A", "Taller Práctico 1", "Taller", 15.0, "2026-02-20"],
            ["EVAL-SUB-MAT-10A-02", "SUB-MAT-10A", "Parcial Teórico 1", "Parcial", 30.0, "2026-03-25"],
            ["EVAL-SUB-MAT-10A-03", "SUB-MAT-10A", "Quiz Diagnóstico", "Quiz", 15.0, "2026-04-18"],
            ["EVAL-SUB-MAT-10A-04", "SUB-MAT-10A", "Examen Final Semestral", "Examen Final", 40.0, "2026-05-28"],
        ],
        "calificaciones": [
            ["grade_id", "assessment_id", "student_id", "score", "submission_date", "feedback"],
            ["GRD-00001", "EVAL-SUB-MAT-10A-01", "EST-001", 4.5, "2026-02-21", "Excelente dominio de los conceptos."],
            ["GRD-00002", "EVAL-SUB-MAT-10A-02", "EST-001", 4.0, "2026-03-26", "Buen trabajo, repasar ejercicios."],
            ["GRD-00003", "EVAL-SUB-MAT-10A-03", "EST-001", 4.2, "2026-04-19", "Aprobado con solvencia."],
            ["GRD-00004", "EVAL-SUB-MAT-10A-04", "EST-001", 4.6, "2026-05-29", "Desempeño superior."],
        ]
    }

    for sheet_name, rows in sample_data.items():
        ws = wb.create_sheet(title=sheet_name)
        for r_idx, row in enumerate(rows, start=1):
            for c_idx, val in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.border = thin_border
                if r_idx == 1:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = align_center
                else:
                    cell.alignment = align_left

        # Adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(output)
    output.seek(0)
    return output.getvalue()


def process_uploaded_excel_file(file_content: bytes) -> Dict[str, Any]:
    """
    Parses an uploaded Excel file, validates that required sheets exist,
    writes them as raw CSVs, recalculates metadata, and executes the data pipeline.
    """
    logger.info("Processing uploaded Excel file...")
    excel_io = io.BytesIO(file_content)
    xls = pd.ExcelFile(excel_io)
    sheet_names_lower = {s.lower().strip(): s for s in xls.sheet_names}

    found_mappings = {}
    for target_key, csv_name in SHEET_MAPPINGS.items():
        if target_key in sheet_names_lower:
            actual_sheet = sheet_names_lower[target_key]
            found_mappings[csv_name] = actual_sheet

    if not found_mappings:
        raise ValueError(
            f"El archivo Excel no contiene ninguna de las hojas requeridas: {list(SHEET_MAPPINGS.keys())}. "
            f"Hojas encontradas: {xls.sheet_names}"
        )

    # Save sheets to data/raw/
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    exported_counts = {}

    for csv_filename, sheet_name in found_mappings.items():
        df = pd.read_excel(excel_io, sheet_name=sheet_name)
        # Normalize column names to snake_case
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        target_file = RAW_DATA_DIR / csv_filename
        df.to_csv(target_file, index=False, encoding="utf-8")
        exported_counts[csv_filename] = len(df)
        logger.info(f"Excel Sheet '{sheet_name}' -> {csv_filename} ({len(df)} rows)")

    # Execute pipeline stages: validation -> raw -> staging -> silver -> gold
    from src.validation.validate_data import run_validation
    from src.loading.load_raw import load_all_raw
    from src.transformation.transform_staging import run_staging_transformations
    from src.transformation.transform_silver import run_silver_transformations
    from src.transformation.transform_gold import run_gold_transformations

    val_summary = run_validation()
    load_all_raw()
    run_staging_transformations()
    run_silver_transformations()
    gold_counts = run_gold_transformations()

    return {
        "status": "success",
        "sheets_imported": list(found_mappings.keys()),
        "rows_imported": exported_counts,
        "validation_summary": val_summary,
        "gold_counts": gold_counts,
    }
