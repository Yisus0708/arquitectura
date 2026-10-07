-- ==============================================================================
-- Schema: GOLD - POBLACIÓN DE MODELO ESTRELLA Y MARTS ANALÍTICOS
-- Idempotente: Carga limpia y estructurada de dimensiones, hechos y marts
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Carga de Dimensiones
-- ------------------------------------------------------------------------------

-- Dim Course
TRUNCATE TABLE gold.dim_course CASCADE;
INSERT INTO gold.dim_course (course_id, course_name, grade_level, academic_year)
SELECT course_id, course_name, grade_level, academic_year
FROM silver.courses;

-- Dim Subject
TRUNCATE TABLE gold.dim_subject CASCADE;
INSERT INTO gold.dim_subject (subject_id, subject_name, course_id, department)
SELECT subject_id, subject_name, course_id, department
FROM silver.subjects;

-- Dim Student
TRUNCATE TABLE gold.dim_student CASCADE;
INSERT INTO gold.dim_student (student_id, full_name, first_name, last_name, email, course_id, enrollment_date, status)
SELECT
    student_id,
    first_name || ' ' || last_name AS full_name,
    first_name,
    last_name,
    email,
    course_id,
    enrollment_date,
    status
FROM silver.students;

-- Dim Date
TRUNCATE TABLE gold.dim_date CASCADE;
WITH distinct_dates AS (
    SELECT DISTINCT submission_date AS dt FROM silver.grades
    UNION
    SELECT DISTINCT assessment_date AS dt FROM silver.assessments
    UNION
    SELECT DISTINCT enrollment_date AS dt FROM silver.students
)
INSERT INTO gold.dim_date (date_key, year, month, month_name, day, day_of_week, quarter, semester)
SELECT
    dt AS date_key,
    EXTRACT(YEAR FROM dt)::INT AS year,
    EXTRACT(MONTH FROM dt)::INT AS month,
    TO_CHAR(dt, 'TMMonth') AS month_name,
    EXTRACT(DAY FROM dt)::INT AS day,
    TO_CHAR(dt, 'TMDay') AS day_of_week,
    EXTRACT(QUARTER FROM dt)::INT AS quarter,
    CASE WHEN EXTRACT(MONTH FROM dt) <= 6 THEN 1 ELSE 2 END AS semester
FROM distinct_dates
WHERE dt IS NOT NULL;


-- ------------------------------------------------------------------------------
-- 2. Carga de Tabla de Hechos: Fact Grades
-- ------------------------------------------------------------------------------
TRUNCATE TABLE gold.fact_grades;
INSERT INTO gold.fact_grades (
    grade_id, student_id, subject_id, course_id, submission_date,
    assessment_id, assessment_name, assessment_type, weight_percentage,
    score, weighted_points, is_passing, feedback
)
SELECT
    g.grade_id,
    g.student_id,
    ev.subject_id,
    st.course_id,
    g.submission_date,
    ev.assessment_id,
    ev.assessment_name,
    ev.assessment_type,
    ev.weight_percentage,
    g.score,
    ROUND((g.score * ev.weight_percentage / 100.0), 3) AS weighted_points,
    (g.score >= 3.0) AS is_passing,
    g.feedback
FROM silver.grades g
INNER JOIN silver.assessments ev ON g.assessment_id = ev.assessment_id
INNER JOIN silver.students st ON g.student_id = st.student_id;


-- ------------------------------------------------------------------------------
-- 3. Mart 1: Nota Final Ponderada por Estudiante y Materia
-- Métrica central: final_grade = SUM(score * weight_percentage / 100.0)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.final_grade_by_student_subject CASCADE;
CREATE TABLE gold.final_grade_by_student_subject AS
SELECT
    f.student_id,
    st.full_name,
    f.course_id,
    c.course_name,
    f.subject_id,
    sub.subject_name,
    sub.department,
    ROUND(SUM(f.score * f.weight_percentage / 100.0), 2) AS final_grade,
    ROUND(SUM(f.weight_percentage), 2) AS total_evaluated_weight,
    (ROUND(SUM(f.score * f.weight_percentage / 100.0), 2) >= 3.0) AS is_approved,
    CASE
        WHEN ROUND(SUM(f.score * f.weight_percentage / 100.0), 2) >= 3.0 THEN 'Aprobado'
        ELSE 'Reprobado'
    END AS approval_status,
    CURRENT_TIMESTAMP AS calculated_at
