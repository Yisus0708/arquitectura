-- ==============================================================================
-- Schema: SILVER
-- Población Idempotente desde STAGING hacia SILVER
-- ==============================================================================

-- 1. Courses
INSERT INTO silver.courses (course_id, course_name, grade_level, academic_year, updated_at)
SELECT
    course_id,
    course_name,
    grade_level,
    academic_year,
    CURRENT_TIMESTAMP
FROM staging.courses
ON CONFLICT (course_id) DO UPDATE SET
    course_name = EXCLUDED.course_name,
    grade_level = EXCLUDED.grade_level,
    academic_year = EXCLUDED.academic_year,
    updated_at = CURRENT_TIMESTAMP;


-- 2. Subjects
INSERT INTO silver.subjects (subject_id, subject_name, course_id, department, updated_at)
SELECT
    subject_id,
    subject_name,
    course_id,
    department,
    CURRENT_TIMESTAMP
FROM staging.subjects
ON CONFLICT (subject_id) DO UPDATE SET
    subject_name = EXCLUDED.subject_name,
    course_id = EXCLUDED.course_id,
    department = EXCLUDED.department,
    updated_at = CURRENT_TIMESTAMP;


-- 3. Students
INSERT INTO silver.students (student_id, first_name, last_name, email, course_id, enrollment_date, status, updated_at)
SELECT
    student_id,
    first_name,
    last_name,
    email,
    course_id,
    enrollment_date,
    status,
    CURRENT_TIMESTAMP
FROM staging.students
ON CONFLICT (student_id) DO UPDATE SET
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    email = EXCLUDED.email,
    course_id = EXCLUDED.course_id,
    enrollment_date = EXCLUDED.enrollment_date,
    status = EXCLUDED.status,
    updated_at = CURRENT_TIMESTAMP;


-- 4. Assessments
INSERT INTO silver.assessments (assessment_id, subject_id, assessment_name, assessment_type, weight_percentage, assessment_date, updated_at)
SELECT
    assessment_id,
    subject_id,
    assessment_name,
    assessment_type,
    weight_percentage,
    assessment_date,
    CURRENT_TIMESTAMP
FROM staging.assessments
ON CONFLICT (assessment_id) DO UPDATE SET
    subject_id = EXCLUDED.subject_id,
    assessment_name = EXCLUDED.assessment_name,
    assessment_type = EXCLUDED.assessment_type,
    weight_percentage = EXCLUDED.weight_percentage,
    assessment_date = EXCLUDED.assessment_date,
    updated_at = CURRENT_TIMESTAMP;


-- 5. Grades
INSERT INTO silver.grades (grade_id, assessment_id, student_id, score, submission_date, feedback, updated_at)
SELECT
    grade_id,
    assessment_id,
    student_id,
    score,
    submission_date,
    feedback,
    CURRENT_TIMESTAMP
FROM staging.grades
ON CONFLICT (grade_id) DO UPDATE SET
    assessment_id = EXCLUDED.assessment_id,
    student_id = EXCLUDED.student_id,
    score = EXCLUDED.score,
    submission_date = EXCLUDED.submission_date,
    feedback = EXCLUDED.feedback,
    updated_at = CURRENT_TIMESTAMP;
