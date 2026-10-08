"""
Módulo de detección inteligente de entidades y columnas para cualquier Excel académico.
Combina análisis de nombres (sinónimos multilingües, normalización de tildes)
y análisis de contenido (rangos de notas, unicidad de IDs, sumas de pesos).
"""
from typing import Dict, Any, List, Optional, Tuple
import unicodedata
import re
import pandas as pd
import numpy as np


def normalize_text(text: str) -> str:
    """Elimina tildes, caracteres especiales y convierte a minúsculas snake_case."""
    if not text:
        return ""
    text = str(text).strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", "_", text).strip("_")
    return text


# Definición canónica de entidades con sinónimos de hoja
ENTITY_SYNONYMS = {
    "students": ["estudiantes", "estudiante", "alumnos", "alumno", "students", "student", "matricula", "matriculas", "pupils"],
    "courses": ["cursos", "curso", "grupos", "grupo", "grados", "grado", "courses", "course", "classes", "class", "aulas"],
    "subjects": ["materias", "materia", "asignaturas", "asignatura", "subjects", "subject", "disciplinas", "areas"],
    "teachers": ["docentes", "docente", "profesores", "profesor", "maestros", "maestro", "teachers", "teacher", "instructores"],
    "periods": ["periodos", "periodo", "terminos", "termino", "lapsos", "lapso", "bimestres", "trimestres", "periods", "period", "terms"],
    "course_subjects": ["curso_materia", "cursos_materias", "curso_materias", "asignaciones", "asignacion", "course_subject", "carga_academica"],
    "assessments": ["evaluaciones", "evaluacion", "actividades", "actividad", "tareas", "trabajos", "assessments", "assessment", "exams", "parciales"],
    "grades": ["notas", "nota", "calificaciones", "calificacion", "grades", "grade", "scores", "score", "registro_notas"],
    "attendance": ["asistencia", "asistencias", "inasistencias", "attendance", "absences", "fallas"],
    "performance_scale": ["escala_desempeno", "escala_calificaciones", "escala_notas", "escala", "desempeno", "grading_scale", "performance_scale"],
}

