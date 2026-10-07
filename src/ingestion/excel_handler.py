"""
Excel Handler Module.
Provides functionality to:
1. Generate an official, structured Excel template (.xlsx) for courses, subjects, students, assessments, and grades.
2. Ingest uploaded Excel workbooks with ultra-flexible sheet and column mapping (Spanish & English aliases).
3. Standardize raw data, export to data/raw/, generate audit metadata, and trigger the end-to-end pipeline.
"""
import io
import json
import re
import unicodedata
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from src.utils.config import RAW_DATA_DIR, BASE_DIR
from src.utils.hashing import calculate_file_sha256
from src.utils.logger import get_logger

logger = get_logger("excel_handler")

# Standard CSV file names and schemas expected by the pipeline
EXPECTED_COLUMNS = {
    "courses.csv": ["course_id", "course_name", "grade_level", "academic_year"],
    "subjects.csv": ["subject_id", "subject_name", "course_id", "department"],
    "students.csv": ["student_id", "first_name", "last_name", "email", "course_id", "enrollment_date", "status"],
    "assessments.csv": ["assessment_id", "subject_id", "assessment_name", "assessment_type", "weight_percentage", "assessment_date"],
    "grades.csv": ["grade_id", "assessment_id", "student_id", "score", "submission_date", "feedback"]
}

# Aliases for detecting sheet names
SHEET_ALIASES = {
    "courses": ["cursos", "courses", "curso", "course", "grados", "grupos", "aulas"],
    "subjects": ["materias", "subjects", "materia", "subject", "asignaturas", "asignatura", "areas", "area"],
    "students": ["estudiantes", "students", "estudiante", "student", "alumnos", "alumno", "matriculas", "matricula"],
    "assessments": ["evaluaciones", "assessments", "evaluacion", "assessment", "actividades", "actividad", "examenes", "examen", "parciales", "parcial"],
    "grades": ["calificaciones", "grades", "calificacion", "grade", "notas", "nota", "puntajes", "puntaje"],
}

# Column aliases for each entity
COLUMN_ALIASES = {
    "courses": {
        "course_id": ["course_id", "curso_id", "id_curso", "id", "codigo_curso", "codigo", "cod_curso"],
        "course_name": ["course_name", "nombre_curso", "curso_nombre", "nombre", "curso", "descripcion"],
        "grade_level": ["grade_level", "grado", "nivel", "nivel_grado"],
        "academic_year": ["academic_year", "anio_academico", "ano_academico", "anio", "ano", "year", "periodo", "vigencia"],
    },
    "subjects": {
        "subject_id": ["subject_id", "materia_id", "id_materia", "id_asignatura", "id", "codigo_materia", "codigo", "cod_materia"],
        "subject_name": ["subject_name", "nombre_materia", "materia", "asignatura", "nombre", "nombre_asignatura"],
        "course_id": ["course_id", "curso_id", "id_curso", "curso"],
        "department": ["department", "departamento", "docente", "profesor", "area", "area_academica"],
    },
    "students": {
        "student_id": ["student_id", "estudiante_id", "id_estudiante", "id_alumno", "id", "documento", "matricula", "cod_estudiante"],
        "first_name": ["first_name", "nombres", "nombre", "primer_nombre"],
        "last_name": ["last_name", "apellidos", "apellido", "primer_apellido"],
        "email": ["email", "correo", "correo_electronico", "mail"],
        "course_id": ["course_id", "curso_id", "id_curso", "curso", "grado_id"],
        "enrollment_date": ["enrollment_date", "fecha_ingreso", "fecha_matricula", "fecha_nacimiento", "fecha"],
        "status": ["status", "estado", "condicion"],
    },
    "assessments": {
        "assessment_id": ["assessment_id", "evaluacion_id", "id_evaluacion", "id", "codigo_evaluacion", "codigo"],
        "subject_id": ["subject_id", "materia_id", "id_materia", "id_asignatura"],
        "assessment_name": ["assessment_name", "nombre_evaluacion", "evaluacion", "nombre", "titulo", "tipo"],
        "assessment_type": ["assessment_type", "tipo", "tipo_evaluacion", "categoria"],
        "weight_percentage": ["weight_percentage", "porcentaje", "peso", "peso_porcentaje", "ponderacion", "valor"],
        "assessment_date": ["assessment_date", "fecha_evaluacion", "fecha", "fecha_limite"],
    },
    "grades": {
        "grade_id": ["grade_id", "nota_id", "id_nota", "id_calificacion", "id"],
        "assessment_id": ["assessment_id", "evaluacion_id", "id_evaluacion"],
        "student_id": ["student_id", "estudiante_id", "id_estudiante", "id_alumno"],
        "score": ["score", "nota", "calificacion", "puntaje", "valor"],
        "submission_date": ["submission_date", "fecha_registro", "fecha_entrega", "fecha"],
        "feedback": ["feedback", "observaciones", "comentarios", "retroalimentacion"],
    }
}


