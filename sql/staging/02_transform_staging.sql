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
        CAST(TRIM(grade_level) AS INT) AS grade_level,
        CAST(TRIM(academic_year) AS INT) AS academic_year,
        ROW_NUMBER() OVER(PARTITION BY TRIM(course_id) ORDER BY _loaded_at ASC) AS rn
    FROM raw.courses
    WHERE course_id IS NOT NULL
      AND TRIM(course_id) <> ''
      AND grade_level ~ '^\d+$'
      AND academic_year ~ '^\d+$'
)
INSERT INTO staging.courses (course_id, course_name, grade_level, academic_year)
SELECT course_id, course_name, grade_level, academic_year
FROM ranked_courses
WHERE rn = 1;


-- 2. Subjects
TRUNCATE TABLE staging.subjects;

WITH ranked_subjects AS (
    SELECT
        TRIM(s.subject_id) AS subject_id,
        TRIM(s.subject_name) AS subject_name,
        TRIM(s.course_id) AS course_id,
        TRIM(s.department) AS department,
        ROW_NUMBER() OVER(PARTITION BY TRIM(s.subject_id) ORDER BY s._loaded_at ASC) AS rn
    FROM raw.subjects s
    INNER JOIN staging.courses c ON TRIM(s.course_id) = c.course_id
    WHERE s.subject_id IS NOT NULL
      AND TRIM(s.subject_id) <> ''
      AND s.subject_name IS NOT NULL
)
INSERT INTO staging.subjects (subject_id, subject_name, course_id, department)
SELECT subject_id, subject_name, course_id, department
FROM ranked_subjects
WHERE rn = 1;


-- 3. Students
TRUNCATE TABLE staging.students;

WITH clean_students AS (
    SELECT
        TRIM(s.student_id) AS student_id,
        TRIM(s.first_name) AS first_name,
        TRIM(s.last_name) AS last_name,
        LOWER(TRIM(s.email)) AS email,
        TRIM(s.course_id) AS course_id,
        CAST(TRIM(s.enrollment_date) AS DATE) AS enrollment_date,
        UPPER(TRIM(COALESCE(s.status, 'ACTIVO'))) AS status,
        ROW_NUMBER() OVER(PARTITION BY TRIM(s.student_id) ORDER BY s._loaded_at ASC) AS rn
    FROM raw.students s
    INNER JOIN staging.courses c ON TRIM(s.course_id) = c.course_id
    WHERE s.student_id IS NOT NULL
      AND TRIM(s.student_id) <> ''
      AND s.last_name IS NOT NULL
      AND TRIM(s.last_name) <> ''
      AND s.enrollment_date ~ '^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'
)
INSERT INTO staging.students (student_id, first_name, last_name, email, course_id, enrollment_date, status)
SELECT student_id, first_name, last_name, email, course_id, enrollment_date, status
FROM clean_students
WHERE rn = 1;


-- 4. Assessments
TRUNCATE TABLE staging.assessments;

WITH clean_assessments AS (
    SELECT
        TRIM(a.assessment_id) AS assessment_id,
        TRIM(a.subject_id) AS subject_id,
        TRIM(a.assessment_name) AS assessment_name,
        TRIM(a.assessment_type) AS assessment_type,
        CAST(TRIM(a.weight_percentage) AS NUMERIC(5,2)) AS weight_percentage,
        CAST(TRIM(a.assessment_date) AS DATE) AS assessment_date,
        ROW_NUMBER() OVER(PARTITION BY TRIM(a.assessment_id) ORDER BY a._loaded_at ASC) AS rn
    FROM raw.assessments a
    INNER JOIN staging.subjects sub ON TRIM(a.subject_id) = sub.subject_id
    WHERE a.assessment_id IS NOT NULL
      AND TRIM(a.assessment_id) <> ''
      AND a.assessment_name IS NOT NULL
      AND TRIM(a.assessment_name) <> ''
      AND a.weight_percentage ~ '^-?\d+(\.\d+)?$'
      AND CAST(TRIM(a.weight_percentage) AS NUMERIC(5,2)) BETWEEN 0.0 AND 100.0
      AND a.assessment_date ~ '^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'
),
deduped_assessments AS (
    SELECT * FROM clean_assessments WHERE rn = 1
),
subject_weights AS (
    SELECT subject_id, SUM(weight_percentage) AS total_weight
    FROM deduped_assessments
    GROUP BY subject_id
)
INSERT INTO staging.assessments (assessment_id, subject_id, assessment_name, assessment_type, weight_percentage, assessment_date)
SELECT
    da.assessment_id,
    da.subject_id,
    da.assessment_name,
    da.assessment_type,
    da.weight_percentage,
    da.assessment_date
FROM deduped_assessments da
INNER JOIN subject_weights sw ON da.subject_id = sw.subject_id
-- Regla de negocio: la suma de porcentajes de las evaluaciones de la materia debe ser exactamente 100%
WHERE ABS(sw.total_weight - 100.0) <= 0.01;


-- 5. Grades
TRUNCATE TABLE staging.grades;

WITH clean_grades AS (
    SELECT
        TRIM(g.grade_id) AS grade_id,
        TRIM(g.assessment_id) AS assessment_id,
        TRIM(g.student_id) AS student_id,
        CAST(TRIM(g.score) AS NUMERIC(3,1)) AS score,
        CAST(TRIM(g.submission_date) AS DATE) AS submission_date,
        TRIM(g.feedback) AS feedback,
        ROW_NUMBER() OVER(PARTITION BY TRIM(g.grade_id) ORDER BY g._loaded_at ASC) AS rn
    FROM raw.grades g
    INNER JOIN staging.students st ON TRIM(g.student_id) = st.student_id
    INNER JOIN staging.assessments ev ON TRIM(g.assessment_id) = ev.assessment_id
    WHERE g.grade_id IS NOT NULL
      AND TRIM(g.grade_id) <> ''
      AND g.score ~ '^-?\d+(\.\d+)?$'
      AND CAST(TRIM(g.score) AS NUMERIC(3,1)) BETWEEN 0.0 AND 5.0
      AND g.submission_date ~ '^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'
)
INSERT INTO staging.grades (grade_id, assessment_id, student_id, score, submission_date, feedback)
SELECT grade_id, assessment_id, student_id, score, submission_date, feedback
FROM clean_grades
WHERE rn = 1;
