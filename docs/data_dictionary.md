# Diccionario de Datos del Sistema de Calificaciones Escolar

> **Propósito**: Documentar con exactitud las entidades, columnas, tipos de datos, restricciones y métricas detectadas en la capa `raw` generada.

---

## 1. Entidad: `Courses` (`courses.csv`)
- **Total de registros**: 4
- **Clave Primaria Candidata**: `course_id`
- **Duplicados en PK detectados (anomalías raw)**: 0

| Columna | Tipo Inferido | Nulos (%) | Únicos | Rango (Min - Max) | Ejemplo | Descripción de Negocio |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_id` | str | 0 (0.0%) | 4 | N/A | `CUR-10A` | Identificador único del curso/grado (ej. CUR-10A). |
| `course_name` | str | 0 (0.0%) | 4 | N/A | `Grado 10-A` | Nombre descriptivo del grupo y salón (ej. Grado 10-A). |
| `grade_level` | int64 | 0 (0.0%) | 2 | 10.0 a 11.0 | `10` | Nivel o grado escolar (10 o 11). |
| `academic_year` | int64 | 0 (0.0%) | 1 | 2026.0 a 2026.0 | `2026` | Año lectivo académico (2026). |

---

## 1. Entidad: `Subjects` (`subjects.csv`)
- **Total de registros**: 20
- **Clave Primaria Candidata**: `subject_id`
- **Duplicados en PK detectados (anomalías raw)**: 0

| Columna | Tipo Inferido | Nulos (%) | Únicos | Rango (Min - Max) | Ejemplo | Descripción de Negocio |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `subject_id` | str | 0 (0.0%) | 20 | N/A | `SUB-MAT-10A` | Identificador único de la asignatura para el curso. |
| `subject_name` | str | 0 (0.0%) | 10 | N/A | `Matemáticas 10°` | Nombre de la materia (Matemáticas, Física, etc.). |
| `course_id` | str | 0 (0.0%) | 4 | N/A | `CUR-10A` | FK referenciando al curso que dicta la asignatura. |
| `department` | str | 0 (0.0%) | 4 | N/A | `Ciencias Exactas` | Área o departamento académico pedagógico. |

---

## 1. Entidad: `Students` (`students.csv`)
- **Total de registros**: 83
- **Clave Primaria Candidata**: `student_id`
- **Duplicados en PK detectados (anomalías raw)**: 1

| Columna | Tipo Inferido | Nulos (%) | Únicos | Rango (Min - Max) | Ejemplo | Descripción de Negocio |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `student_id` | str | 0 (0.0%) | 82 | N/A | `EST-001` | Identificador único del estudiante matriculado. |
| `first_name` | str | 0 (0.0%) | 30 | N/A | `Andrés` | Primer nombre del alumno. |
| `last_name` | str | 1 (1.2%) | 25 | N/A | `Martínez` | Apellidos del alumno. |
| `email` | str | 0 (0.0%) | 83 | N/A | `andres.martinez1@colegio.edu.co` | Correo electrónico institucional del estudiante. |
| `course_id` | str | 0 (0.0%) | 5 | N/A | `CUR-10A` | FK referenciando al curso asignado. |
| `enrollment_date` | str | 0 (0.0%) | 1 | N/A | `2026-01-15` | Fecha de ingreso y formalización de matrícula. |
| `status` | str | 0 (0.0%) | 1 | N/A | `ACTIVO` | Estado académico del estudiante (ACTIVO). |

---

## 1. Entidad: `Assessments` (`assessments.csv`)
- **Total de registros**: 83
- **Clave Primaria Candidata**: `assessment_id`
- **Duplicados en PK detectados (anomalías raw)**: 0

| Columna | Tipo Inferido | Nulos (%) | Únicos | Rango (Min - Max) | Ejemplo | Descripción de Negocio |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `assessment_id` | str | 0 (0.0%) | 83 | N/A | `EVAL-SUB-MAT-10A-01` | Identificador único del instrumento de evaluación. |
| `subject_id` | str | 0 (0.0%) | 20 | N/A | `SUB-MAT-10A` | FK referenciando a la materia evaluada. |
| `assessment_name` | str | 1 (1.2%) | 7 | N/A | `Taller Práctico 1` | Nombre de la prueba (Parcial 1, Quiz, etc.). |
| `assessment_type` | str | 0 (0.0%) | 4 | N/A | `Taller` | Categoría (Taller, Parcial, Quiz, Examen Final, Proyecto). |
| `weight_percentage` | float64 | 0 (0.0%) | 7 | -15.0 a 150.0 | `15.0` | Porcentaje de ponderación en la nota final (0-100%). La suma por materia debe ser 100%. |
| `assessment_date` | str | 0 (0.0%) | 7 | N/A | `2026-02-20` | Fecha programada de aplicación del examen. |

---

## 1. Entidad: `Grades` (`grades.csv`)
- **Total de registros**: 1627
- **Clave Primaria Candidata**: `grade_id`
- **Duplicados en PK detectados (anomalías raw)**: 1

| Columna | Tipo Inferido | Nulos (%) | Únicos | Rango (Min - Max) | Ejemplo | Descripción de Negocio |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `grade_id` | str | 0 (0.0%) | 1626 | N/A | `GRD-00001` | Identificador único del registro de calificación individual. |
| `assessment_id` | str | 0 (0.0%) | 81 | N/A | `EVAL-SUB-MAT-10A-01` | FK referenciando la evaluación aplicada. |
| `student_id` | str | 0 (0.0%) | 81 | N/A | `EST-001` | FK referenciando al estudiante evaluado. |
| `score` | float64 | 1 (0.06%) | 43 | -1.5 a 6.8 | `3.5` | Calificación obtenida en escala 0.0 a 5.0 (aprobación >= 3.0). |
| `submission_date` | str | 0 (0.0%) | 2 | N/A | `2026-03-30` | Fecha de entrega o subida de la nota. |
| `feedback` | str | 0 (0.0%) | 13 | N/A | `Muy buen análisis y resolución metodológica.` | Retroalimentación cualitativa pedagógica del docente. |

---
