"""
Data Validation and Quality Assurance Module.
Aplica validaciones estrictas, cuarentena de errores con motivos detallados,
conversión de texto con comas a flotantes (con auditoría), normalización de género
y nombres, validación dinámica de pesos por agrupación (materia + periodo),
y reglas de fechas relativas a la fecha actual.
"""
import sys
import re
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import RAW_DATA_DIR, PROCESSED_DATA_DIR, ERRORS_DATA_DIR
from src.utils.logger import get_logger

logger = get_logger("validate_data")

EXPECTED_FILES = [
    "courses.csv", "subjects.csv", "students.csv", "assessments.csv", "grades.csv"
]

EXPECTED_SCHEMAS = {
    "courses.csv": ["course_id", "course_name"],
    "subjects.csv": ["subject_id", "subject_name"],
    "students.csv": ["student_id", "first_name"],
    "assessments.csv": ["assessment_id", "assessment_name", "weight_percentage"],
    "grades.csv": ["grade_id", "assessment_id", "student_id", "score"]
}


def is_valid_date(val: Any) -> bool:
    """Valida si un valor puede ser interpretado como una fecha válida de calendario."""
    if pd.isnull(val):
        return False
    val_str = str(val).strip()
    if not val_str or val_str in ("nan", "None", ""):
        return False
    for fmt in (
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y",
        "%Y/%m/%d %H:%M:%S", "%Y/%m/%d",
        "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"
    ):
        try:
            datetime.strptime(val_str, fmt)
            return True
        except (ValueError, TypeError):
            continue
    return False


