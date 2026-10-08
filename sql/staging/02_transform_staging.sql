-- ==============================================================================
-- Schema: STAGING
-- Transformaciones y Carga desde RAW hacia STAGING
-- Idempotente: Truncate + Rebuild con tipado, limpieza de cadenas y filtrado
-- ==============================================================================

-- 1. Courses
TRUNCATE TABLE staging.courses;

WITH ranked_courses AS (
    SELECT
        TRIM(course_id) AS course_id,
        TRIM(course_name) AS course_name,
        CASE WHEN TRIM(grade_level) ~ '^\d+$' THEN CAST(TRIM(grade_level) AS INT) ELSE NULL END AS grade_level,
        CASE WHEN TRIM(academic_year) ~ '^\d+$' THEN CAST(TRIM(academic_year) AS INT) ELSE NULL END AS academic_year,
        CASE WHEN extra IS NOT NULL AND TRIM(extra) <> '' THEN extra::JSONB ELSE NULL END AS extra,
        ROW_NUMBER() OVER(PARTITION BY TRIM(course_id) ORDER BY _loaded_at ASC) AS rn
    FROM raw.courses
    WHERE course_id IS NOT NULL AND TRIM(course_id) <> ''
)
INSERT INTO staging.courses (course_id, course_name, grade_level, academic_year, extra)
SELECT course_id, course_name, grade_level, academic_year, extra
FROM ranked_courses
WHERE rn = 1;


-- 2. Subjects
TRUNCATE TABLE staging.subjects;

WITH ranked_subjects AS (
    SELECT
        TRIM(s.subject_id) AS subject_id,
        TRIM(s.subject_name) AS subject_name,
        NULLIF(TRIM(s.course_id), '') AS course_id,
        NULLIF(TRIM(s.department), '') AS department,
        CASE WHEN s.extra IS NOT NULL AND TRIM(s.extra) <> '' THEN s.extra::JSONB ELSE NULL END AS extra,
        ROW_NUMBER() OVER(PARTITION BY TRIM(s.subject_id) ORDER BY s._loaded_at ASC) AS rn
    FROM raw.subjects s
    WHERE s.subject_id IS NOT NULL AND TRIM(s.subject_id) <> ''
)
INSERT INTO staging.subjects (subject_id, subject_name, course_id, department, extra)
SELECT subject_id, subject_name, course_id, department, extra
FROM ranked_subjects
WHERE rn = 1;


-- 3. Students
TRUNCATE TABLE staging.students;

WITH clean_students AS (
    SELECT
        TRIM(s.student_id) AS student_id,
        NULLIF(TRIM(s.document_number), '') AS document_number,
        TRIM(s.first_name) AS first_name,
        TRIM(s.last_name) AS last_name,
        CASE
            WHEN LOWER(TRIM(s.gender)) IN ('m', 'masculino', 'male', 'hombre') THEN 'M'
            WHEN LOWER(TRIM(s.gender)) IN ('f', 'femenino', 'female', 'mujer') THEN 'F'
            ELSE NULLIF(TRIM(s.gender), '')
        END AS gender,
        CASE
            WHEN s.birth_date ~ '^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$' THEN CAST(TRIM(s.birth_date) AS DATE)
            ELSE NULL
        END AS birth_date,
        NULLIF(LOWER(TRIM(s.email)), '') AS email,
        NULLIF(TRIM(s.course_id), '') AS course_id,
        CASE
            WHEN s.enrollment_date ~ '^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$' THEN CAST(TRIM(s.enrollment_date) AS DATE)
            ELSE NULL
        END AS enrollment_date,
        COALESCE(NULLIF(UPPER(TRIM(s.status)), ''), 'ACTIVO') AS status,
        CASE WHEN s.extra IS NOT NULL AND TRIM(s.extra) <> '' THEN s.extra::JSONB ELSE NULL END AS extra,
        ROW_NUMBER() OVER(PARTITION BY TRIM(s.student_id) ORDER BY s._loaded_at ASC) AS rn
    FROM raw.students s
    WHERE s.student_id IS NOT NULL AND TRIM(s.student_id) <> ''
)
INSERT INTO staging.students (
    student_id, document_number, first_name, last_name, gender,
    birth_date, email, course_id, enrollment_date, status, extra
)
SELECT
    student_id, document_number, first_name, last_name, gender,
    birth_date, email, course_id, enrollment_date, status, extra
FROM clean_students
WHERE rn = 1;


-- 4. Assessments
TRUNCATE TABLE staging.assessments;

