"""
Data generation module.
Generates realistic, reproducible synthetic data for a school grading system.
Creates 5 raw CSV files in data/raw/ and an ingestion_metadata.json audit log.
Includes intentional anomalies (nulls, out-of-range scores, duplicate IDs, referential violations)
to test validation and error logging without corrupting raw immutability.
"""
import json
import random
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import RAW_DATA_DIR, RANDOM_SEED
from src.utils.hashing import calculate_file_sha256
from src.utils.logger import get_logger

logger = get_logger("generate_data")

FIRST_NAMES = [
    "Santiago", "Mateo", "Sebastián", "Alejandro", "Matías", "Nicolás", "Samuel",
    "Lucas", "Diego", "Benjamín", "Valentina", "Sofía", "Isabella", "Camila",
    "Mariana", "Luciana", "Daniela", "Gabriela", "Victoria", "Martina",
    "Andrés", "Felipe", "Carlos", "Esteban", "Julian", "Sara", "Laura", "Elena"
]

LAST_NAMES = [
    "Rodríguez", "Gómez", "González", "Martínez", "García", "López", "Hernández",
    "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Díaz", "Vargas", "Castro",
    "Morales", "Ortiz", "Silva", "Rojas", "Navarro", "Mendoza", "Castillo"
]

ASSESSMENT_TEMPLATES = [
    {"name": "Taller Práctico 1", "type": "Taller", "weight": 15.0, "day_offset": 20},
    {"name": "Parcial Teórico 1", "type": "Parcial", "weight": 30.0, "day_offset": 45},
    {"name": "Quiz Diagnóstico", "type": "Quiz", "weight": 15.0, "day_offset": 70},
    {"name": "Examen Final Semestral", "type": "Examen Final", "weight": 40.0, "day_offset": 105},
]

FEEDBACK_OPTIONS = [
    "Excelente dominio de los conceptos.",
    "Buen trabajo, repasar ejercicios prácticos.",
    "Aprobado, profundizar en temas teóricos.",
    "Desempeño bajo, requiere tutoría académica.",
    "Insuficiente, programar plan de mejoramiento.",
    "Muy buen análisis y resolución metodológica."
]


def generate_courses() -> pd.DataFrame:
    """Generates courses dimension data."""
    courses_data = [
        {"course_id": "CUR-10A", "course_name": "Grado 10-A", "grade_level": 10, "academic_year": 2026},
        {"course_id": "CUR-10B", "course_name": "Grado 10-B", "grade_level": 10, "academic_year": 2026},
        {"course_id": "CUR-11A", "course_name": "Grado 11-A", "grade_level": 11, "academic_year": 2026},
        {"course_id": "CUR-11B", "course_name": "Grado 11-B", "grade_level": 11, "academic_year": 2026},
    ]
    return pd.DataFrame(courses_data)


def generate_subjects(courses_df: pd.DataFrame) -> pd.DataFrame:
    """Generates subjects for each course."""
    base_subjects = [
        ("MAT", "Matemáticas", "Ciencias Exactas"),
        ("FIS", "Física", "Ciencias Naturales"),
        ("QUI", "Química", "Ciencias Naturales"),
        ("ESP", "Español y Literatura", "Humanidades"),
        ("ING", "Inglés", "Idiomas"),
    ]
    rows = []
    for _, course in courses_df.iterrows():
        c_id = course["course_id"]
        level = course["grade_level"]
        section = c_id[-1]
        for code, name, dept in base_subjects:
            subj_id = f"SUB-{code}-{level}{section}"
            rows.append({
                "subject_id": subj_id,
                "subject_name": f"{name} {level}°",
                "course_id": c_id,
                "department": dept
            })
    return pd.DataFrame(rows)


def generate_students(courses_df: pd.DataFrame, num_students: int = 80) -> pd.DataFrame:
    """Generates students distributed across courses with controlled dirty records."""
    course_ids = courses_df["course_id"].tolist()
    students = []

    for i in range(1, num_students + 1):
        c_id = course_ids[(i - 1) % len(course_ids)]
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        email = f"{fname.lower()}.{lname.lower()}{i}@colegio.edu.co".replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        students.append({
            "student_id": f"EST-{i:03d}",
            "first_name": fname,
            "last_name": lname,
            "email": email,
            "course_id": c_id,
            "enrollment_date": "2026-01-15",
            "status": "ACTIVO"
        })

    # Intentional dirty records for students
    # 1. Duplicate Primary Key
    students.append({
        "student_id": "EST-005",  # Duplicate ID
        "first_name": "Duplicado",
        "last_name": "Test",
        "email": "duplicado.test@colegio.edu.co",
        "course_id": "CUR-10A",
        "enrollment_date": "2026-01-15",
        "status": "ACTIVO"
    })
    # 2. Null mandatory field (last_name)
    students.append({
        "student_id": "EST-081",
        "first_name": "SinApellido",
        "last_name": None,
        "email": "sin.apellido@colegio.edu.co",
        "course_id": "CUR-10B",
        "enrollment_date": "2026-01-15",
        "status": "ACTIVO"
    })
    # 3. Non-existent course_id
    students.append({
        "student_id": "EST-082",
        "first_name": "CursoInvalido",
        "last_name": "Huérfano",
        "email": "invalido@colegio.edu.co",
        "course_id": "CUR-99Z",  # Non-existent FK
        "enrollment_date": "2026-01-15",
        "status": "ACTIVO"
    })

    return pd.DataFrame(students)


