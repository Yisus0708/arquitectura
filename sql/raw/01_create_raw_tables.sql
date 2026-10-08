-- ==============================================================================
-- Schema: RAW
-- Copia fiel de los archivos CSV con tipos TEXT, metadatos de auditoría y columna extra
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS raw;

DROP TABLE IF EXISTS raw.courses CASCADE;
CREATE TABLE raw.courses (
    course_id VARCHAR(50),
    course_name VARCHAR(100),
    grade_level VARCHAR(20),
    academic_year VARCHAR(20),
    extra TEXT,
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(100)
);

DROP TABLE IF EXISTS raw.subjects CASCADE;
CREATE TABLE raw.subjects (
    subject_id VARCHAR(50),
    subject_name VARCHAR(100),
    course_id VARCHAR(50),
    department VARCHAR(100),
    extra TEXT,
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(100)
);

DROP TABLE IF EXISTS raw.students CASCADE;
CREATE TABLE raw.students (
    student_id VARCHAR(50),
    document_number VARCHAR(50),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    gender VARCHAR(20),
    birth_date VARCHAR(50),
    email VARCHAR(150),
    course_id VARCHAR(50),
    enrollment_date VARCHAR(50),
    status VARCHAR(50),
    extra TEXT,
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(100)
);

DROP TABLE IF EXISTS raw.assessments CASCADE;
CREATE TABLE raw.assessments (
    assessment_id VARCHAR(50),
    course_id VARCHAR(50),
    subject_id VARCHAR(50),
    period_id VARCHAR(50),
    assessment_name VARCHAR(150),
    assessment_type VARCHAR(50),
    weight_percentage VARCHAR(20),
    assessment_date VARCHAR(50),
    extra TEXT,
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(100)
);

DROP TABLE IF EXISTS raw.grades CASCADE;
CREATE TABLE raw.grades (
    grade_id VARCHAR(50),
    assessment_id VARCHAR(50),
    student_id VARCHAR(50),
    score VARCHAR(20),
    submission_date VARCHAR(50),
    feedback TEXT,
    extra TEXT,
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(100)
);

DROP TABLE IF EXISTS raw.periods CASCADE;
CREATE TABLE raw.periods (
    period_id VARCHAR(50),
    period_name VARCHAR(100),
    start_date VARCHAR(50),
    end_date VARCHAR(50),
    weight VARCHAR(20),
    extra TEXT,
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(100)
);

DROP TABLE IF EXISTS raw.attendance CASCADE;
CREATE TABLE raw.attendance (
    attendance_id VARCHAR(50),
    student_id VARCHAR(50),
    course_id VARCHAR(50),
    period_id VARCHAR(50),
    total_classes VARCHAR(20),
    absences VARCHAR(20),
    extra TEXT,
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(100)
);