# Sinónimos inequívocos por campo dentro de cada entidad
FIELD_SYNONYMS = {
    "students": {
        "student_id": ["estudiante_id", "id_estudiante", "student_id", "id_alumno", "alumno_id", "codigo", "codigo_estudiante", "id"],
        "document_number": ["documento_numero", "numero_documento", "documento", "doc_identidad", "cedula", "tarjeta_identidad", "ti", "dni", "id_document"],
        "first_name": ["nombre", "nombres", "first_name", "primer_nombre"],
        "last_name": ["apellido", "apellidos", "last_name", "primer_apellido"],
        "full_name": ["nombre_completo", "estudiante_nombre", "alumno", "full_name"],
        "gender": ["genero", "sexo", "gender"],
        "birth_date": ["fecha_nacimiento", "nacimiento", "birth_date", "dob"],
        "email": ["email", "correo", "correo_electronico", "email_estudiante"],
        "course_id": ["curso_id", "id_curso", "curso", "grado", "grupo", "course_id"],
    },
    "courses": {
        "course_id": ["curso_id", "id_curso", "course_id", "id", "codigo_curso"],
        "course_name": ["nombre_curso", "curso_nombre", "nombre", "curso", "grado", "grupo", "name", "course_name"],
        "level": ["nivel", "grado_nivel", "jornada", "level"],
    },
    "subjects": {
        "subject_id": ["materia_id", "id_materia", "asignatura_id", "subject_id", "id", "codigo_materia"],
        "subject_name": ["nombre_materia", "materia_nombre", "materia", "asignatura", "nombre", "name", "subject_name"],
    },
    "teachers": {
        "teacher_id": ["docente_id", "id_docente", "profesor_id", "teacher_id", "id"],
        "document_number": ["documento_numero", "numero_documento", "documento", "cedula", "dni"],
        "first_name": ["nombre", "nombres", "first_name"],
        "last_name": ["apellido", "apellidos", "last_name"],
        "full_name": ["nombre_completo", "docente", "profesor", "full_name"],
        "email": ["email", "correo", "correo_electronico"],
        "specialty": ["especialidad", "area", "profesion"],
    },
    "periods": {
        "period_id": ["periodo_id", "id_periodo", "period_id", "periodo", "id"],
        "period_name": ["nombre_periodo", "periodo_nombre", "nombre", "periodo", "name"],
        "start_date": ["fecha_inicio", "inicio", "start_date"],
        "end_date": ["fecha_fin", "fin", "end_date"],
        "weight": ["peso", "porcentaje", "peso_porcentaje", "weight"],
    },
    "course_subjects": {
        "course_id": ["curso_id", "id_curso", "course_id"],
        "subject_id": ["materia_id", "id_materia", "subject_id"],
        "teacher_id": ["docente_id", "id_docente", "profesor_id", "teacher_id"],
        "hours_per_week": ["horas_semanales", "intensidad_horaria", "horas", "hours_per_week"],
    },
    "assessments": {
        "assessment_id": ["evaluacion_id", "id_evaluacion", "actividad_id", "assessment_id", "id"],
        "course_id": ["curso_id", "id_curso", "course_id"],
        "subject_id": ["materia_id", "id_materia", "subject_id"],
        "period_id": ["periodo_id", "id_periodo", "periodo", "period_id"],
        "name": ["nombre", "nombre_evaluacion", "actividad", "descripcion", "name", "title"],
        "weight": ["peso", "porcentaje", "peso_porcentaje", "weight", "valor_porcentual"],
        "date": ["fecha", "fecha_evaluacion", "fecha_entrega", "date"],
        "type": ["tipo", "tipo_evaluacion", "categoria", "type"],
    },
    "grades": {
        "grade_id": ["nota_id", "id_nota", "calificacion_id", "grade_id", "id"],
        "student_id": ["estudiante_id", "id_estudiante", "alumno_id", "student_id"],
        "assessment_id": ["evaluacion_id", "id_evaluacion", "actividad_id", "assessment_id"],
        "score": ["nota", "calificacion", "valor", "score", "grade", "resultado"],
        "registration_date": ["fecha_registro", "fecha", "created_at", "registration_date"],
    },
    "attendance": {
        "attendance_id": ["asistencia_id", "id_asistencia", "id"],
        "student_id": ["estudiante_id", "id_estudiante", "alumno_id", "student_id"],
        "course_id": ["curso_id", "id_curso", "course_id"],
        "period_id": ["periodo_id", "id_periodo", "periodo", "period_id"],
        "total_classes": ["dias_clase", "total_clases", "clases_totales", "total_classes"],
        "absences": ["inasistencias", "fallas", "ausencias", "absences"],
    },
    "performance_scale": {
        "level": ["nivel", "desempeno", "escala", "level"],
        "min_score": ["nota_minima", "min_nota", "rango_min", "min_score", "minimo"],
        "max_score": ["nota_maxima", "max_nota", "rango_max", "max_score", "maximo"],
        "description": ["descripcion", "mensaje", "criterio", "description"],
    },
}

IGNORED_SHEET_KEYWORDS = ["diccionario", "errores_sembrados", "readme", "instrucciones", "glosario", "hoja_ejemplo"]


def score_sheet_for_entity(sheet_name: str, sheet_columns: List[str], entity: str) -> float:
    """Calcula el score de coincidencia entre una hoja y una entidad del modelo."""
    norm_sheet = normalize_text(sheet_name)
    
    # Check ignored sheets
    for ign in IGNORED_SHEET_KEYWORDS:
        if ign in norm_sheet:
            return 0.0

    name_score = 0.0
    synonyms = ENTITY_SYNONYMS.get(entity, [])
    if norm_sheet in synonyms:
        name_score = 0.6
    elif any(s in norm_sheet or norm_sheet in s for s in synonyms):
        name_score = 0.4

    # Column coverage score
    field_syns = FIELD_SYNONYMS.get(entity, {})
    norm_cols = [normalize_text(c) for c in sheet_columns]
    
    matched_fields = 0
    total_target_fields = len(field_syns)
    
    for field, syns in field_syns.items():
        if any(c in syns for c in norm_cols):
            matched_fields += 1

    col_score = (matched_fields / total_target_fields) * 0.4 if total_target_fields > 0 else 0.0

    # Key mandatory columns presence
    if entity == "grades":
        has_score = any(c in ["nota", "calificacion", "score", "grade"] for c in norm_cols)
        has_student = any(c in ["estudiante_id", "student_id", "alumno_id"] for c in norm_cols)
        has_eval = any(c in ["evaluacion_id", "assessment_id", "actividad_id"] for c in norm_cols)
        if has_score and has_student and has_eval:
            col_score += 0.3
    elif entity == "students":
        has_name = any(c in ["nombre", "nombres", "nombre_completo"] for c in norm_cols)
        if has_name:
            col_score += 0.2
    elif entity == "assessments":
        has_weight = any(c in ["peso", "porcentaje", "weight"] for c in norm_cols)
        has_eval_name = any(c in ["nombre", "actividad", "evaluacion"] for c in norm_cols)
        if has_weight or has_eval_name:
            col_score += 0.2

    total_score = min(1.0, round(name_score + col_score, 2))
    return total_score