def generate_assessments(subjects_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates assessments per subject.
    Valid subjects sum exactly to 100.0%.
    Includes controlled anomalies to test validation of business rules.
    """
    assessments = []
    subject_ids = subjects_df["subject_id"].tolist()

    for s_idx, s_id in enumerate(subject_ids):
        # We will make the last subject intentionally have bad assessment weights (sum != 100%)
        # to test the rule: 'los porcentajes de las evaluaciones de cada materia suman 100%'
        is_bad_subject = (s_idx == len(subject_ids) - 1)

        for a_idx, tmpl in enumerate(ASSESSMENT_TEMPLATES, start=1):
            eval_id = f"EVAL-{s_id}-{a_idx:02d}"
            weight = tmpl["weight"]
            if is_bad_subject and a_idx == 4:
                # Intentionally make it 55.0% so the sum is 115.0%
                weight = 55.0

            assessments.append({
                "assessment_id": eval_id,
                "subject_id": s_id,
                "assessment_name": tmpl["name"],
                "assessment_type": tmpl["type"],
                "weight_percentage": weight,
                "assessment_date": f"2026-0{2 + (a_idx - 1)}:02d-15" if a_idx <= 4 else "2026-05-20"
            })

    # Standardize dates for templates
    for a in assessments:
        if a["assessment_name"] == "Taller Práctico 1":
            a["assessment_date"] = "2026-02-20"
        elif a["assessment_name"] == "Parcial Teórico 1":
            a["assessment_date"] = "2026-03-25"
        elif a["assessment_name"] == "Quiz Diagnóstico":
            a["assessment_date"] = "2026-04-18"
        elif a["assessment_name"] == "Examen Final Semestral":
            a["assessment_date"] = "2026-05-28"

    # Intentional dirty assessment records
    # 1. Weight out of range (> 100%)
    assessments.append({
        "assessment_id": "EVAL-ERR-01",
        "subject_id": subject_ids[0],
        "assessment_name": "Evaluación Peso Excesivo",
        "assessment_type": "Parcial",
        "weight_percentage": 150.0,  # Invalid: > 100%
        "assessment_date": "2026-03-01"
    })
    # 2. Negative weight
    assessments.append({
        "assessment_id": "EVAL-ERR-02",
        "subject_id": subject_ids[0],
        "assessment_name": "Evaluación Peso Negativo",
        "assessment_type": "Quiz",
        "weight_percentage": -15.0,  # Invalid: < 0%
        "assessment_date": "2026-03-05"
    })
    # 3. Missing mandatory field (null assessment_name)
    assessments.append({
        "assessment_id": "EVAL-ERR-03",
        "subject_id": subject_ids[1],
        "assessment_name": None,  # Invalid: NULL name
        "assessment_type": "Taller",
        "weight_percentage": 10.0,
        "assessment_date": "2026-03-10"
    })

    return pd.DataFrame(assessments)


def generate_grades(
    students_df: pd.DataFrame,
    subjects_df: pd.DataFrame,
    assessments_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Generates grades for each student and their enrolled assessments.
    Grading scale: 0.0 to 5.0 (passing >= 3.0).
    Includes intentional anomalies (out of range, duplicates, non-existent FK, nulls).
    """
    grades = []
    grade_counter = 1

    # Map course_id -> list of students (only valid students from base list)
    valid_students = students_df[
        students_df["student_id"].str.startswith("EST-") &
        (students_df["student_id"] <= "EST-080")
    ]
    course_to_students = {}
    for _, st in valid_students.iterrows():
        c_id = st["course_id"]
        course_to_students.setdefault(c_id, []).append(st["student_id"])

    # Map course_id -> list of subjects
    course_to_subjects = {}
    for _, sub in subjects_df.iterrows():
        c_id = sub["course_id"]
        course_to_subjects.setdefault(c_id, []).append(sub["subject_id"])

    # Map subject_id -> list of assessments (exclude error evaluations)
    subj_to_assessments = {}
    valid_evals = assessments_df[~assessments_df["assessment_id"].str.startswith("EVAL-ERR")]
    for _, ev in valid_evals.iterrows():
        s_id = ev["subject_id"]
        subj_to_assessments.setdefault(s_id, []).append(ev["assessment_id"])

    for course_id, student_list in course_to_students.items():
        subject_list = course_to_subjects.get(course_id, [])
        for st_id in student_list:
            # Student inherent proficiency (mean score between 2.5 and 4.7)
            student_ability = random.gauss(3.5, 0.6)
            for s_id in subject_list:
                eval_ids = subj_to_assessments.get(s_id, [])
                for ev_id in eval_ids:
                    # Realistic grade generation bounded between 1.0 and 5.0
                    raw_score = random.gauss(student_ability, 0.5)
                    score = max(0.5, min(5.0, round(raw_score, 1)))

                    feedback = random.choice(FEEDBACK_OPTIONS)
                    submission_date = "2026-03-30"

                    grades.append({
                        "grade_id": f"GRD-{grade_counter:05d}",
                        "assessment_id": ev_id,
                        "student_id": st_id,
                        "score": score,
                        "submission_date": submission_date,
                        "feedback": feedback
                    })
                    grade_counter += 1

    # Intentional dirty grade records
    # 1. Score > 5.0
    grades.append({
        "grade_id": f"GRD-{grade_counter:05d}",
        "assessment_id": "EVAL-SUB-MAT-10A-01",
        "student_id": "EST-001",
        "score": 6.8,  # Invalid: > 5.0
        "submission_date": "2026-03-30",
        "feedback": "Nota errónea fuera de escala."
    })
    grade_counter += 1

    # 2. Score < 0.0
    grades.append({
        "grade_id": f"GRD-{grade_counter:05d}",
        "assessment_id": "EVAL-SUB-MAT-10A-02",
        "student_id": "EST-002",
        "score": -1.5,  # Invalid: < 0.0
        "submission_date": "2026-03-30",
        "feedback": "Nota negativa inválida."
    })
    grade_counter += 1

    # 3. Null score in mandatory field
    grades.append({
        "grade_id": f"GRD-{grade_counter:05d}",
        "assessment_id": "EVAL-SUB-FIS-10A-01",
        "student_id": "EST-003",
        "score": None,  # Invalid: NULL
        "submission_date": "2026-03-30",
        "feedback": "Falta registro de nota."
    })
    grade_counter += 1

    # 4. Duplicate Primary Key
    grades.append({
        "grade_id": "GRD-00001",  # Duplicate PK
        "assessment_id": "EVAL-SUB-MAT-10A-01",
        "student_id": "EST-001",
        "score": 4.0,
        "submission_date": "2026-03-30",
        "feedback": "Registro duplicado intencional."
    })

    # 5. Non-existent student_id (Referential integrity breach)
    grades.append({
        "grade_id": f"GRD-{grade_counter:05d}",
        "assessment_id": "EVAL-SUB-MAT-10A-01",
        "student_id": "EST-999",  # Does not exist
        "score": 3.8,
        "submission_date": "2026-03-30",
        "feedback": "Estudiante inexistente."
    })
    grade_counter += 1

    # 6. Non-existent assessment_id (Referential integrity breach)
    grades.append({
        "grade_id": f"GRD-{grade_counter:05d}",
        "assessment_id": "EVAL-NONEXISTENT-99",  # Does not exist
        "student_id": "EST-001",
        "score": 4.5,
        "submission_date": "2026-03-30",
        "feedback": "Evaluación inexistente."
    })
    grade_counter += 1

    # 7. Invalid date format
    grades.append({
        "grade_id": f"GRD-{grade_counter:05d}",
        "assessment_id": "EVAL-SUB-MAT-10A-01",
        "student_id": "EST-004",
        "score": 3.5,
        "submission_date": "2026-99-99",  # Invalid Date
        "feedback": "Fecha corrupta."
    })

    return pd.DataFrame(grades)


def main():
    logger.info("Initializing synthetic data generation with fixed seed...")
    # Set seeds for reproducibility
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Generate datasets
    logger.info("Generating courses...")
    courses_df = generate_courses()

    logger.info("Generating subjects...")
    subjects_df = generate_subjects(courses_df)

    logger.info("Generating students...")
    students_df = generate_students(courses_df, num_students=80)

    logger.info("Generating assessments...")
    assessments_df = generate_assessments(subjects_df)

    logger.info("Generating grades...")
    grades_df = generate_grades(students_df, subjects_df, assessments_df)

    datasets = {
        "courses.csv": courses_df,
        "subjects.csv": subjects_df,
        "students.csv": students_df,
        "assessments.csv": assessments_df,
        "grades.csv": grades_df,
    }

    metadata: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "random_seed": RANDOM_SEED,
        "scale": "0.0 - 5.0 (passing >= 3.0)",
        "files": {}
    }

    for filename, df in datasets.items():
        file_path = RAW_DATA_DIR / filename
        df.to_csv(file_path, index=False, encoding="utf-8")
        row_count = len(df)
        file_size = file_path.stat().st_size
        checksum = calculate_file_sha256(file_path)

        metadata["files"][filename] = {
            "path": str(file_path.relative_to(RAW_DATA_DIR.parent.parent)),
            "row_count": row_count,
            "columns": list(df.columns),
            "size_bytes": file_size,
            "sha256": checksum
        }
        logger.info(f"Generated {filename}: {row_count} rows, {file_size} bytes, sha256={checksum[:12]}...")

    # Write ingestion metadata
    metadata_path = RAW_DATA_DIR / "ingestion_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    logger.info(f"Ingestion metadata saved to {metadata_path.name}")
    logger.info("Raw data generation complete. Raw data remains immutable.")


if __name__ == "__main__":
    main()