FROM gold.fact_grades f
INNER JOIN gold.dim_student st ON f.student_id = st.student_id
INNER JOIN gold.dim_subject sub ON f.subject_id = sub.subject_id
INNER JOIN gold.dim_course c ON f.course_id = c.course_id
GROUP BY
    f.student_id, st.full_name, f.course_id, c.course_name,
    f.subject_id, sub.subject_name, sub.department;

CREATE INDEX idx_gold_final_student ON gold.final_grade_by_student_subject (student_id);
CREATE INDEX idx_gold_final_subject ON gold.final_grade_by_student_subject (subject_id);


-- ------------------------------------------------------------------------------
-- 4. Mart 2: Rendimiento Académico por Asignatura (Subject Performance)
-- Métricas: Promedio, % Aprobados, % Reprobados (Suma = 100%)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.subject_performance CASCADE;
CREATE TABLE gold.subject_performance AS
SELECT
    fg.subject_id,
    fg.subject_name,
    fg.course_id,
    fg.course_name,
    fg.department,
    COUNT(DISTINCT fg.student_id) AS enrolled_students,
    ROUND(AVG(fg.final_grade), 2) AS average_final_grade,
    MIN(fg.final_grade) AS min_final_grade,
    MAX(fg.final_grade) AS max_final_grade,
    SUM(CASE WHEN fg.is_approved THEN 1 ELSE 0 END) AS approved_count,
    SUM(CASE WHEN NOT fg.is_approved THEN 1 ELSE 0 END) AS failed_count,
    ROUND(
        (SUM(CASE WHEN fg.is_approved THEN 1 ELSE 0 END)::NUMERIC * 100.0 / NULLIF(COUNT(DISTINCT fg.student_id), 0)),
        2
    ) AS pass_rate_percentage,
    ROUND(
        (SUM(CASE WHEN NOT fg.is_approved THEN 1 ELSE 0 END)::NUMERIC * 100.0 / NULLIF(COUNT(DISTINCT fg.student_id), 0)),
        2
    ) AS fail_rate_percentage,
    CURRENT_TIMESTAMP AS calculated_at
FROM gold.final_grade_by_student_subject fg
GROUP BY
    fg.subject_id, fg.subject_name, fg.course_id, fg.course_name, fg.department;


-- ------------------------------------------------------------------------------
-- 5. Mart 3: Rendimiento Integral del Estudiante (Student Performance)
-- Métricas: Promedio general acumulado (GPA), ranking general y ranking por curso
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.student_performance CASCADE;
CREATE TABLE gold.student_performance AS
WITH student_stats AS (
    SELECT
        fg.student_id,
        fg.full_name,
        fg.course_id,
        fg.course_name,
        COUNT(DISTINCT fg.subject_id) AS subjects_enrolled,
        SUM(CASE WHEN fg.is_approved THEN 1 ELSE 0 END) AS subjects_passed,
        SUM(CASE WHEN NOT fg.is_approved THEN 1 ELSE 0 END) AS subjects_failed,
        ROUND(AVG(fg.final_grade), 2) AS overall_average,
        MIN(fg.final_grade) AS lowest_subject_grade,
        MAX(fg.final_grade) AS highest_subject_grade
    FROM gold.final_grade_by_student_subject fg
    GROUP BY fg.student_id, fg.full_name, fg.course_id, fg.course_name
)
SELECT
    student_id,
    full_name,
    course_id,
    course_name,
    subjects_enrolled,
    subjects_passed,
    subjects_failed,
    overall_average,
    lowest_subject_grade,
    highest_subject_grade,
    DENSE_RANK() OVER(ORDER BY overall_average DESC) AS academic_ranking_overall,
    DENSE_RANK() OVER(PARTITION BY course_id ORDER BY overall_average DESC) AS academic_ranking_in_course,
    CASE
        WHEN overall_average >= 4.5 THEN 'Excelente (Cuadro de Honor)'
        WHEN overall_average >= 4.0 THEN 'Sobresaliente'
        WHEN overall_average >= 3.0 THEN 'Aceptable'
        ELSE 'Bajo / En Riesgo Académico'
    END AS performance_category,
    CURRENT_TIMESTAMP AS calculated_at
