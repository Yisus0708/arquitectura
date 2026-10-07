-- ==============================================================================
-- Schema: SILVER
-- Modelo relacional normalizado con integridad referencial estricta:
-- Llaves primarias (PK), foráneas (FK), NOT NULL y restricciones CHECK.
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS silver;

-- 1. Courses
DROP TABLE IF EXISTS silver.grades CASCADE;
DROP TABLE IF EXISTS silver.assessments CASCADE;
DROP TABLE IF EXISTS silver.students CASCADE;
DROP TABLE IF EXISTS silver.subjects CASCADE;
DROP TABLE IF EXISTS silver.courses CASCADE;

CREATE TABLE silver.courses (
    course_id VARCHAR(50) PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    grade_level INT NOT NULL CHECK (grade_level BETWEEN 1 AND 12),
    academic_year INT NOT NULL CHECK (academic_year >= 2000),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Subjects
CREATE TABLE silver.subjects (
    subject_id VARCHAR(50) PRIMARY KEY,
    subject_name VARCHAR(100) NOT NULL,
    course_id VARCHAR(50) NOT NULL,
    department VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_subjects_course FOREIGN KEY (course_id)
        REFERENCES silver.courses (course_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 3. Students
CREATE TABLE silver.students (
    student_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    course_id VARCHAR(50) NOT NULL,
    enrollment_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_students_course FOREIGN KEY (course_id)
        REFERENCES silver.courses (course_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 4. Assessments
CREATE TABLE silver.assessments (
    assessment_id VARCHAR(50) PRIMARY KEY,
    subject_id VARCHAR(50) NOT NULL,
    assessment_name VARCHAR(150) NOT NULL,
    assessment_type VARCHAR(50) NOT NULL,
    weight_percentage NUMERIC(5, 2) NOT NULL,
    assessment_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_assessments_subject FOREIGN KEY (subject_id)
        REFERENCES silver.subjects (subject_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_assessment_weight CHECK (weight_percentage >= 0.0 AND weight_percentage <= 100.0)
);

-- 5. Grades
CREATE TABLE silver.grades (
    grade_id VARCHAR(50) PRIMARY KEY,
    assessment_id VARCHAR(50) NOT NULL,
    student_id VARCHAR(50) NOT NULL,
    score NUMERIC(3, 1) NOT NULL,
    submission_date DATE NOT NULL,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_grades_assessment FOREIGN KEY (assessment_id)
        REFERENCES silver.assessments (assessment_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_grades_student FOREIGN KEY (student_id)
        REFERENCES silver.students (student_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT uq_grades_assessment_student UNIQUE (assessment_id, student_id),
    CONSTRAINT chk_grade_score CHECK (score >= 0.0 AND score <= 5.0)
);

-- Índices para optimización de queries analíticos y joins
CREATE INDEX idx_silver_subjects_course ON silver.subjects (course_id);
CREATE INDEX idx_silver_students_course ON silver.students (course_id);
CREATE INDEX idx_silver_assessments_subject ON silver.assessments (subject_id);
CREATE INDEX idx_silver_grades_student ON silver.grades (student_id);
CREATE INDEX idx_silver_grades_assessment ON silver.grades (assessment_id);
