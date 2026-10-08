-- ==============================================================================
-- Schema: SILVER
-- Modelo relacional normalizado con integridad referencial, tipos flexibles
-- y soporte para atributos extra y entidades opcionales
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS silver;

DROP TABLE IF EXISTS silver.grades CASCADE;
DROP TABLE IF EXISTS silver.assessments CASCADE;
DROP TABLE IF EXISTS silver.attendance CASCADE;
DROP TABLE IF EXISTS silver.students CASCADE;
DROP TABLE IF EXISTS silver.subjects CASCADE;
DROP TABLE IF EXISTS silver.courses CASCADE;
DROP TABLE IF EXISTS silver.periods CASCADE;

-- 1. Courses
CREATE TABLE silver.courses (
    course_id VARCHAR(50) PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    grade_level INT,
    academic_year INT,
    extra JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Subjects
CREATE TABLE silver.subjects (
    subject_id VARCHAR(50) PRIMARY KEY,
    subject_name VARCHAR(100) NOT NULL,
    course_id VARCHAR(50),
    department VARCHAR(100),
    extra JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Periods
CREATE TABLE silver.periods (
    period_id VARCHAR(50) PRIMARY KEY,
    period_name VARCHAR(100) NOT NULL,
    start_date DATE,
    end_date DATE,
    weight NUMERIC(5, 2),
    extra JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Students
CREATE TABLE silver.students (
    student_id VARCHAR(50) PRIMARY KEY,
    document_number VARCHAR(50),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    gender VARCHAR(20),
    birth_date DATE,
    email VARCHAR(150),
    course_id VARCHAR(50),
    enrollment_date DATE,
    status VARCHAR(50) DEFAULT 'ACTIVO',
    extra JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Assessments
CREATE TABLE silver.assessments (
    assessment_id VARCHAR(50) PRIMARY KEY,
    course_id VARCHAR(50),
    subject_id VARCHAR(50),
    period_id VARCHAR(50),
    assessment_name VARCHAR(150) NOT NULL,
    assessment_type VARCHAR(50),
    weight_percentage NUMERIC(5, 2) NOT NULL,
    assessment_date DATE,
    extra JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Grades
CREATE TABLE silver.grades (
    grade_id VARCHAR(50) PRIMARY KEY,
    assessment_id VARCHAR(50) NOT NULL,
    student_id VARCHAR(50) NOT NULL,
    score NUMERIC(5, 2) NOT NULL,
    submission_date DATE,
    feedback TEXT,
    extra JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_grades_assessment FOREIGN KEY (assessment_id)
        REFERENCES silver.assessments (assessment_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_grades_student FOREIGN KEY (student_id)
        REFERENCES silver.students (student_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_grades_assessment_student UNIQUE (assessment_id, student_id)
);

-- 7. Attendance
CREATE TABLE silver.attendance (
    attendance_id VARCHAR(50) PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL,
    course_id VARCHAR(50),
    period_id VARCHAR(50),
    total_classes INT,
    absences INT,
    extra JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_silver_subjects_course ON silver.subjects (course_id);
CREATE INDEX idx_silver_students_course ON silver.students (course_id);
CREATE INDEX idx_silver_assessments_subject ON silver.assessments (subject_id);
CREATE INDEX idx_silver_assessments_period ON silver.assessments (period_id);
CREATE INDEX idx_silver_grades_student ON silver.grades (student_id);
CREATE INDEX idx_silver_grades_assessment ON silver.grades (assessment_id);