FROM student_stats;


-- ------------------------------------------------------------------------------
-- 6. Mart 4: Rendimiento por Curso / Cohorte (Course Performance)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.course_performance CASCADE;
CREATE TABLE gold.course_performance AS
SELECT
    c.course_id,
    c.course_name,
    c.grade_level,
    c.academic_year,
    COUNT(DISTINCT sp.student_id) AS total_students,
    ROUND(AVG(sp.overall_average), 2) AS course_gpa,
    SUM(sp.subjects_passed) AS total_subjects_passed,
    SUM(sp.subjects_failed) AS total_subjects_failed,
    ROUND(
        (SUM(sp.subjects_passed)::NUMERIC * 100.0 / NULLIF(SUM(sp.subjects_passed + sp.subjects_failed), 0)),
        2
    ) AS overall_pass_rate_percentage,
    ROUND(
        (SUM(sp.subjects_failed)::NUMERIC * 100.0 / NULLIF(SUM(sp.subjects_passed + sp.subjects_failed), 0)),
        2
    ) AS overall_fail_rate_percentage,
    CURRENT_TIMESTAMP AS calculated_at
FROM gold.dim_course c
INNER JOIN gold.student_performance sp ON c.course_id = sp.course_id
GROUP BY c.course_id, c.course_name, c.grade_level, c.academic_year;


-- ------------------------------------------------------------------------------
-- 7. Mart 5: Rendimiento por Tipo de Evaluación (Assessment Type Performance)
-- Analiza cómo responden los estudiantes por instrumento pedagógico
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.assessment_type_performance CASCADE;
CREATE TABLE gold.assessment_type_performance AS
SELECT
    assessment_type,
    COUNT(*) AS total_evaluations_taken,
    ROUND(AVG(score), 2) AS average_score,
    MIN(score) AS min_score,
    MAX(score) AS max_score,
    SUM(CASE WHEN is_passing THEN 1 ELSE 0 END) AS passing_count,
    SUM(CASE WHEN NOT is_passing THEN 1 ELSE 0 END) AS failing_count,
    ROUND(
        (SUM(CASE WHEN is_passing THEN 1 ELSE 0 END)::NUMERIC * 100.0 / COUNT(*)),
        2
    ) AS pass_rate_percentage,
    CURRENT_TIMESTAMP AS calculated_at
FROM gold.fact_grades
GROUP BY assessment_type;


-- ------------------------------------------------------------------------------
-- 8. Mart 6: Cuadro de Honor y Refuerzo (Top & Bottom Students)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.top_bottom_students CASCADE;
CREATE TABLE gold.top_bottom_students AS
WITH ranked_all AS (
    SELECT
        student_id,
        full_name,
        course_id,
        course_name,
        overall_average,
        academic_ranking_overall,
        ROW_NUMBER() OVER(ORDER BY overall_average DESC) AS rn_top,
        ROW_NUMBER() OVER(ORDER BY overall_average ASC) AS rn_bottom
    FROM gold.student_performance
)
SELECT
    'Top 5 Cuadro de Honor' AS cohort_group,
    academic_ranking_overall AS ranking_position,
    student_id,
    full_name,
    course_name,
    overall_average
FROM ranked_all
WHERE rn_top <= 5
UNION ALL
SELECT
    'Bottom 5 Plan de Refuerzo' AS cohort_group,
    academic_ranking_overall AS ranking_position,
    student_id,
    full_name,
    course_name,
    overall_average
FROM ranked_all
WHERE rn_bottom <= 5
ORDER BY overall_average DESC;


-- ------------------------------------------------------------------------------
-- 9. Mart 7: Materias con Mayor Tasa de Reprobación
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.subjects_highest_failure CASCADE;
CREATE TABLE gold.subjects_highest_failure AS
SELECT
    subject_id,
    subject_name,
    course_name,
    department,
    enrolled_students,
    failed_count,
    fail_rate_percentage,
    average_final_grade,
    DENSE_RANK() OVER(ORDER BY fail_rate_percentage DESC, average_final_grade ASC) AS failure_rank
FROM gold.subject_performance
ORDER BY fail_rate_percentage DESC, average_final_grade ASC;
