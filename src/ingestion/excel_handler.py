"""
Excel Handler Module.
Procesa cualquier archivo Excel académico:
1. Perfila hojas y columnas dinámicamente sin esquemas fijos.
2. Detecta mapeos semánticos (nombre + contenido), escala de notas y regla de pesos.
3. Genera previsualización interactiva para validación o ajuste del usuario.
4. Escribe a data/raw/ preservando columnas extra en JSON y SIN inventar datos por defecto.
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
from src.ingestion.profiler import profile_workbook, profile_dataframe
from src.ingestion.detector import detect_workbook_structure, normalize_text

logger = get_logger("excel_handler")

TEMPLATES_DIR = BASE_DIR / "data" / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Mandatory fields per entity (missing mandatory = explicit error)
MANDATORY_FIELDS = {
    "students": ["student_id", "first_name"],
    "courses": ["course_id", "course_name"],
    "subjects": ["subject_id", "subject_name"],
    "assessments": ["assessment_id", "name", "weight"],
    "grades": ["student_id", "assessment_id", "score"],
    "periods": ["period_id", "period_name"],
    "teachers": ["teacher_id"],
    "course_subjects": ["course_id", "subject_id"],
    "attendance": ["student_id"],
    "performance_scale": ["level", "min_score", "max_score"],
}

# Standard column names for export to raw CSVs
CANONICAL_COLUMNS = {
    "courses": ["course_id", "course_name", "grade_level", "academic_year", "extra"],
    "subjects": ["subject_id", "subject_name", "course_id", "department", "extra"],
    "students": ["student_id", "document_number", "first_name", "last_name", "gender", "birth_date", "email", "course_id", "enrollment_date", "status", "extra"],
    "assessments": ["assessment_id", "course_id", "subject_id", "period_id", "assessment_name", "assessment_type", "weight_percentage", "assessment_date", "extra"],
    "grades": ["grade_id", "assessment_id", "student_id", "score", "submission_date", "feedback", "extra"],
    "periods": ["period_id", "period_name", "start_date", "end_date", "weight", "extra"],
    "teachers": ["teacher_id", "document_number", "first_name", "last_name", "email", "specialty", "extra"],
    "course_subjects": ["course_id", "subject_id", "teacher_id", "hours_per_week", "extra"],
    "attendance": ["attendance_id", "student_id", "course_id", "period_id", "total_classes", "absences", "extra"],
    "performance_scale": ["level", "min_score", "max_score", "description", "extra"],
}


def format_date_cell(val: Any) -> Any:
    """Formatea fecha a YYYY-MM-DD preservando cadenas no parseables para auditoría."""
    if pd.isnull(val) or val is None or str(val).strip() in ("", "nan", "None"):
        return ""
    if isinstance(val, (datetime, date, pd.Timestamp)):
        return val.strftime("%Y-%m-%d")
    val_str = str(val).strip()
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
    return val_str


def preview_excel_mapping(file_bytes_or_path: Any) -> Dict[str, Any]:
    """
    Analiza y genera una propuesta transparente de mapeo para previsualización.
    """
    logger.info("Generando propuesta de mapeo para el archivo Excel...")
    if isinstance(file_bytes_or_path, (bytes, bytearray)):
        bio = io.BytesIO(file_bytes_or_path)
        prof = profile_workbook(bio)
        bio.seek(0)
        structure = detect_workbook_structure(prof, bio)
    else:
        prof = profile_workbook(file_bytes_or_path)
        structure = detect_workbook_structure(prof, str(file_bytes_or_path))

    # Verificar requerimientos mínimos
    mapped_entities = {info["entity"] for info in structure["mapped_sheets"].values()}
    required_entities = {"students", "assessments", "grades"}
    missing_required = required_entities - mapped_entities

    warnings = []
    if missing_required:
        warnings.append(f"Faltan hojas obligatorias para el pipeline: {list(missing_required)}")
    if "courses" not in mapped_entities:
        warnings.append("No se detectó hoja de cursos; las evaluaciones y estudiantes no tendrán referencia de grupo.")
    if "subjects" not in mapped_entities:
        warnings.append("No se detectó catálogo de materias.")

    # Flatten sheets list for UI and API convenience
    sheets_summary = []
    for s_name, info in structure["mapped_sheets"].items():
        sheets_summary.append({
            "sheet_name": s_name,
            "entity_mapped": info["entity"],
            "confidence": info.get("confidence", 1.0),
            "rows_count": info.get("row_count", 0),
            "column_mappings": info.get("column_mapping", {}),
            "ignored_columns": info.get("ignored_columns", []),
        })
    for ign in structure["ignored_sheets"]:
        sheets_summary.append({
            "sheet_name": ign["sheet_name"],
            "entity_mapped": None,
            "confidence": 0.0,
            "rows_count": ign.get("row_count", 0),
            "column_mappings": {},
            "ignored_columns": [],
        })

    scale_info = structure["detected_grading_scale"]
    scale_label = scale_info.get("scale_type", "0-5")
    pass_grade = scale_info.get("passing_grade", 3.0)

    weight_rule_info = structure["detected_weight_rule"]
    rule_name = weight_rule_info.get("rule", "by_subject_period")
    rule_label = "(materia, periodo)" if "subject_period" in str(rule_name) else "(materia)"

    return {
        "status": "ready" if not missing_required else "incomplete",
        "mapped_sheets": structure["mapped_sheets"],
        "ignored_sheets": structure["ignored_sheets"],
        "detected_grading_scale": scale_info,
        "detected_weight_rule": weight_rule_info,
        "detected_parameters": {
            "grade_scale": scale_label,
            "min_passing_grade": pass_grade,
            "weight_grouping_rule": rule_label,
        },
        "sheets": sheets_summary,
        "unmapped_sheets": structure["ignored_sheets"],
        "can_process": len(missing_required) == 0,
        "warnings": warnings,
    }


def save_mapping_template(mapping: Dict[str, Any], template_name: str = "default_template.json") -> Path:
    """Guarda el mapeo confirmado por el usuario como plantilla reutilizable."""
    out_path = TEMPLATES_DIR / template_name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4, ensure_ascii=False)
    logger.info(f"Plantilla de mapeo guardada en: {out_path}")
    return out_path


def process_confirmed_excel(file_bytes_or_path: Any, confirmed_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """
    Toma un Excel y un mapeo confirmado (hoja -> entidad, columna -> campo) y
    produce los archivos CSV en data/raw/ con columna 'extra' para columnas no mapeadas.
    REGLA: NUNCA inventa datos. Si falta obligatorio -> error; si opcional -> NULL.
    """
    logger.info("Iniciando procesamiento de Excel con mapeo confirmado...")
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if isinstance(file_bytes_or_path, (bytes, bytearray)):
        excel_source = io.BytesIO(file_bytes_or_path)
    else:
        excel_source = file_bytes_or_path

    xl = pd.ExcelFile(excel_source)
    sheet_mappings = confirmed_mapping.get("mapped_sheets", {})

    # Mapeo invertido: entity -> sheet_name
    entity_to_sheet = {}
    for sheet_name, info in sheet_mappings.items():
        entity = info.get("entity")
        if entity:
            entity_to_sheet[entity] = (sheet_name, info.get("column_mapping", {}))

    processed_entities = {}
    total_raw_rows = {}

    for entity, canonical_cols in CANONICAL_COLUMNS.items():
        if entity not in entity_to_sheet:
            # Crear archivo vacío con encabezados para compatibilidad
            df_empty = pd.DataFrame(columns=canonical_cols)
            df_empty.to_csv(RAW_DATA_DIR / f"{entity}.csv", index=False, encoding="utf-8")
            continue

        sheet_name, col_map = entity_to_sheet[entity]
        raw_df = pd.read_excel(xl, sheet_name=sheet_name, dtype=str)
        total_raw_rows[entity] = len(raw_df)

        # Validar campos obligatorios
        mandatory = MANDATORY_FIELDS.get(entity, [])
        mapped_target_fields = set(col_map.values())
        
        # Especial para students: first_name o full_name es obligatorio
        if entity == "students":
            if not any(f in mapped_target_fields for f in ["first_name", "full_name"]):
                raise ValueError(f"En la hoja '{sheet_name}' (estudiantes) falta el campo obligatorio de nombre.")
            if "student_id" not in mapped_target_fields:
                raise ValueError(f"En la hoja '{sheet_name}' (estudiantes) falta el ID obligatorio del estudiante.")
        elif entity == "assessments":
            if "assessment_id" not in mapped_target_fields:
                raise ValueError(f"En la hoja '{sheet_name}' (evaluaciones) falta assessment_id obligatorio.")
            if not any(f in mapped_target_fields for f in ["name", "assessment_name", "type", "assessment_type"]):
                raise ValueError(f"En la hoja '{sheet_name}' (evaluaciones) falta el nombre o tipo de evaluación.")
            if not any(f in mapped_target_fields for f in ["weight", "weight_percentage"]):
                raise ValueError(f"En la hoja '{sheet_name}' (evaluaciones) falta el peso/porcentaje.")
        elif entity == "grades":
            if "score" not in mapped_target_fields and "nota" not in mapped_target_fields:
                raise ValueError(f"En la hoja '{sheet_name}' (calificaciones) falta la nota/calificación.")
            if "student_id" not in mapped_target_fields or "assessment_id" not in mapped_target_fields:
                raise ValueError(f"En la hoja '{sheet_name}' (calificaciones) faltan IDs de estudiante o evaluación.")

        # Construir dataframe estandarizado
        std_df = pd.DataFrame()

        # Invertir mapeo: target_field -> excel_column
        target_to_source = {target: src for src, target in col_map.items()}

        for target_field in canonical_cols:
            if target_field == "extra":
                continue

            # Buscar coincidencias directas o sinónimos de campo
            src_col = target_to_source.get(target_field)
            if not src_col:
                # Aliases canónicos
                if target_field == "name" and "assessment_name" in target_to_source:
                    src_col = target_to_source["assessment_name"]
                elif target_field == "assessment_name" and "name" in target_to_source:
                    src_col = target_to_source["name"]
                elif target_field == "weight_percentage" and "weight" in target_to_source:
                    src_col = target_to_source["weight"]
                elif target_field == "score" and "nota" in target_to_source:
                    src_col = target_to_source["nota"]
                elif target_field == "submission_date" and "registration_date" in target_to_source:
                    src_col = target_to_source["registration_date"]
                elif target_field == "assessment_date" and "date" in target_to_source:
                    src_col = target_to_source["date"]
                elif target_field == "course_name" and "name" in target_to_source:
                    src_col = target_to_source["name"]
                elif target_field == "subject_name" and "name" in target_to_source:
                    src_col = target_to_source["name"]
                elif target_field == "period_name" and "name" in target_to_source:
                    src_col = target_to_source["name"]

            if src_col and src_col in raw_df.columns:
                series = raw_df[src_col].copy()
                if "date" in target_field or target_field in ["birth_date", "enrollment_date", "submission_date", "assessment_date", "start_date", "end_date"]:
                    series = series.apply(format_date_cell)
                std_df[target_field] = series
            else:
                # Opcional faltante: NUNCA INVENTAR, DEJAR VACÍO / NULL
                std_df[target_field] = ""

        # Manejo de full_name si first_name y last_name no vienen separados
        if entity == "students" and "full_name" in target_to_source:
            fn_col = target_to_source["full_name"]
            if fn_col in raw_df.columns:
                std_df["first_name"] = raw_df[fn_col]
                std_df["last_name"] = ""

        # Manejo de assessment_name si solo vino tipo
        if entity == "assessments" and (std_df["assessment_name"].str.strip() == "").all():
            if "assessment_type" in std_df and not (std_df["assessment_type"].str.strip() == "").all():
                std_df["assessment_name"] = std_df["assessment_type"]
            else:
                std_df["assessment_name"] = std_df["assessment_id"]

        # Empaquetar columnas no mapeadas en 'extra' como JSON por fila
        used_src_cols = set(col_map.keys())
        ignored_src_cols = [c for c in raw_df.columns if c not in used_src_cols]

        if ignored_src_cols:
            extras = []
            for _, row in raw_df.iterrows():
                row_extra = {c: str(row[c]) for c in ignored_src_cols if pd.notna(row[c])}
                extras.append(json.dumps(row_extra, ensure_ascii=False) if row_extra else "")
            std_df["extra"] = extras
        else:
            std_df["extra"] = ""

        # Si grade_id falta en grades, generarlo secuencialmente sin inventar contenido semántico
        if entity == "grades" and (std_df["grade_id"].str.strip() == "").all():
            std_df["grade_id"] = [f"G-{i+1:06d}" for i in range(len(std_df))]

        # Guardar en data/raw/{entity}.csv
        csv_file = RAW_DATA_DIR / f"{entity}.csv"
        std_df.to_csv(csv_file, index=False, encoding="utf-8")
        processed_entities[entity] = len(std_df)

    # Generar metadatos de auditoría criptográfica
    meta_path = RAW_DATA_DIR / "ingestion_metadata.json"
    files_meta = {}
    for entity in CANONICAL_COLUMNS.keys():
        fpath = RAW_DATA_DIR / f"{entity}.csv"
        if fpath.exists():
            files_meta[f"{entity}.csv"] = {
                "path": str(fpath),
                "row_count": processed_entities.get(entity, 0),
                "sha256": calculate_file_sha256(fpath) if fpath.stat().st_size > 0 else "",
            }

    metadata = {
        "generated_at": datetime.now().isoformat(),
        "random_seed": "N/A (Uploaded Excel)",
        "source": "Uploaded Excel Workbook (Custom Mapping)",
        "mapping_used": confirmed_mapping,
        "files": files_meta,
        "raw_counts": total_raw_rows,
        "processed_entities": processed_entities,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    logger.info("Ingesta raw completada sin valores inventados. Datos listos para validación.")
    return metadata


def process_uploaded_excel_file(file_content: bytes) -> Dict[str, Any]:
    """
    Función de compatibilidad: genera propuesta, aplica mapeo y ejecuta el pipeline.
    """
    preview = preview_excel_mapping(file_content)
    if not preview["can_process"]:
        raise ValueError(f"No se puede procesar el archivo. Advertencias: {preview['warnings']}")

    metadata = process_confirmed_excel(file_content, preview)

    from scripts.run_pipeline import execute_pipeline
    pipeline_success = execute_pipeline(generate_data=False)

    return {
        "success": pipeline_success,
        "metadata": metadata,
        "preview": preview,
    }


def create_excel_template() -> bytes:
    """Plantilla estándar de ejemplo."""
    output = io.BytesIO()
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    sample_data = {
        "estudiantes": [
            ["estudiante_id", "documento_numero", "nombre", "apellido", "genero", "fecha_nacimiento", "curso_id"],
            ["1", "10001", "Ana", "Gómez", "F", "2008-03-12", "101"],
            ["2", "10002", "Carlos", "Pérez", "M", "2007-11-20", "101"],
        ],
        "evaluaciones": [
            ["evaluacion_id", "materia_id", "periodo_id", "nombre", "peso", "fecha"],
            ["1", "1", "1", "Taller 1", 30.0, "2025-02-15"],
            ["2", "1", "1", "Parcial 1", 70.0, "2025-03-20"],
        ],
        "notas": [
            ["nota_id", "estudiante_id", "evaluacion_id", "nota", "fecha_registro"],
            ["1", "1", "1", 4.2, "2025-02-16"],
            ["2", "1", "2", 3.8, "2025-03-21"],
        ]
    }

    for sname, rows in sample_data.items():
        ws = wb.create_sheet(title=sname)
        for r_idx, row in enumerate(rows, start=1):
            for c_idx, val in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.border = thin_border
                if r_idx == 1:
                    cell.font = header_font
                    cell.fill = header_fill

    wb.save(output)
    output.seek(0)
    return output.getvalue()
