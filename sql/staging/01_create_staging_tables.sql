-- ==============================================================================
-- Schema: STAGING
-- Tablas intermedias tipadas, normalizadas (snake_case), limpias y con columna extra JSONB
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS staging;

DROP TABLE IF EXISTS staging.courses CASCADE;
CREATE TABLE staging.courses (
    course_id VARCHAR(50),
    course_name VARCHAR(100),
    grade_level INT,
    academic_year INT,
    extra JSONB,
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging.subjects CASCADE;
CREATE TABLE staging.subjects (
    subject_id VARCHAR(50),
    subject_name VARCHAR(100),
    course_id VARCHAR(50),
    department VARCHAR(100),
    extra JSONB,
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging.students CASCADE;
CREATE TABLE staging.students (
    student_id VARCHAR(50),
    document_number VARCHAR(50),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    gender VARCHAR(20),
    birth_date DATE,
    email VARCHAR(150),
    course_id VARCHAR(50),
    enrollment_date DATE,
    status VARCHAR(50),
    extra JSONB,
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging.assessments CASCADE;
CREATE TABLE staging.assessments (
    assessment_id VARCHAR(50),
    course_id VARCHAR(50),
    subject_id VARCHAR(50),
    period_id VARCHAR(50),
    assessment_name VARCHAR(150),
    assessment_type VARCHAR(50),
    weight_percentage NUMERIC(5, 2),
    assessment_date DATE,
    extra JSONB,
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging.grades CASCADE;
CREATE TABLE staging.grades (
    grade_id VARCHAR(50),
    assessment_id VARCHAR(50),
    student_id VARCHAR(50),
    score NUMERIC(5, 2),
    submission_date DATE,
    feedback TEXT,
    extra JSONB,
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging.periods CASCADE;
CREATE TABLE staging.periods (
    period_id VARCHAR(50),
    period_name VARCHAR(100),
    start_date DATE,
    end_date DATE,
    weight NUMERIC(5, 2),
    extra JSONB,
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging.attendance CASCADE;
CREATE TABLE staging.attendance (
    attendance_id VARCHAR(50),
    student_id VARCHAR(50),
    course_id VARCHAR(50),
    period_id VARCHAR(50),
    total_classes INT,
    absences INT,
    extra JSONB,
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