def clean_text_key(s: Any) -> str:
    """Normalizes string for comparison: lowercase, remove accents, strip spaces/underscores."""
    if not isinstance(s, str):
        s = str(s)
    # Remove accents
    s_norm = unicodedata.normalize('NFD', s)
    s_clean = ''.join(c for c in s_norm if unicodedata.category(c) != 'Mn')
    s_clean = s_clean.lower().strip()
    s_clean = re.sub(r'[\s\-_]+', '', s_clean)
    return s_clean


def find_matching_sheet(sheet_names: List[str], entity: str) -> Optional[str]:
    """Finds best matching sheet name for a given entity among workbook sheets."""
    clean_sheets = {clean_text_key(s): s for s in sheet_names}
    for alias in SHEET_ALIASES.get(entity, []):
        clean_alias = clean_text_key(alias)
        if clean_alias in clean_sheets:
            return clean_sheets[clean_alias]
    # Fallback: substring matching
    for alias in SHEET_ALIASES.get(entity, []):
        clean_alias = clean_text_key(alias)
        for cs, orig in clean_sheets.items():
            if clean_alias in cs or cs in clean_alias:
                return orig
    return None


def format_date_cell(val: Any) -> Any:
    """Formats date or datetime to YYYY-MM-DD string while preserving unparseable text."""
    if pd.isnull(val):
        return ""
    if isinstance(val, (datetime, date, pd.Timestamp)):
        return val.strftime("%Y-%m-%d")
    val_str = str(val).strip()
    # Check if string matches standard date formats including timestamps
    for fmt in (
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y",
        "%Y/%m/%d %H:%M:%S", "%Y/%m/%d",
        "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"
    ):
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    # Preserve raw string (e.g. invalid dates like '31/02/2026' so validation can catch them)
    return val_str


def create_excel_template() -> bytes:
    """
    Generates a beautifully styled Excel workbook template (.xlsx) in memory
    containing the 5 required sheets with headers, instructions, and sample rows.
    """
    output = io.BytesIO()
    wb = openpyxl.Workbook()
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

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(output)
    output.seek(0)
    return output.getvalue()