def map_columns_for_entity(sheet_columns: List[str], entity: str) -> Tuple[Dict[str, str], List[str], Dict[str, float]]:
    """
    Mapea columnas del Excel a campos de la entidad asegurando relación 1 a 1 estricta.
    Retorna: (mapping: {excel_col: field_name}, ignored_cols, confidences: {field_name: confidence})
    """
    field_syns = FIELD_SYNONYMS.get(entity, {})
    col_mappings: Dict[str, str] = {}
    confidences: Dict[str, float] = {}
    used_fields = set()
    used_cols = set()

    # Pass 1: Exact and high-confidence synonym matches
    candidates = []
    for col in sheet_columns:
        norm_col = normalize_text(col)
        for field, syns in field_syns.items():
            score = 0.0
            if norm_col in syns:
                # Direct match with top synonym or exact field name
                score = 1.0 if norm_col == syns[0] or norm_col == field else 0.95
            elif any(s in norm_col or norm_col in s for s in syns):
                score = 0.70
            
            if score > 0.0:
                candidates.append((score, col, field))

    # Sort descending by score
    candidates.sort(key=lambda x: x[0], reverse=True)

    for score, col, field in candidates:
        if col not in used_cols and field not in used_fields:
            col_mappings[col] = field
            confidences[field] = score
            used_cols.add(col)
            used_fields.add(field)

    ignored_cols = [c for c in sheet_columns if c not in used_cols]
    return col_mappings, ignored_cols, confidences


