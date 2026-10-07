"""
Data Validation Module.
Enforces data quality contracts, schema conformance, range checks, referential integrity,
and business rules (such as subject assessment weights summing to 100%).
Invalid records are never deleted; they are quarantined in data/errors/ with an error_reason.
Valid records are written to data/processed/ for subsequent database loading.
Raw data remains strictly immutable.
"""
import sys
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

EXPECTED_SCHEMAS = {
    "courses.csv": ["course_id", "course_name", "grade_level", "academic_year"],
    "subjects.csv": ["subject_id", "subject_name", "course_id", "department"],
    "students.csv": ["student_id", "first_name", "last_name", "email", "course_id", "enrollment_date", "status"],
    "assessments.csv": ["assessment_id", "subject_id", "assessment_name", "assessment_type", "weight_percentage", "assessment_date"],
    "grades.csv": ["grade_id", "assessment_id", "student_id", "score", "submission_date", "feedback"]
}


def is_valid_date(val: Any) -> bool:
    """Checks if a string or object can be parsed as a valid calendar date."""
    if pd.isnull(val):
        return False
    val_str = str(val).strip()
    if not val_str:
        return False
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            datetime.strptime(val_str, fmt)
            return True
        except (ValueError, TypeError):
            continue
    return False


def parse_date(val: Any) -> Optional[datetime]:
    """Attempts to parse a date into a datetime object."""
    if pd.isnull(val):
        return None
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(val_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def validate_courses(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Validates courses dataset."""
    errors = []
    valid_mask = pd.Series(True, index=df.index)

    # 1. Null check on mandatory columns
    for col in ["course_id", "course_name", "grade_level", "academic_year"]:
        null_idx = df[df[col].isnull() | (df[col].astype(str).str.strip() == "")].index
        for idx in null_idx:
            if valid_mask[idx]:
                valid_mask[idx] = False
                err_row = df.loc[idx].to_dict()
                err_row["error_reason"] = f"Null value in mandatory column: {col}"
                errors.append(err_row)

    # 2. Duplicate PK
    dups = df[df["course_id"].duplicated(keep="first")].index
    for idx in dups:
        if valid_mask[idx]:
            valid_mask[idx] = False
            err_row = df.loc[idx].to_dict()
            err_row["error_reason"] = "Duplicate course_id primary key"
            errors.append(err_row)

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df


def validate_subjects(df: pd.DataFrame, valid_courses_ids: set) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Validates subjects dataset."""
    errors = []
    valid_mask = pd.Series(True, index=df.index)

    for col in ["subject_id", "subject_name", "course_id"]:
        null_idx = df[df[col].isnull() | (df[col].astype(str).str.strip() == "")].index
        for idx in null_idx:
            if valid_mask[idx]:
                valid_mask[idx] = False
                err_row = df.loc[idx].to_dict()
                err_row["error_reason"] = f"Null value in mandatory column: {col}"
                errors.append(err_row)

    # Duplicate PK
    dups = df[df["subject_id"].duplicated(keep="first")].index
    for idx in dups:
        if valid_mask[idx]:
            valid_mask[idx] = False
            err_row = df.loc[idx].to_dict()
            err_row["error_reason"] = "Duplicate subject_id primary key"
            errors.append(err_row)

    # FK to courses (only if valid courses exist)
    if valid_courses_ids:
        fk_err = df[~df["course_id"].astype(str).isin(valid_courses_ids)].index
        for idx in fk_err:
            if valid_mask[idx]:
                valid_mask[idx] = False
                err_row = df.loc[idx].to_dict()
                err_row["error_reason"] = f"Foreign key violation: course_id '{df.loc[idx, 'course_id']}' does not exist"
                errors.append(err_row)

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df


def validate_students(df: pd.DataFrame, valid_courses_ids: set) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Validates students dataset."""
    errors = []
    valid_mask = pd.Series(True, index=df.index)

    # Mandatory fields
    for col in ["student_id", "first_name", "last_name", "course_id"]:
        null_idx = df[df[col].isnull() | (df[col].astype(str).str.strip() == "")].index
        for idx in null_idx:
            if valid_mask[idx]:
                valid_mask[idx] = False
                err_row = df.loc[idx].to_dict()
                err_row["error_reason"] = f"Null value in mandatory column: {col}"
                errors.append(err_row)

    # Duplicate student_id
    dups = df[df["student_id"].duplicated(keep="first")].index
    for idx in dups:
        if valid_mask[idx]:
            valid_mask[idx] = False
            err_row = df.loc[idx].to_dict()
            err_row["error_reason"] = f"Duplicate student_id primary key: {df.loc[idx, 'student_id']}"
            errors.append(err_row)

    # FK course_id
    if valid_courses_ids:
        fk_err = df[~df["course_id"].astype(str).isin(valid_courses_ids)].index
        for idx in fk_err:
            if valid_mask[idx]:
                valid_mask[idx] = False
                err_row = df.loc[idx].to_dict()
                err_row["error_reason"] = f"Foreign key violation: course_id '{df.loc[idx, 'course_id']}' does not exist"
                errors.append(err_row)

    # Date check
    for idx, row in df.iterrows():
        if valid_mask[idx] and not is_valid_date(row["enrollment_date"]):
            valid_mask[idx] = False
            err_row = row.to_dict()
            err_row["error_reason"] = f"Invalid enrollment_date format: {row['enrollment_date']}"
            errors.append(err_row)

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df


def validate_assessments(df: pd.DataFrame, valid_subjects_ids: set) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validates assessments dataset.
    Enforces percentage range 0-100% and the business rule:
    'Los porcentajes de las evaluaciones de cada materia suman 100%'
    """
    errors = []
    valid_mask = pd.Series(True, index=df.index)

    # 1. Mandatory columns null check
    for col in ["assessment_id", "subject_id", "assessment_name", "weight_percentage", "assessment_date"]:
        null_idx = df[df[col].isnull() | (df[col].astype(str).str.strip() == "")].index
        for idx in null_idx:
            if valid_mask[idx]:
                valid_mask[idx] = False
                err_row = df.loc[idx].to_dict()
                err_row["error_reason"] = f"Null value in mandatory column: {col}"
                errors.append(err_row)

    # 2. Duplicate PK
    dups = df[df["assessment_id"].duplicated(keep="first")].index
    for idx in dups:
        if valid_mask[idx]:
            valid_mask[idx] = False
            err_row = df.loc[idx].to_dict()
            err_row["error_reason"] = f"Duplicate assessment_id: {df.loc[idx, 'assessment_id']}"
            errors.append(err_row)

    # 3. FK subject_id
    fk_err = df[~df["subject_id"].astype(str).isin(valid_subjects_ids)].index
    for idx in fk_err:
        if valid_mask[idx]:
            valid_mask[idx] = False
            err_row = df.loc[idx].to_dict()
            err_row["error_reason"] = f"Foreign key violation: subject_id '{df.loc[idx, 'subject_id']}' does not exist"
            errors.append(err_row)

    # 4. Range check for weights (0.0 to 100.0)
    for idx, row in df.iterrows():
        if valid_mask[idx]:
            try:
                w = float(str(row["weight_percentage"]).replace(",", ".").strip())
                if w < 0.0 or w > 100.0:
                    valid_mask[idx] = False
                    err_row = row.to_dict()
                    err_row["error_reason"] = f"Weight percentage out of range [0-100%]: {w}"
                    errors.append(err_row)
            except (ValueError, TypeError):
                valid_mask[idx] = False
                err_row = row.to_dict()
                err_row["error_reason"] = f"Non-numeric weight percentage: {row['weight_percentage']}"
                errors.append(err_row)

    # 5. Date validation
    for idx, row in df.iterrows():
        if valid_mask[idx] and not is_valid_date(row["assessment_date"]):
            valid_mask[idx] = False
            err_row = row.to_dict()
            err_row["error_reason"] = f"Invalid assessment_date format: {row['assessment_date']}"
            errors.append(err_row)

    # 6. Critical Business Rule: Sum of weights for each subject must equal 100.0%
    interim_valid = df[valid_mask].copy()
    if not interim_valid.empty:
        # Convert weight_percentage to float for summation
        interim_valid["numeric_weight"] = interim_valid["weight_percentage"].astype(str).str.replace(",", ".").astype(float)
        subject_weight_sums = interim_valid.groupby("subject_id")["numeric_weight"].sum()

        invalid_sum_subjects = set(subject_weight_sums[abs(subject_weight_sums - 100.0) > 0.01].index)
        if invalid_sum_subjects:
            for idx in interim_valid[interim_valid["subject_id"].isin(invalid_sum_subjects)].index:
                valid_mask[idx] = False
                err_row = df.loc[idx].to_dict()
                actual_sum = round(float(subject_weight_sums.get(err_row["subject_id"], 0.0)), 2)
                err_row["error_reason"] = f"Subject assessment weights sum to {actual_sum}%, expected 100.0%"
                errors.append(err_row)

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df


def validate_grades(
    df: pd.DataFrame,
    valid_students_ids: set,
    valid_assessments_ids: set
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validates grades dataset:
    - Mandatory null checks
    - PK uniqueness
    - Text comma numeric errors
    - Scale bounds: 0.0 <= score <= 5.0
    - FK references to valid students and valid assessments
    - Valid submission dates and future date restrictions
    """
    errors = []
    valid_mask = pd.Series(True, index=df.index)

    # 1. Mandatory columns null check
    for col in ["grade_id", "assessment_id", "student_id", "score", "submission_date"]:
        null_idx = df[df[col].isnull() | (df[col].astype(str).str.strip().isin(["", "nan", "None"]))].index
        for idx in null_idx:
            if valid_mask[idx]:
                valid_mask[idx] = False
                err_row = df.loc[idx].to_dict()
                err_row["error_reason"] = f"Null value in mandatory column: {col}"
                errors.append(err_row)

    # 2. Duplicate PK
    dups = df[df["grade_id"].duplicated(keep="first")].index
    for idx in dups:
        if valid_mask[idx]:
            valid_mask[idx] = False
            err_row = df.loc[idx].to_dict()
            err_row["error_reason"] = f"Duplicate grade_id primary key: {df.loc[idx, 'grade_id']}"
            errors.append(err_row)

    # 3. Score validations
    for idx, row in df.iterrows():
        if valid_mask[idx]:
            s_val = row["score"]
            s_str = str(s_val).strip()

            # Catch explicit text comma numbers (e.g. '2,2', '4,0')
            if "," in s_str:
                valid_mask[idx] = False
                err_row = row.to_dict()
                err_row["error_reason"] = f"Invalid numeric format: score contains comma text '{s_str}'"
                errors.append(err_row)
                continue

            try:
                s_float = float(s_str)
                if s_float < 0.0 or s_float > 5.0:
                    valid_mask[idx] = False
                    err_row = row.to_dict()
                    err_row["error_reason"] = f"Grade score {s_float} out of allowed scale [0.0 - 5.0]"
                    errors.append(err_row)
                    continue
            except (ValueError, TypeError):
                valid_mask[idx] = False
                err_row = row.to_dict()
                err_row["error_reason"] = f"Invalid non-numeric grade score: '{s_val}'"
                errors.append(err_row)
                continue

    # 4. FK to valid students
    for idx, row in df.iterrows():
        if valid_mask[idx] and str(row["student_id"]).strip() not in valid_students_ids:
            valid_mask[idx] = False
            err_row = row.to_dict()
            err_row["error_reason"] = f"Foreign key violation: student_id '{row['student_id']}' does not exist"
            errors.append(err_row)

    # 5. FK to valid assessments
    for idx, row in df.iterrows():
        if valid_mask[idx] and str(row["assessment_id"]).strip() not in valid_assessments_ids:
            valid_mask[idx] = False
            err_row = row.to_dict()
            err_row["error_reason"] = f"Foreign key violation: assessment_id '{row['assessment_id']}' does not exist or was rejected"
            errors.append(err_row)

    # 6. Submission date format & future dates check
    for idx, row in df.iterrows():
        if valid_mask[idx]:
            sub_date = row["submission_date"]
            if not is_valid_date(sub_date):
                valid_mask[idx] = False
                err_row = row.to_dict()
                err_row["error_reason"] = f"Invalid submission_date format: {sub_date}"
                errors.append(err_row)
                continue

            parsed_dt = parse_date(sub_date)
            if parsed_dt and parsed_dt.year > 2026:
                valid_mask[idx] = False
                err_row = row.to_dict()
                err_row["error_reason"] = f"Future submission date not allowed: {sub_date}"
                errors.append(err_row)
                continue

    valid_df = df[valid_mask].copy()
    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=list(df.columns) + ["error_reason"])
    return valid_df, errors_df


def run_validation() -> Dict[str, Dict[str, int]]:
    """
    Executes full validation pipeline across all raw files.
    Writes valid records to data/processed/ and dirty records to data/errors/.
    Returns summary metrics.
    """
    logger.info("Starting raw data validation process...")
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ERRORS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    summary = {}

    for fname in EXPECTED_SCHEMAS.keys():
        fpath = RAW_DATA_DIR / fname
        if not fpath.exists():
            raise FileNotFoundError(f"Validation aborted: Required raw file not found: {fpath}")

    # 1. Courses
    raw_courses = pd.read_csv(RAW_DATA_DIR / "courses.csv", dtype=str)
    valid_courses, err_courses = validate_courses(raw_courses)
    valid_courses.to_csv(PROCESSED_DATA_DIR / "courses.csv", index=False, encoding="utf-8")
    err_courses.to_csv(ERRORS_DATA_DIR / "courses_errors.csv", index=False, encoding="utf-8")
    summary["courses"] = {"total": len(raw_courses), "valid": len(valid_courses), "errors": len(err_courses)}

    valid_courses_ids = set(valid_courses["course_id"].astype(str).str.strip())

    # 2. Subjects
    raw_subjects = pd.read_csv(RAW_DATA_DIR / "subjects.csv", dtype=str)
    valid_subjects, err_subjects = validate_subjects(raw_subjects, valid_courses_ids)
    valid_subjects.to_csv(PROCESSED_DATA_DIR / "subjects.csv", index=False, encoding="utf-8")
    err_subjects.to_csv(ERRORS_DATA_DIR / "subjects_errors.csv", index=False, encoding="utf-8")
    summary["subjects"] = {"total": len(raw_subjects), "valid": len(valid_subjects), "errors": len(err_subjects)}

    valid_subjects_ids = set(valid_subjects["subject_id"].astype(str).str.strip())

    # 3. Students
    raw_students = pd.read_csv(RAW_DATA_DIR / "students.csv", dtype=str)
    valid_students, err_students = validate_students(raw_students, valid_courses_ids)
    valid_students.to_csv(PROCESSED_DATA_DIR / "students.csv", index=False, encoding="utf-8")
    err_students.to_csv(ERRORS_DATA_DIR / "students_errors.csv", index=False, encoding="utf-8")
    summary["students"] = {"total": len(raw_students), "valid": len(valid_students), "errors": len(err_students)}

    valid_students_ids = set(valid_students["student_id"].astype(str).str.strip())

    # 4. Assessments
    raw_assessments = pd.read_csv(RAW_DATA_DIR / "assessments.csv", dtype=str)
    valid_assessments, err_assessments = validate_assessments(raw_assessments, valid_subjects_ids)
    valid_assessments.to_csv(PROCESSED_DATA_DIR / "assessments.csv", index=False, encoding="utf-8")
    err_assessments.to_csv(ERRORS_DATA_DIR / "assessments_errors.csv", index=False, encoding="utf-8")
    summary["assessments"] = {"total": len(raw_assessments), "valid": len(valid_assessments), "errors": len(err_assessments)}

    valid_assessments_ids = set(valid_assessments["assessment_id"].astype(str).str.strip())

    # 5. Grades
    raw_grades = pd.read_csv(RAW_DATA_DIR / "grades.csv", dtype=str)
    valid_grades, err_grades = validate_grades(raw_grades, valid_students_ids, valid_assessments_ids)
    valid_grades.to_csv(PROCESSED_DATA_DIR / "grades.csv", index=False, encoding="utf-8")
    err_grades.to_csv(ERRORS_DATA_DIR / "grades_errors.csv", index=False, encoding="utf-8")
    summary["grades"] = {"total": len(raw_grades), "valid": len(valid_grades), "errors": len(err_grades)}

    # Print summary report
    print("\n" + "=" * 75)
    print(f"{'RESUMEN DE VALIDACIÓN DE CALIDAD DE DATOS (DATA QUALITY AUDIT)':^75}")
    print("=" * 75)
    print(f"{'Entidad':<16} | {'Revisadas':<10} | {'Válidas':<10} | {'Inválidas':<10} | {'% Calidad':<10}")
    print("-" * 75)

    tot_rev = 0
    tot_val = 0
    tot_err = 0
    for entity, counts in summary.items():
        pct = (counts["valid"] / counts["total"] * 100) if counts["total"] > 0 else 0
        tot_rev += counts["total"]
        tot_val += counts["valid"]
        tot_err += counts["errors"]
        print(f"{entity:<16} | {counts['total']:<10} | {counts['valid']:<10} | {counts['errors']:<10} | {pct:>8.2f}%")

    print("-" * 75)
    tot_pct = (tot_val / tot_rev * 100) if tot_rev > 0 else 0
    print(f"{'TOTAL GENERAL':<16} | {tot_rev:<10} | {tot_val:<10} | {tot_err:<10} | {tot_pct:>8.2f}%")
    print("=" * 75)
    logger.info(f"Validation complete: {tot_rev} checked, {tot_val} valid, {tot_err} quarantined into data/errors/")

    return summary


if __name__ == "__main__":
    run_validation()
