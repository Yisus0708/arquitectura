-- ==============================================================================
-- Schema: SILVER
-- Población Idempotente desde STAGING hacia SILVER: reemplazo completo por carga
-- ==============================================================================

TRUNCATE TABLE silver.grades, silver.assessments, silver.attendance, silver.students, silver.subjects, silver.courses, silver.periods CASCADE;

-- 1. Courses
INSERT INTO silver.courses (course_id, course_name, grade_level, academic_year, extra, updated_at)
SELECT
    course_id,
    course_name,
    grade_level,
    academic_year,
    extra,
    CURRENT_TIMESTAMP
FROM staging.courses
ON CONFLICT (course_id) DO UPDATE SET
    course_name = EXCLUDED.course_name,
    grade_level = EXCLUDED.grade_level,
    academic_year = EXCLUDED.academic_year,
    extra = EXCLUDED.extra,
    updated_at = CURRENT_TIMESTAMP;


-- 2. Subjects
INSERT INTO silver.subjects (subject_id, subject_name, course_id, department, extra, updated_at)
SELECT
    subject_id,
    subject_name,
    course_id,
    department,
    extra,
    CURRENT_TIMESTAMP
FROM staging.subjects
ON CONFLICT (subject_id) DO UPDATE SET
    subject_name = EXCLUDED.subject_name,
    course_id = EXCLUDED.course_id,
    department = EXCLUDED.department,
    extra = EXCLUDED.extra,
    updated_at = CURRENT_TIMESTAMP;


-- 3. Periods
INSERT INTO silver.periods (period_id, period_name, start_date, end_date, weight, extra, updated_at)
SELECT
    period_id,
    period_name,
    start_date,
    end_date,
    weight,
    extra,
    CURRENT_TIMESTAMP
FROM staging.periods
ON CONFLICT (period_id) DO UPDATE SET
    period_name = EXCLUDED.period_name,
    start_date = EXCLUDED.start_date,
    end_date = EXCLUDED.end_date,
    weight = EXCLUDED.weight,
    extra = EXCLUDED.extra,
    updated_at = CURRENT_TIMESTAMP;


-- 4. Students
INSERT INTO silver.students (
    student_id, document_number, first_name, last_name, gender,
    birth_date, email, course_id, enrollment_date, status, extra, updated_at
)
SELECT
    student_id,
    document_number,
    first_name,
    last_name,
    gender,
    birth_date,
    email,
    course_id,
    enrollment_date,
    status,
    extra,
    CURRENT_TIMESTAMP
FROM staging.students
ON CONFLICT (student_id) DO UPDATE SET
    document_number = EXCLUDED.document_number,
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    gender = EXCLUDED.gender,
    birth_date = EXCLUDED.birth_date,
    email = EXCLUDED.email,
    course_id = EXCLUDED.course_id,
    enrollment_date = EXCLUDED.enrollment_date,
    status = EXCLUDED.status,
    extra = EXCLUDED.extra,
    updated_at = CURRENT_TIMESTAMP;


-- 5. Assessments
INSERT INTO silver.assessments (
    assessment_id, course_id, subject_id, period_id,
    assessment_name, assessment_type, weight_percentage, assessment_date, extra, updated_at
)
SELECT
    assessment_id,
    course_id,
    subject_id,
    period_id,
    assessment_name,
    assessment_type,
    weight_percentage,
    assessment_date,
    extra,
    CURRENT_TIMESTAMP
FROM staging.assessments
ON CONFLICT (assessment_id) DO UPDATE SET
    course_id = EXCLUDED.course_id,
    subject_id = EXCLUDED.subject_id,
    period_id = EXCLUDED.period_id,
    assessment_name = EXCLUDED.assessment_name,
    assessment_type = EXCLUDED.assessment_type,
    weight_percentage = EXCLUDED.weight_percentage,
    assessment_date = EXCLUDED.assessment_date,
    extra = EXCLUDED.extra,
    updated_at = CURRENT_TIMESTAMP;


-- 6. Grades
INSERT INTO silver.grades (grade_id, assessment_id, student_id, score, submission_date, feedback, extra, updated_at)
SELECT
    grade_id,
    assessment_id,
    student_id,
    score,
    submission_date,
    feedback,
    extra,
    CURRENT_TIMESTAMP
FROM staging.grades
ON CONFLICT (grade_id) DO UPDATE SET
    assessment_id = EXCLUDED.assessment_id,
    student_id = EXCLUDED.student_id,
    score = EXCLUDED.score,
    submission_date = EXCLUDED.submission_date,
    feedback = EXCLUDED.feedback,
    extra = EXCLUDED.extra,
    updated_at = CURRENT_TIMESTAMP;


-- 7. Attendance
INSERT INTO silver.attendance (attendance_id, student_id, course_id, period_id, total_classes, absences, extra, updated_at)
SELECT
    attendance_id,
    student_id,
    course_id,
    period_id,
    total_classes,
    absences,
    extra,
    CURRENT_TIMESTAMP
FROM staging.attendance
ON CONFLICT (attendance_id) DO UPDATE SET
    student_id = EXCLUDED.student_id,
    course_id = EXCLUDED.course_id,
    period_id = EXCLUDED.period_id,
    total_classes = EXCLUDED.total_classes,
    absences = EXCLUDED.absences,
    extra = EXCLUDED.extra,
    updated_at = CURRENT_TIMESTAMP;