def detect_grading_scale(df_grades: Optional[pd.DataFrame], df_scale: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Detecta dinámicamente la escala de notas y la nota mínima aprobatoria.
    """
    if df_scale is not None and not df_scale.empty:
        # Extraer de escala_desempeno si existe
        scale_records = df_scale.to_dict(orient="records")
        max_limit = float(df_scale["nota_maxima"].max()) if "nota_maxima" in df_scale else 5.0
        passing_grade = 3.0
        if "nota_minima" in df_scale:
            # Typically level 'Básico' min_score
            basic_row = df_scale[df_scale["nivel"].astype(str).str.lower().str.contains("basico|basic")]
            if not basic_row.empty:
                passing_grade = float(basic_row["nota_minima"].iloc[0])
            else:
                passing_grade = float(df_scale["nota_minima"].median())
        scale_type = "0-5" if max_limit <= 5.5 else ("0-10" if max_limit <= 10.5 else "0-100")
        return {
            "scale_type": scale_type,
            "min_grade": 0.0,
            "max_grade": max_limit,
            "passing_grade": passing_grade,
            "scale_table": scale_records,
        }

    # Infer from grades distribution
    if df_grades is not None and not df_grades.empty and "nota" in df_grades:
        from src.ingestion.profiler import _to_float_if_possible
        vals = df_grades["nota"].apply(_to_float_if_possible).dropna()
        q99 = vals.quantile(0.99) if len(vals) > 0 else 5.0
        if q99 <= 5.2:
            return {"scale_type": "0-5", "min_grade": 0.0, "max_grade": 5.0, "passing_grade": 3.0}
        elif q99 <= 10.5:
            return {"scale_type": "0-10", "min_grade": 0.0, "max_grade": 10.0, "passing_grade": 6.0}
        else:
            return {"scale_type": "0-100", "min_grade": 0.0, "max_grade": 100.0, "passing_grade": 60.0}

    return {"scale_type": "0-5", "min_grade": 0.0, "max_grade": 5.0, "passing_grade": 3.0}


def detect_weight_rule(df_assessments: pd.DataFrame) -> Dict[str, Any]:
    """
    Prueba por qué agrupación los porcentajes de evaluaciones suman 100%
    (por materia, por materia+periodo, por curso+materia+periodo, etc.).
    """
    if df_assessments is None or df_assessments.empty:
        return {"rule": "none", "group_cols": []}

    cols = df_assessments.columns.tolist()
    weight_col = next((c for c in cols if normalize_text(c) in ["peso", "porcentaje", "weight"]), None)
    if not weight_col:
        return {"rule": "none", "group_cols": []}

    from src.ingestion.profiler import _to_float_if_possible
    df_clean = df_assessments.copy()
    df_clean["clean_weight"] = df_clean[weight_col].apply(_to_float_if_possible).fillna(0.0)

    # Test candidate groupings
    group_candidates = [
        ("by_subject_period", ["materia_id", "periodo_id"]),
        ("by_course_subject_period", ["curso_id", "materia_id", "periodo_id"]),
        ("by_subject", ["materia_id"]),
        ("by_period", ["periodo_id"]),
    ]

    best_rule = "by_subject_period"
    best_matching_pct = 0.0
    best_group_cols = ["materia_id", "periodo_id"]

    for rule_name, group_cols in group_candidates:
        if all(c in df_clean.columns for c in group_cols):
            grouped = df_clean.groupby(group_cols)["clean_weight"].sum()
            # Count groups where sum is close to 100 (or 1.0)
            valid_100 = ((grouped >= 99.0) & (grouped <= 101.0)) | ((grouped >= 0.99) & (grouped <= 1.01))
            pct = valid_100.mean() if len(grouped) > 0 else 0.0
            if pct > best_matching_pct:
                best_matching_pct = pct
                best_rule = rule_name
                best_group_cols = group_cols

    return {
        "rule": best_rule,
        "group_cols": best_group_cols,
        "valid_group_ratio": round(float(best_matching_pct), 4),
    }


def detect_workbook_structure(workbook_profile: Dict[str, Any], excel_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Genera la propuesta completa de mapeo para un libro de trabajo Excel.
    """
    sheets_info = workbook_profile.get("sheets", {})
    sheet_to_entity: Dict[str, Dict[str, Any]] = {}
    assigned_entities = set()
    ignored_sheets = []

    # Score each sheet against each entity
    scored_pairs = []
    for sheet_name, sdata in sheets_info.items():
        cols = list(sdata.get("columns", {}).keys())
        for entity in ENTITY_SYNONYMS.keys():
            score = score_sheet_for_entity(sheet_name, cols, entity)
            if score >= 0.4:
                scored_pairs.append((score, sheet_name, entity))

    # Sort descending
    scored_pairs.sort(key=lambda x: x[0], reverse=True)

    for score, sheet_name, entity in scored_pairs:
        if sheet_name not in sheet_to_entity and entity not in assigned_entities:
            cols = list(sheets_info[sheet_name].get("columns", {}).keys())
            col_map, ignored_cols, confidences = map_columns_for_entity(cols, entity)
            sheet_to_entity[sheet_name] = {
                "entity": entity,
                "confidence": score,
                "column_mapping": col_map,
                "ignored_columns": ignored_cols,
                "field_confidences": confidences,
                "row_count": sheets_info[sheet_name].get("row_count", 0),
            }
            assigned_entities.add(entity)

    for sheet_name in sheets_info.keys():
        if sheet_name not in sheet_to_entity:
            ignored_sheets.append({
                "sheet_name": sheet_name,
                "reason": "Ignorada (no coincide con entidades académicas o es auxiliar)",
                "row_count": sheets_info[sheet_name].get("row_count", 0),
            })

    # Read scale and weight rules if excel path available
    grading_scale = {"scale_type": "0-5", "min_grade": 0.0, "max_grade": 5.0, "passing_grade": 3.0}
    weight_rule = {"rule": "by_subject_period", "group_cols": ["materia_id", "periodo_id"]}

    if excel_file_path:
        try:
            if hasattr(excel_file_path, "seek"):
                excel_file_path.seek(0)
            xl = pd.ExcelFile(excel_file_path)
            # Find scale sheet
            scale_sheet = next((s for s, m in sheet_to_entity.items() if m["entity"] == "performance_scale"), None)
            df_scale = pd.read_excel(xl, sheet_name=scale_sheet) if scale_sheet else None

            # Find grades sheet
            grades_sheet = next((s for s, m in sheet_to_entity.items() if m["entity"] == "grades"), None)
            df_grades = pd.read_excel(xl, sheet_name=grades_sheet) if grades_sheet else None

            grading_scale = detect_grading_scale(df_grades, df_scale)

            # Find assessments sheet
            assess_sheet = next((s for s, m in sheet_to_entity.items() if m["entity"] == "assessments"), None)
            if assess_sheet:
                df_assess = pd.read_excel(xl, sheet_name=assess_sheet)
                weight_rule = detect_weight_rule(df_assess)
        except Exception:
            pass

    return {
        "mapped_sheets": sheet_to_entity,
        "ignored_sheets": ignored_sheets,
        "detected_grading_scale": grading_scale,
        "detected_weight_rule": weight_rule,
        "is_ready_for_preview": True,
    }