def parse_date(val: Any) -> Optional[date]:
    """Parsea una fecha a objeto date."""
    if pd.isnull(val):
        return None
    val_str = str(val).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y",
        "%Y/%m/%d %H:%M:%S", "%Y/%m/%d",
        "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"
    ):
        try:
            return datetime.strptime(val_str, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def validate_courses(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    errors = []
    corrections = []
    if df.empty:
        return df, pd.DataFrame(columns=list(df.columns) + ["error_reason"]), corrections

    valid_mask = pd.Series(True, index=df.index)

    # 1. Null PK
    for idx, row in df.iterrows():
        cid = str(row.get("course_id", "")).strip()
        if not cid or cid in ("nan", "None"):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = "Null or empty course_id"
            errors.append(err)

    # 2. Duplicate PK
    dups = df[valid_mask & df["course_id"].duplicated(keep="first")].index
    for idx in dups:
        valid_mask[idx] = False
        err = df.loc[idx].to_dict()
        err["error_reason"] = f"Duplicate course_id primary key: {err['course_id']}"
        errors.append(err)

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df, corrections


def validate_subjects(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    errors = []
    corrections = []
    if df.empty:
        return df, pd.DataFrame(columns=list(df.columns) + ["error_reason"]), corrections

    valid_mask = pd.Series(True, index=df.index)

    # Mandatory subject_id, subject_name
    for idx, row in df.iterrows():
        sid = str(row.get("subject_id", "")).strip()
        sname = str(row.get("subject_name", "")).strip()
        if not sid or sid in ("nan", "None"):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = "Null or empty subject_id"
            errors.append(err)
        elif not sname or sname in ("nan", "None"):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = "Null or empty subject_name"
            errors.append(err)

    # Duplicate PK
    dups = df[valid_mask & df["subject_id"].duplicated(keep="first")].index
    for idx in dups:
        valid_mask[idx] = False
        err = df.loc[idx].to_dict()
        err["error_reason"] = f"Duplicate subject_id: {err['subject_id']}"
        errors.append(err)

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df, corrections


def validate_students(
    df: pd.DataFrame,
    valid_courses_ids: Optional[set] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    errors = []
    corrections = []
    if df.empty:
        return df, pd.DataFrame(columns=list(df.columns) + ["error_reason"]), corrections

    valid_mask = pd.Series(True, index=df.index)
    today = date.today()

    # Pass 1: Normalizations for names and genders
    for idx, row in df.iterrows():
        # Trim and normalize names
        orig_first = str(row.get("first_name", ""))
        clean_first = " ".join(orig_first.split()).strip()
        if clean_first != orig_first and orig_first not in ("nan", "None"):
            corrections.append({
                "entity": "students",
                "id": str(row.get("student_id", "")),
                "field": "first_name",
                "original": orig_first,
                "corrected": clean_first,
                "reason": "Espacios y formato en nombre corregidos"
            })
            df.at[idx, "first_name"] = clean_first

        # Normalize gender
        raw_gender = str(row.get("gender", "")).strip()
        if raw_gender and raw_gender not in ("nan", "None"):
            g_low = raw_gender.lower()
            std_gender = None
            if g_low in ("m", "masculino", "male", "hombre"):
                std_gender = "M"
            elif g_low in ("f", "femenino", "female", "fem", "mujer"):
                std_gender = "F"

            if std_gender and std_gender != raw_gender:
                corrections.append({
                    "entity": "students",
                    "id": str(row.get("student_id", "")),
                    "field": "gender",
                    "original": raw_gender,
                    "corrected": std_gender,
                    "reason": "Normalización de género a estándar ('M'/'F')"
                })
                df.at[idx, "gender"] = std_gender

    # Pass 2: Hard Errors and Quarantining
    for idx, row in df.iterrows():
        sid = str(row.get("student_id", "")).strip()
        if not sid or sid in ("nan", "None"):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = "Null or empty student_id"
            errors.append(err)
            continue

        # Check birth_date validity (not future, not impossible like 1900 or 2031)
        bdate_val = row.get("birth_date")
        if pd.notna(bdate_val) and str(bdate_val).strip() not in ("", "nan", "None"):
            pdate = parse_date(bdate_val)
            if not pdate:
                valid_mask[idx] = False
                err = row.to_dict()
                err["error_reason"] = f"Invalid birth_date format: '{bdate_val}'"
                errors.append(err)
                continue
            elif pdate.year < 1920 or pdate > today:
                valid_mask[idx] = False
                err = row.to_dict()
                err["error_reason"] = f"Impossible birth_date: '{bdate_val}' (out of biological bounds)"
                errors.append(err)
                continue

        # Check course FK if valid_courses_ids is supplied and row has course_id
        cid = str(row.get("course_id", "")).strip()
        if cid and cid not in ("nan", "None") and valid_courses_ids is not None and len(valid_courses_ids) > 0:
            if cid not in valid_courses_ids:
                valid_mask[idx] = False
                err = row.to_dict()
                err["error_reason"] = f"curso_id inexistente ({cid})"
                errors.append(err)
                continue

    # Duplicate student_id
    dups_sid = df[valid_mask & df["student_id"].duplicated(keep="first")].index
    for idx in dups_sid:
        valid_mask[idx] = False
        err = df.loc[idx].to_dict()
        err["error_reason"] = f"estudiante_id duplicado: {err['student_id']}"
        errors.append(err)

    # Duplicate document_number (if present)
    has_doc = valid_mask & df["document_number"].notna() & (df["document_number"].astype(str).str.strip().ne("")) & (df["document_number"].astype(str).ne("nan"))
    dups_doc = df[has_doc & df["document_number"].duplicated(keep="first")].index
    for idx in dups_doc:
        valid_mask[idx] = False
        err = df.loc[idx].to_dict()
        err["error_reason"] = f"documento duplicado: {err['document_number']}"
        errors.append(err)

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df, corrections


def validate_assessments(
    df: pd.DataFrame,
    valid_subjects_ids: Optional[set] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    errors = []
    corrections = []
    if df.empty:
        return df, pd.DataFrame(columns=list(df.columns) + ["error_reason"]), corrections

    valid_mask = pd.Series(True, index=df.index)

    # 1. Null check on mandatory columns
    for idx, row in df.iterrows():
        aid = str(row.get("assessment_id", "")).strip()
        aname = str(row.get("assessment_name", "")).strip()
        wval = str(row.get("weight_percentage", "")).strip()

        if not aid or aid in ("nan", "None"):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = "Null or empty assessment_id"
            errors.append(err)
            continue

        if not aname or aname in ("nan", "None"):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = "Null or empty assessment_name"
            errors.append(err)
            continue

        # Check numeric weight
        w_clean = wval.replace(",", ".")
        try:
            w_float = float(w_clean)
            if w_float < 0.0 or w_float > 100.0:
                valid_mask[idx] = False
                err = row.to_dict()
                err["error_reason"] = f"Weight percentage out of allowed range [0-100%]: {w_float}"
                errors.append(err)
                continue
        except (ValueError, TypeError):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = f"Non-numeric weight percentage: '{wval}'"
            errors.append(err)
            continue

        # Check FK subject_id if subjects list provided
        sub_id = str(row.get("subject_id", "")).strip()
        if sub_id and sub_id not in ("nan", "None") and valid_subjects_ids is not None and len(valid_subjects_ids) > 0:
            if sub_id not in valid_subjects_ids:
                valid_mask[idx] = False
                err = row.to_dict()
                err["error_reason"] = f"Foreign key violation: subject_id '{sub_id}' does not exist"
                errors.append(err)
                continue

    # Duplicate PK
    dups_aid = df[valid_mask & df["assessment_id"].duplicated(keep="first")].index
    for idx in dups_aid:
        valid_mask[idx] = False
        err = df.loc[idx].to_dict()
        err["error_reason"] = f"Duplicate assessment_id: {err['assessment_id']}"
        errors.append(err)

    # 2. Dynamic Weight Summing Rule
    # Group by (subject_id, period_id) if period_id exists, else by subject_id
    interim_valid = df[valid_mask].copy()
    if not interim_valid.empty:
        interim_valid["clean_w"] = interim_valid["weight_percentage"].astype(str).str.replace(",", ".").astype(float)
        
        has_period = "period_id" in interim_valid.columns and not interim_valid["period_id"].astype(str).str.strip().isin(["", "nan", "None"]).all()
        group_cols = ["subject_id", "period_id"] if has_period else ["subject_id"]

        grouped_sums = interim_valid.groupby(group_cols)["clean_w"].sum()
        
        # Identificar grupos que no sumen 100% (+/- 0.5% tolerancia)
        invalid_groups = set()
        for grp_key, total_w in grouped_sums.items():
            if abs(total_w - 100.0) > 0.5 and abs(total_w - 1.0) > 0.01:
                invalid_groups.add(grp_key)

        if invalid_groups:
            for idx in interim_valid.index:
                row = interim_valid.loc[idx]
                grp_val = tuple(row[c] for c in group_cols) if len(group_cols) > 1 else row[group_cols[0]]
                if grp_val in invalid_groups:
                    valid_mask[idx] = False
                    err = df.loc[idx].to_dict()
                    tot = round(float(grouped_sums[grp_val]), 2)
                    err["error_reason"] = f"pesos de evaluación del grupo {grp_val} suman {tot}%, esperado 100%"
                    errors.append(err)

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df, corrections


def validate_grades(
    df: pd.DataFrame,
    valid_students_ids: set,
    valid_assessments_ids: set,
    max_scale: float = 5.0
) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    errors = []
    corrections = []
    if df.empty:
        return df, pd.DataFrame(columns=list(df.columns) + ["error_reason"]), corrections

    valid_mask = pd.Series(True, index=df.index)
    today = date.today()

    # Pass 1: Deduplicate identical rows (seeded duplicate rows)
    # Deduplicate on (student_id, assessment_id, score, submission_date)
    dup_cols = [c for c in ["student_id", "assessment_id", "score", "submission_date"] if c in df.columns]
    if len(dup_cols) >= 2:
        dups_idx = df[df.duplicated(subset=dup_cols, keep="first")].index
        for idx in dups_idx:
            valid_mask[idx] = False
            err = df.loc[idx].to_dict()
            err["error_reason"] = "fila duplicada"
            errors.append(err)

    # Pass 2: Value conversions and error isolation
    for idx, row in df.iterrows():
        if not valid_mask[idx]:
            continue

        raw_score = row.get("score")
        if pd.isna(raw_score) or str(raw_score).strip() in ("", "nan", "None"):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = "nota nula"
            errors.append(err)
            continue

        score_str = str(raw_score).strip()

        # Handle comma decimals: convert and log transformation
        if re.match(r"^-?\d+,\d+$", score_str):
            clean_num_str = score_str.replace(",", ".")
            corrections.append({
                "entity": "grades",
                "id": str(row.get("grade_id", idx)),
                "field": "score",
                "original": score_str,
                "corrected": clean_num_str,
                "reason": f"Conversión de decimal con coma '{score_str}' a formato punto '{clean_num_str}'"
            })
            df.at[idx, "score"] = clean_num_str
            score_str = clean_num_str

        # Check numeric conversion
        try:
            score_float = float(score_str)
            if score_float < 0.0 or score_float > max_scale:
                valid_mask[idx] = False
                err = row.to_dict()
                err["error_reason"] = f"nota fuera de rango ({score_float})"
                errors.append(err)
                continue
        except (ValueError, TypeError):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = f"nota no numérica ('{raw_score}')"
            errors.append(err)
            continue

        # Foreign Key: student_id
        sid = str(row.get("student_id", "")).strip()
        if valid_students_ids and sid not in valid_students_ids:
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = f"estudiante_id inexistente ({sid})"
            errors.append(err)
            continue

        # Foreign Key: assessment_id
        aid = str(row.get("assessment_id", "")).strip()
        if valid_assessments_ids and aid not in valid_assessments_ids:
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = f"evaluacion_id inexistente ({aid})"
            errors.append(err)
            continue

        # Date validations: valid format and not future
        sub_date = row.get("submission_date")
        if pd.notna(sub_date) and str(sub_date).strip() not in ("", "nan", "None"):
            pdate = parse_date(sub_date)
            if not pdate:
                valid_mask[idx] = False
                err = row.to_dict()
                err["error_reason"] = f"fecha inválida (texto '{sub_date}')"
                errors.append(err)
                continue
            elif pdate > today:
                valid_mask[idx] = False
                err = row.to_dict()
                err["error_reason"] = f"fecha futura ({sub_date})"
                errors.append(err)
                continue

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df, corrections


def validate_attendance(
    df: pd.DataFrame,
    valid_students_ids: Optional[set] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    errors = []
    corrections = []
    if df.empty:
        return df, pd.DataFrame(columns=list(df.columns) + ["error_reason"]), corrections

    valid_mask = pd.Series(True, index=df.index)

    for idx, row in df.iterrows():
        sid = str(row.get("student_id", "")).strip()
        if not sid or sid in ("nan", "None"):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = "Null or empty student_id"
            errors.append(err)
            continue

        # Check total_classes and absences
        tot_str = str(row.get("total_classes", "")).strip()
        abs_str = str(row.get("absences", "")).strip()

        try:
            tot = int(float(tot_str))
            absences = int(float(abs_str))

            if absences < 0:
                valid_mask[idx] = False
                err = row.to_dict()
                err["error_reason"] = "inasistencias negativas"
                errors.append(err)
                continue

            if absences > tot:
                valid_mask[idx] = False
                err = row.to_dict()
                err["error_reason"] = "inasistencias > días de clase"
                errors.append(err)
                continue
        except (ValueError, TypeError):
            valid_mask[idx] = False
            err = row.to_dict()
            err["error_reason"] = "Valores de asistencia no enteros"
            errors.append(err)
            continue

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df, corrections


def run_validation(max_scale: float = 5.0) -> Dict[str, Any]:
    """
    Ejecuta el pipeline de validación y cuarentena para todas las entidades.
    Escribe data/processed/ y data/errors/, registrando correcciones de comas y normalizaciones.
    """
    logger.info("Iniciando validación y cuarentena de datos raw...")
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ERRORS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    summary = {}
    all_corrections = []

    # 1. Cursos
    raw_courses = pd.read_csv(RAW_DATA_DIR / "courses.csv", dtype=str) if (RAW_DATA_DIR / "courses.csv").exists() else pd.DataFrame()
    val_courses, err_courses, corr_courses = validate_courses(raw_courses)
    val_courses.to_csv(PROCESSED_DATA_DIR / "courses.csv", index=False, encoding="utf-8")
    err_courses.to_csv(ERRORS_DATA_DIR / "courses_errors.csv", index=False, encoding="utf-8")
    valid_courses_ids = set(val_courses["course_id"].astype(str).str.strip()) if not val_courses.empty else set()
    all_corrections.extend(corr_courses)
    summary["courses"] = {"total": len(raw_courses), "valid": len(val_courses), "errors": len(err_courses)}

    # 2. Materias
    raw_subjects = pd.read_csv(RAW_DATA_DIR / "subjects.csv", dtype=str) if (RAW_DATA_DIR / "subjects.csv").exists() else pd.DataFrame()
    val_subjects, err_subjects, corr_subjects = validate_subjects(raw_subjects)
    val_subjects.to_csv(PROCESSED_DATA_DIR / "subjects.csv", index=False, encoding="utf-8")
    err_subjects.to_csv(ERRORS_DATA_DIR / "subjects_errors.csv", index=False, encoding="utf-8")
    valid_subjects_ids = set(val_subjects["subject_id"].astype(str).str.strip()) if not val_subjects.empty else set()
    all_corrections.extend(corr_subjects)
    summary["subjects"] = {"total": len(raw_subjects), "valid": len(val_subjects), "errors": len(err_subjects)}

    # 3. Estudiantes
    raw_students = pd.read_csv(RAW_DATA_DIR / "students.csv", dtype=str) if (RAW_DATA_DIR / "students.csv").exists() else pd.DataFrame()
    val_students, err_students, corr_students = validate_students(raw_students, valid_courses_ids)
    val_students.to_csv(PROCESSED_DATA_DIR / "students.csv", index=False, encoding="utf-8")
    err_students.to_csv(ERRORS_DATA_DIR / "students_errors.csv", index=False, encoding="utf-8")
    valid_students_ids = set(val_students["student_id"].astype(str).str.strip()) if not val_students.empty else set()
    all_corrections.extend(corr_students)
    summary["students"] = {"total": len(raw_students), "valid": len(val_students), "errors": len(err_students)}

    # 4. Evaluaciones
    raw_assessments = pd.read_csv(RAW_DATA_DIR / "assessments.csv", dtype=str) if (RAW_DATA_DIR / "assessments.csv").exists() else pd.DataFrame()
    val_assessments, err_assessments, corr_assessments = validate_assessments(raw_assessments, valid_subjects_ids)
    val_assessments.to_csv(PROCESSED_DATA_DIR / "assessments.csv", index=False, encoding="utf-8")
    err_assessments.to_csv(ERRORS_DATA_DIR / "assessments_errors.csv", index=False, encoding="utf-8")
    valid_assessments_ids = set(val_assessments["assessment_id"].astype(str).str.strip()) if not val_assessments.empty else set()
    all_corrections.extend(corr_assessments)
    summary["assessments"] = {"total": len(raw_assessments), "valid": len(val_assessments), "errors": len(err_assessments)}

    # 5. Calificaciones
    raw_grades = pd.read_csv(RAW_DATA_DIR / "grades.csv", dtype=str) if (RAW_DATA_DIR / "grades.csv").exists() else pd.DataFrame()
    val_grades, err_grades, corr_grades = validate_grades(raw_grades, valid_students_ids, valid_assessments_ids, max_scale=max_scale)
    val_grades.to_csv(PROCESSED_DATA_DIR / "grades.csv", index=False, encoding="utf-8")
    err_grades.to_csv(ERRORS_DATA_DIR / "grades_errors.csv", index=False, encoding="utf-8")
    all_corrections.extend(corr_grades)
    summary["grades"] = {"total": len(raw_grades), "valid": len(val_grades), "errors": len(err_grades)}

    # 6. Asistencia (opcional)
    if (RAW_DATA_DIR / "attendance.csv").exists():
        raw_att = pd.read_csv(RAW_DATA_DIR / "attendance.csv", dtype=str)
        if not raw_att.empty:
            val_att, err_att, corr_att = validate_attendance(raw_att, valid_students_ids)
            val_att.to_csv(PROCESSED_DATA_DIR / "attendance.csv", index=False, encoding="utf-8")
            err_att.to_csv(ERRORS_DATA_DIR / "attendance_errors.csv", index=False, encoding="utf-8")
            all_corrections.extend(corr_att)
            summary["attendance"] = {"total": len(raw_att), "valid": len(val_att), "errors": len(err_att)}

    # 7. Periodos y otras tablas opcionales: copiar directo a processed si existen
    for opt_entity in ["periods", "teachers", "course_subjects", "performance_scale"]:
        opt_path = RAW_DATA_DIR / f"{opt_entity}.csv"
        if opt_path.exists():
            df_opt = pd.read_csv(opt_path, dtype=str)
            df_opt.to_csv(PROCESSED_DATA_DIR / f"{opt_entity}.csv", index=False, encoding="utf-8")

    # Guardar registro de correcciones y normalizaciones
    pd.DataFrame(all_corrections).to_csv(ERRORS_DATA_DIR / "corrections_log.csv", index=False, encoding="utf-8")

    logger.info(f"Validación finalizada con éxito. Resumen: {summary}")
    return {
        "summary": summary,
        "total_corrections": len(all_corrections),
        "corrections": all_corrections,
    }


if __name__ == "__main__":
    res = run_validation()
    print("Resumen de validación:", res["summary"])
