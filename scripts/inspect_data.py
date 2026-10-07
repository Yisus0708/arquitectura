"""
Data Inspection & Profiling Script (Step 1).
Inspects all generated raw files, verifies schemas, columns, null counts,
duplicate keys, value ranges, and outputs docs/data_dictionary.md.
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config import RAW_DATA_DIR, DOCS_DIR
from src.utils.logger import get_logger

logger = get_logger("inspect_data")

EXPECTED_FILES = [
    "courses.csv",
    "subjects.csv",
    "students.csv",
    "assessments.csv",
    "grades.csv"
]


def inspect_dataset() -> Dict[str, Any]:
    """Inspects all CSV files in RAW_DATA_DIR."""
    inspection_report = {}

    for filename in EXPECTED_FILES:
        filepath = RAW_DATA_DIR / filename
        if not filepath.exists():
            logger.error(f"Missing file: {filename}")
            continue

        df = pd.read_csv(filepath)
        col_details = []

        for col in df.columns:
            null_count = int(df[col].isnull().sum())
            null_pct = round((null_count / len(df)) * 100, 2)
            unique_count = int(df[col].nunique(dropna=False))
            sample_val = str(df[col].dropna().iloc[0]) if not df[col].dropna().empty else "N/A"
            dtype = str(df[col].dtype)

            min_val = None
            max_val = None
            if pd.api.types.is_numeric_dtype(df[col]):
                min_val = float(df[col].min())
                max_val = float(df[col].max())

            col_details.append({
                "column": col,
                "dtype": dtype,
                "null_count": null_count,
                "null_pct": null_pct,
                "unique_count": unique_count,
                "sample_val": sample_val,
                "min": min_val,
                "max": max_val,
            })

        # Duplicate primary keys analysis
        pk_col = df.columns[0]
        duplicates_pk = int(df[pk_col].duplicated().sum())

        inspection_report[filename] = {
            "total_rows": len(df),
            "columns_count": len(df.columns),
            "pk_candidate": pk_col,
            "duplicate_pks": duplicates_pk,
            "columns": col_details,
        }

    return inspection_report


def generate_data_dictionary_md(report: Dict[str, Any]) -> None:
    """Writes docs/data_dictionary.md with inspected details."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    dict_file = DOCS_DIR / "data_dictionary.md"

    md_lines = [
        "# Diccionario de Datos del Sistema de Calificaciones Escolar",
        "",
        "> **Propósito**: Documentar con exactitud las entidades, columnas, tipos de datos, restricciones y métricas detectadas en la capa `raw` generada.",
        "",
        "---",
        ""
    ]

    for filename, info in report.items():
        entity_name = filename.replace(".csv", "").capitalize()
        md_lines.append(f"## 1. Entidad: `{entity_name}` (`{filename}`)")
        md_lines.append(f"- **Total de registros**: {info['total_rows']}")
        md_lines.append(f"- **Clave Primaria Candidata**: `{info['pk_candidate']}`")
        md_lines.append(f"- **Duplicados en PK detectados (anomalías raw)**: {info['duplicate_pks']}")
        md_lines.append("")
        md_lines.append("| Columna | Tipo Inferido | Nulos (%) | Únicos | Rango (Min - Max) | Ejemplo | Descripción de Negocio |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

        for col in info["columns"]:
            range_str = f"{col['min']} a {col['max']}" if col["min"] is not None else "N/A"
            desc = describe_business_field(filename, col["column"])
            md_lines.append(
                f"| `{col['column']}` | {col['dtype']} | {col['null_count']} ({col['null_pct']}%) | {col['unique_count']} | {range_str} | `{col['sample_val']}` | {desc} |"
            )

        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    with open(dict_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    logger.info(f"Data dictionary successfully generated at: {dict_file}")


def describe_business_field(filename: str, col_name: str) -> str:
    """Returns business description for each recognized column."""
    descriptions = {
        ("courses.csv", "course_id"): "Identificador único del curso/grado (ej. CUR-10A).",
        ("courses.csv", "course_name"): "Nombre descriptivo del grupo y salón (ej. Grado 10-A).",
        ("courses.csv", "grade_level"): "Nivel o grado escolar (10 o 11).",
        ("courses.csv", "academic_year"): "Año lectivo académico (2026).",

        ("subjects.csv", "subject_id"): "Identificador único de la asignatura para el curso.",
        ("subjects.csv", "subject_name"): "Nombre de la materia (Matemáticas, Física, etc.).",
        ("subjects.csv", "course_id"): "FK referenciando al curso que dicta la asignatura.",
        ("subjects.csv", "department"): "Área o departamento académico pedagógico.",

        ("students.csv", "student_id"): "Identificador único del estudiante matriculado.",
        ("students.csv", "first_name"): "Primer nombre del alumno.",
        ("students.csv", "last_name"): "Apellidos del alumno.",
        ("students.csv", "email"): "Correo electrónico institucional del estudiante.",
        ("students.csv", "course_id"): "FK referenciando al curso asignado.",
        ("students.csv", "enrollment_date"): "Fecha de ingreso y formalización de matrícula.",
        ("students.csv", "status"): "Estado académico del estudiante (ACTIVO).",

        ("assessments.csv", "assessment_id"): "Identificador único del instrumento de evaluación.",
        ("assessments.csv", "subject_id"): "FK referenciando a la materia evaluada.",
        ("assessments.csv", "assessment_name"): "Nombre de la prueba (Parcial 1, Quiz, etc.).",
        ("assessments.csv", "assessment_type"): "Categoría (Taller, Parcial, Quiz, Examen Final, Proyecto).",
        ("assessments.csv", "weight_percentage"): "Porcentaje de ponderación en la nota final (0-100%). La suma por materia debe ser 100%.",
        ("assessments.csv", "assessment_date"): "Fecha programada de aplicación del examen.",

        ("grades.csv", "grade_id"): "Identificador único del registro de calificación individual.",
        ("grades.csv", "assessment_id"): "FK referenciando la evaluación aplicada.",
        ("grades.csv", "student_id"): "FK referenciando al estudiante evaluado.",
        ("grades.csv", "score"): "Calificación obtenida en escala 0.0 a 5.0 (aprobación >= 3.0).",
        ("grades.csv", "submission_date"): "Fecha de entrega o subida de la nota.",
        ("grades.csv", "feedback"): "Retroalimentación cualitativa pedagógica del docente.",
    }
    return descriptions.get((filename, col_name), "Campo descriptivo de la entidad.")


def main():
    logger.info("Executing Step 1: Dataset Inspection & Profiling...")
    report = inspect_dataset()

    for fname, data in report.items():
        logger.info(
            f"File: {fname:16} | Rows: {data['total_rows']:5} | Columns: {data['columns_count']:2} | Duplicate PKs: {data['duplicate_pks']}"
        )

    generate_data_dictionary_md(report)
    logger.info("Data inspection complete. Dictionary documented.")


if __name__ == "__main__":
    main()