WITH clean_assessments AS (
    SELECT
        TRIM(a.assessment_id) AS assessment_id,
        NULLIF(TRIM(a.course_id), '') AS course_id,
        NULLIF(TRIM(a.subject_id), '') AS subject_id,
        NULLIF(TRIM(a.period_id), '') AS period_id,
        TRIM(a.assessment_name) AS assessment_name,
        NULLIF(TRIM(a.assessment_type), '') AS assessment_type,
        CAST(REPLACE(TRIM(a.weight_percentage), ',', '.') AS NUMERIC(5,2)) AS weight_percentage,
        CASE
            WHEN a.assessment_date ~ '^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$' THEN CAST(TRIM(a.assessment_date) AS DATE)
            ELSE NULL
        END AS assessment_date,
        CASE WHEN a.extra IS NOT NULL AND TRIM(a.extra) <> '' THEN a.extra::JSONB ELSE NULL END AS extra,
        ROW_NUMBER() OVER(PARTITION BY TRIM(a.assessment_id) ORDER BY a._loaded_at ASC) AS rn
    FROM raw.assessments a
    WHERE a.assessment_id IS NOT NULL AND TRIM(a.assessment_id) <> ''
      AND a.assessment_name IS NOT NULL AND TRIM(a.assessment_name) <> ''
      AND a.weight_percentage ~ '^-?\d+([.,]\d+)?$'
      AND CAST(REPLACE(TRIM(a.weight_percentage), ',', '.') AS NUMERIC(5,2)) BETWEEN 0.0 AND 100.0
),
deduped_assessments AS (
    SELECT * FROM clean_assessments WHERE rn = 1
),
group_weights AS (
    SELECT
        COALESCE(subject_id, '') AS subj,
        COALESCE(period_id, '') AS per,
        SUM(weight_percentage) AS total_weight
    FROM deduped_assessments
    GROUP BY COALESCE(subject_id, ''), COALESCE(period_id, '')
)
INSERT INTO staging.assessments (
    assessment_id, course_id, subject_id, period_id,
    assessment_name, assessment_type, weight_percentage, assessment_date, extra
)
SELECT
    da.assessment_id,
    da.course_id,
    da.subject_id,
    da.period_id,
    da.assessment_name,
    da.assessment_type,
    da.weight_percentage,
    da.assessment_date,
    da.extra
FROM deduped_assessments da
INNER JOIN group_weights gw
    ON COALESCE(da.subject_id, '') = gw.subj
   AND COALESCE(da.period_id, '') = gw.per
-- Solo descartar grupos cuyos pesos no sumen 100% (+/- 1%)
WHERE ABS(gw.total_weight - 100.0) <= 1.0;


-- 5. Grades
TRUNCATE TABLE staging.grades;

WITH clean_grades AS (
    SELECT
        TRIM(g.grade_id) AS grade_id,
        TRIM(g.assessment_id) AS assessment_id,
        TRIM(g.student_id) AS student_id,
        CAST(REPLACE(TRIM(g.score), ',', '.') AS NUMERIC(5,2)) AS score,
        CASE
            WHEN g.submission_date ~ '^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$' THEN CAST(TRIM(g.submission_date) AS DATE)
            ELSE NULL
        END AS submission_date,
        NULLIF(TRIM(g.feedback), '') AS feedback,
        CASE WHEN g.extra IS NOT NULL AND TRIM(g.extra) <> '' THEN g.extra::JSONB ELSE NULL END AS extra,
        ROW_NUMBER() OVER(PARTITION BY TRIM(g.assessment_id), TRIM(g.student_id) ORDER BY g.grade_id ASC, g._loaded_at ASC) AS rn
    FROM raw.grades g
    INNER JOIN staging.students st ON TRIM(g.student_id) = st.student_id
    INNER JOIN staging.assessments ev ON TRIM(g.assessment_id) = ev.assessment_id
    WHERE g.grade_id IS NOT NULL AND TRIM(g.grade_id) <> ''
      AND g.score ~ '^-?\d+([.,]\d+)?$'
      AND CAST(REPLACE(TRIM(g.score), ',', '.') AS NUMERIC(5,2)) BETWEEN 0.0 AND 5.0
      AND (g.submission_date IS NULL OR TRIM(g.submission_date) = '' OR (
          g.submission_date ~ '^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'
          AND CAST(TRIM(g.submission_date) AS DATE) <= CURRENT_DATE
      ))
)
INSERT INTO staging.grades (grade_id, assessment_id, student_id, score, submission_date, feedback, extra)
SELECT grade_id, assessment_id, student_id, score, submission_date, feedback, extra
FROM clean_grades
WHERE rn = 1;


-- 6. Optional: Periods
TRUNCATE TABLE staging.periods;
INSERT INTO staging.periods (period_id, period_name, start_date, end_date, weight, extra)
SELECT DISTINCT
    TRIM(period_id),
    TRIM(period_name),
    CASE WHEN start_date ~ '^\d{4}-\d{2}-\d{2}' THEN CAST(TRIM(start_date) AS DATE) ELSE NULL END,
    CASE WHEN end_date ~ '^\d{4}-\d{2}-\d{2}' THEN CAST(TRIM(end_date) AS DATE) ELSE NULL END,
    CASE WHEN weight ~ '^-?\d+([.,]\d+)?$' THEN CAST(REPLACE(TRIM(weight), ',', '.') AS NUMERIC(5,2)) ELSE NULL END,
    CASE WHEN extra IS NOT NULL AND TRIM(extra) <> '' THEN extra::JSONB ELSE NULL END
FROM raw.periods
WHERE period_id IS NOT NULL AND TRIM(period_id) <> '';


-- 7. Optional: Attendance
TRUNCATE TABLE staging.attendance;
INSERT INTO staging.attendance (attendance_id, student_id, course_id, period_id, total_classes, absences, extra)
SELECT
    TRIM(attendance_id),
    TRIM(student_id),
    NULLIF(TRIM(course_id), ''),
    NULLIF(TRIM(period_id), ''),
    CASE WHEN total_classes ~ '^\d+$' THEN CAST(TRIM(total_classes) AS INT) ELSE NULL END,
    CASE WHEN absences ~ '^\d+$' THEN CAST(TRIM(absences) AS INT) ELSE NULL END,
    CASE WHEN extra IS NOT NULL AND TRIM(extra) <> '' THEN extra::JSONB ELSE NULL END
FROM raw.attendance
WHERE student_id IS NOT NULL AND TRIM(student_id) <> ''
  AND CAST(TRIM(absences) AS INT) >= 0
  AND CAST(TRIM(absences) AS INT) <= CAST(TRIM(total_classes) AS INT);
