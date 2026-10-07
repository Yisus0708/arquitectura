-- ==============================================================================
-- Schema: STAGING
-- Tablas intermedias tipadas, normalizadas (snake_case) y limpias
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS staging;

DROP TABLE IF EXISTS staging.courses CASCADE;
CREATE TABLE staging.courses (
    course_id VARCHAR(50),
    course_name VARCHAR(100),
    grade_level INT,
    academic_year INT,
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging.subjects CASCADE;
CREATE TABLE staging.subjects (
    subject_id VARCHAR(50),
    subject_name VARCHAR(100),
    course_id VARCHAR(50),
    department VARCHAR(100),
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging.students CASCADE;
CREATE TABLE staging.students (
    student_id VARCHAR(50),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(150),
    course_id VARCHAR(50),
    enrollment_date DATE,
    status VARCHAR(50),
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging.assessments CASCADE;
CREATE TABLE staging.assessments (
    assessment_id VARCHAR(50),
    subject_id VARCHAR(50),
    assessment_name VARCHAR(150),
    assessment_type VARCHAR(50),
    weight_percentage NUMERIC(5, 2),
    assessment_date DATE,
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging.grades CASCADE;
CREATE TABLE staging.grades (
    grade_id VARCHAR(50),
    assessment_id VARCHAR(50),
    student_id VARCHAR(50),
    score NUMERIC(3, 1),
    submission_date DATE,
    feedback TEXT,
    _extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
