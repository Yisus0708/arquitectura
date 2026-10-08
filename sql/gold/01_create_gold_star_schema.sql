-- ==============================================================================
-- Schema: GOLD - MODELO ESTRELLA (STAR SCHEMA)
-- Optimizado para consultas dimensionales y modelado en Power BI / BI Tools
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS gold;

DROP TABLE IF EXISTS gold.fact_grades CASCADE;
DROP TABLE IF EXISTS gold.dim_student CASCADE;
DROP TABLE IF EXISTS gold.dim_subject CASCADE;
DROP TABLE IF EXISTS gold.dim_course CASCADE;
DROP TABLE IF EXISTS gold.dim_period CASCADE;
DROP TABLE IF EXISTS gold.dim_date CASCADE;

-- 1. Dimensión: Estudiante
CREATE TABLE gold.dim_student (
    student_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    document_number VARCHAR(50),
    gender VARCHAR(20),
    email VARCHAR(150),
    course_id VARCHAR(50),
    enrollment_date DATE,
    status VARCHAR(50)
);

-- 2. Dimensión: Curso
CREATE TABLE gold.dim_course (
    course_id VARCHAR(50) PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    grade_level INT,
    academic_year INT
);

-- 3. Dimensión: Asignatura (Materia)
CREATE TABLE gold.dim_subject (
    subject_id VARCHAR(50) PRIMARY KEY,
    subject_name VARCHAR(100) NOT NULL,
    course_id VARCHAR(50),
    department VARCHAR(100)
);

-- 4. Dimensión: Periodo
CREATE TABLE gold.dim_period (
    period_id VARCHAR(50) PRIMARY KEY,
    period_name VARCHAR(100) NOT NULL,
    weight NUMERIC(5, 2)
);

-- 5. Dimensión: Calendario / Fecha
CREATE TABLE gold.dim_date (
    date_key DATE PRIMARY KEY,
    year INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day INT NOT NULL,
    day_of_week VARCHAR(20) NOT NULL,
    quarter INT NOT NULL,
    semester INT NOT NULL
);

-- 6. Tabla de Hechos: Calificaciones Individuales (Fact Grades)
CREATE TABLE gold.fact_grades (
    grade_id VARCHAR(50) PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL REFERENCES gold.dim_student(student_id),
    subject_id VARCHAR(50) REFERENCES gold.dim_subject(subject_id),
    course_id VARCHAR(50),
    period_id VARCHAR(50),
    submission_date DATE,
    assessment_id VARCHAR(50) NOT NULL,
    assessment_name VARCHAR(150) NOT NULL,
    assessment_type VARCHAR(50),
    weight_percentage NUMERIC(5, 2) NOT NULL,
    score NUMERIC(5, 2) NOT NULL,
    weighted_points NUMERIC(6, 3) NOT NULL,
    is_passing BOOLEAN NOT NULL,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gold_fact_student ON gold.fact_grades (student_id);
CREATE INDEX idx_gold_fact_subject ON gold.fact_grades (subject_id);
CREATE INDEX idx_gold_fact_course ON gold.fact_grades (course_id);
CREATE INDEX idx_gold_fact_period ON gold.fact_grades (period_id);
CREATE INDEX idx_gold_fact_date ON gold.fact_grades (submission_date);