def process_uploaded_excel_file(file_content: bytes) -> Dict[str, Any]:
    """
    Parses an uploaded Excel file, intelligently maps sheets and columns,
    normalizes data into standard raw CSVs, calculates cryptographic metadata,
    and executes the end-to-end data pipeline.
    """
    logger.info("Processing uploaded Excel file with flexible schema mapper...")
    excel_io = io.BytesIO(file_content)
    xls = pd.ExcelFile(excel_io)
    available_sheets = xls.sheet_names

    # 1. Match sheets
    matched_sheets: Dict[str, str] = {}
    for entity in ["courses", "subjects", "students", "assessments", "grades"]:
        sheet_name = find_matching_sheet(available_sheets, entity)
        if sheet_name:
            matched_sheets[entity] = sheet_name

    # Check for minimum required sheets (at least students, subjects, assessments, grades)
    missing_entities = [e for e in ["subjects", "students", "assessments", "grades"] if e not in matched_sheets]
    if missing_entities:
        raise ValueError(
            f"El archivo Excel debe contener al menos las hojas de materias, estudiantes, evaluaciones y calificaciones. "
            f"Faltan: {missing_entities}. Hojas en el archivo: {available_sheets}"
        )

    # 2. Read raw dataframes
    dfs: Dict[str, pd.DataFrame] = {}
    for entity, sheet_name in matched_sheets.items():
        raw_df = pd.read_excel(excel_io, sheet_name=sheet_name, dtype=str)
        dfs[entity] = raw_df

    # 3. Standardize and Map Courses
    if "courses" in dfs:
        courses_raw = dfs["courses"]
        col_map = {}
        for target_col, aliases in COLUMN_ALIASES["courses"].items():
            for c in courses_raw.columns:
                if clean_text_key(c) in [clean_text_key(a) for a in aliases]:
                    col_map[target_col] = c
                    break

        courses_df = pd.DataFrame()
        courses_df["course_id"] = courses_raw[col_map["course_id"]] if "course_id" in col_map else [f"CUR-{i+1}" for i in range(len(courses_raw))]
        courses_df["course_name"] = courses_raw[col_map["course_name"]] if "course_name" in col_map else courses_df["course_id"]

        if "grade_level" in col_map:
            courses_df["grade_level"] = courses_raw[col_map["grade_level"]]
        else:
            # Extract digit from course name or default to 10
            courses_df["grade_level"] = courses_df["course_name"].astype(str).str.extract(r'(\d+)')[0].fillna("10")

        if "academic_year" in col_map:
            courses_df["academic_year"] = courses_raw[col_map["academic_year"]]
        else:
            courses_df["academic_year"] = "2026"
    else:
        # Synthesize default courses if courses sheet was omitted
        courses_df = pd.DataFrame([
            {"course_id": "CUR-01", "course_name": "Curso General", "grade_level": "10", "academic_year": "2026"}
        ])

    default_course_id = courses_df["course_id"].iloc[0] if len(courses_df) > 0 else "CUR-01"

    # 4. Standardize and Map Subjects
    subjects_raw = dfs["subjects"]
    col_map = {}
    for target_col, aliases in COLUMN_ALIASES["subjects"].items():
        for c in subjects_raw.columns:
            if clean_text_key(c) in [clean_text_key(a) for a in aliases]:
                col_map[target_col] = c
                break

    subjects_df = pd.DataFrame()
    subjects_df["subject_id"] = subjects_raw[col_map["subject_id"]] if "subject_id" in col_map else [f"SUB-{i+1}" for i in range(len(subjects_raw))]
    subjects_df["subject_name"] = subjects_raw[col_map["subject_name"]] if "subject_name" in col_map else subjects_df["subject_id"]

    if "course_id" in col_map:
        subjects_df["course_id"] = subjects_raw[col_map["course_id"]]
    else:
        # If subjects are defined at school level without course_id, assign default course
        subjects_df["course_id"] = default_course_id

    if "department" in col_map:
        subjects_df["department"] = subjects_raw[col_map["department"]]
    else:
        subjects_df["department"] = "Académico"

    # 5. Standardize and Map Students
    students_raw = dfs["students"]
    col_map = {}
    for target_col, aliases in COLUMN_ALIASES["students"].items():
        for c in students_raw.columns:
            if clean_text_key(c) in [clean_text_key(a) for a in aliases]:
                col_map[target_col] = c
                break

    students_df = pd.DataFrame()
    students_df["student_id"] = students_raw[col_map["student_id"]] if "student_id" in col_map else [f"EST-{i+1}" for i in range(len(students_raw))]

    if "first_name" in col_map:
        students_df["first_name"] = students_raw[col_map["first_name"]]
    else:
        students_df["first_name"] = "Estudiante"

    if "last_name" in col_map:
        students_df["last_name"] = students_raw[col_map["last_name"]]
    else:
        students_df["last_name"] = students_df["student_id"]

    if "email" in col_map:
        students_df["email"] = students_raw[col_map["email"]]
    else:
        students_df["email"] = [f"est_{sid}@colegio.edu.co" for sid in students_df["student_id"]]

    if "course_id" in col_map:
        students_df["course_id"] = students_raw[col_map["course_id"]]
    else:
        students_df["course_id"] = default_course_id

    if "enrollment_date" in col_map:
        students_df["enrollment_date"] = students_raw[col_map["enrollment_date"]].apply(format_date_cell)
    else:
        students_df["enrollment_date"] = "2026-01-15"

    if "status" in col_map:
        students_df["status"] = students_raw[col_map["status"]]
    else:
        students_df["status"] = "ACTIVO"

    # 6. Standardize and Map Assessments
    assessments_raw = dfs["assessments"]
    col_map = {}
    for target_col, aliases in COLUMN_ALIASES["assessments"].items():
        for c in assessments_raw.columns:
            if clean_text_key(c) in [clean_text_key(a) for a in aliases]:
                col_map[target_col] = c
                break

    assessments_df = pd.DataFrame()
    assessments_df["assessment_id"] = assessments_raw[col_map["assessment_id"]] if "assessment_id" in col_map else [f"EVAL-{i+1}" for i in range(len(assessments_raw))]
    assessments_df["subject_id"] = assessments_raw[col_map["subject_id"]] if "subject_id" in col_map else "1"

    if "assessment_name" in col_map:
        assessments_df["assessment_name"] = assessments_raw[col_map["assessment_name"]]
    elif "assessment_type" in col_map:
        assessments_df["assessment_name"] = assessments_raw[col_map["assessment_type"]]
    else:
        assessments_df["assessment_name"] = "Evaluación"

    if "assessment_type" in col_map:
        assessments_df["assessment_type"] = assessments_raw[col_map["assessment_type"]]
    else:
        assessments_df["assessment_type"] = assessments_df["assessment_name"]

    if "weight_percentage" in col_map:
        assessments_df["weight_percentage"] = assessments_raw[col_map["weight_percentage"]]
    else:
        assessments_df["weight_percentage"] = "25.0"

    if "assessment_date" in col_map:
        assessments_df["assessment_date"] = assessments_raw[col_map["assessment_date"]].apply(format_date_cell)
    else:
        assessments_df["assessment_date"] = "2026-03-01"

    # 7. Standardize and Map Grades
    grades_raw = dfs["grades"]
    col_map = {}
    for target_col, aliases in COLUMN_ALIASES["grades"].items():
        for c in grades_raw.columns:
            if clean_text_key(c) in [clean_text_key(a) for a in aliases]:
                col_map[target_col] = c
                break

    grades_df = pd.DataFrame()
    grades_df["grade_id"] = grades_raw[col_map["grade_id"]] if "grade_id" in col_map else [f"GRD-{i+1}" for i in range(len(grades_raw))]
    grades_df["assessment_id"] = grades_raw[col_map["assessment_id"]] if "assessment_id" in col_map else "1"
    grades_df["student_id"] = grades_raw[col_map["student_id"]] if "student_id" in col_map else "1"
    grades_df["score"] = grades_raw[col_map["score"]] if "score" in col_map else None

    if "submission_date" in col_map:
        grades_df["submission_date"] = grades_raw[col_map["submission_date"]].apply(format_date_cell)
    else:
        grades_df["submission_date"] = "2026-03-01"

    if "feedback" in col_map:
        grades_df["feedback"] = grades_raw[col_map["feedback"]]
    else:
        grades_df["feedback"] = ""

    # 8. Save clean raw datasets to data/raw/
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    datasets = {
        "courses.csv": courses_df,
        "subjects.csv": subjects_df,
        "students.csv": students_df,
        "assessments.csv": assessments_df,
        "grades.csv": grades_df,
    }

    metadata: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "random_seed": "N/A (Uploaded Excel)",
        "source": "Uploaded Excel Workbook",
        "scale": "0.0 - 5.0 (passing >= 3.0)",
        "files": {}
    }
    exported_counts = {}

    for filename, df in datasets.items():
        file_path = RAW_DATA_DIR / filename
        df.to_csv(file_path, index=False, encoding="utf-8")
        row_count = len(df)
        file_size = file_path.stat().st_size
        checksum = calculate_file_sha256(file_path)

        metadata["files"][filename] = {
            "path": str(file_path.relative_to(BASE_DIR)),
            "row_count": row_count,
            "columns": list(df.columns),
            "size_bytes": file_size,
            "sha256": checksum
        }
        exported_counts[filename] = row_count
        logger.info(f"Exported raw {filename}: {row_count} rows, sha256={checksum[:12]}...")

    # Write ingestion metadata audit log
    metadata_path = RAW_DATA_DIR / "ingestion_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    # 9. Execute Medallion Pipeline Stages
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
        "sheets_imported": list(matched_sheets.values()),
        "rows_imported": exported_counts,
        "validation_summary": val_summary,
        "gold_counts": gold_counts,
    }
