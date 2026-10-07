# 📊 Especificación de Diseño de Tablero Power BI
## Sistema Analítico de Calificaciones y Rendimiento Académico Escolar

Este documento describe la arquitectura semántica, el modelo de datos dimensional, las páginas recomendadas, las métricas DAX clave y las consideraciones de visualización para el tablero en **Power BI** conectado al esquema `gold` de PostgreSQL (`school_dw`).

---

## 1. Modelo Semántico Dimensional (Star Schema)

El tablero se conecta directamente a la capa `gold` mediante el **modelo estrella**:

```
           +-------------------+
           |  gold.dim_course  |
           +---------+---------+
                     | 1
                     |
                     | *
+-----------------+  |  +--------------------+  *  +------------------+
| gold.dim_student|--+--|  gold.fact_grades  |----+| gold.dim_subject |
+-----------------+ 1   +---------+----------+   1 +------------------+
                                  | *
                                  |
                                  | 1
                        +---------+---------+
                        |   gold.dim_date   |
                        +-------------------+
```

### Relaciones en Power BI
1. `gold.fact_grades[student_id]` $\rightarrow$ `gold.dim_student[student_id]` (Muchos a Uno, Filtro Cruzado: Sencillo).
2. `gold.fact_grades[subject_id]` $\rightarrow$ `gold.dim_subject[subject_id]` (Muchos a Uno, Filtro Cruzado: Sencillo).
3. `gold.fact_grades[course_id]` $\rightarrow$ `gold.dim_course[course_id]` (Muchos a Uno, Filtro Cruzado: Sencillo).
4. `gold.fact_grades[submission_date]` $\rightarrow$ `gold.dim_date[date_key]` (Muchos a Uno, Filtro Cruzado: Sencillo).

---

## 2. Métricas DAX Fundamentales (Calculated Measures)

Se recomienda organizar las medidas en una tabla vacía llamada `_Medidas`:

### Métrica 1: Total Calificaciones Evaluadas
```dax
Total Calificaciones = COUNTROWS(gold.fact_grades)
```

### Métrica 2: Promedio de Calificación Individual
```dax
Nota Promedio = AVERAGE(gold.fact_grades[score])
```

### Métrica 3: Nota Final Ponderada por Asignatura
```dax
Nota Final Ponderada = 
SUMX(
    gold.fact_grades,
    gold.fact_grades[score] * (gold.fact_grades[weight_percentage] / 100)
)
```

### Métrica 4: Estudiantes Evaluados Únicos
```dax
Estudiantes Evaluados = DISTINCTCOUNT(gold.fact_grades[student_id])
```

### Métrica 5: Total Estudiantes Aprobados
```dax
Estudiantes Aprobados = 
CALCULATE(
    DISTINCTCOUNT(gold.final_grade_by_student_subject[student_id]),
    gold.final_grade_by_student_subject[is_approved] = TRUE()
)
```

### Métrica 6: Tasa de Aprobación (%)
```dax
% Aprobacion = 
DIVIDE(
    [Estudiantes Aprobados],
    [Estudiantes Evaluados],
    0
)
```

### Métrica 7: Tasa de Reprobación (%)
```dax
% Reprobacion = 1 - [% Aprobacion]
```

### Métrica 8: Promedio General de la Institución (GPA)
```dax
Promedio General Colegio = AVERAGE(gold.final_grade_by_student_subject[final_grade])
```

---

## 3. Páginas del Tablero y Visualizaciones Recomendadas

### 📌 Página 1: Resumen Ejecutivo (Vista Rectoría y Dirección Académica)
* **Objetivo**: Proveer una visión macro instantánea de la salud académica del colegio.
* **KPI Cards superiores**:
  - Promedio General Institucional (ej. `3.85 / 5.0`).
  - % General de Aprobación (ej. `86.5%`).
  - Total Estudiantes Matriculados y Activos (`80`).
  - Asignatura con Mayor Riesgo de Pérdida.
* **Visualizaciones**:
  1. **Gráfico de Barras Agrupadas**: Promedio general por Grado/Curso (`Grado 10-A`, `10-B`, `11-A`, `11-B`).
  2. **Gráfico de Donut / Gauge**: Distribución % Aprobados vs % Reprobados (Target: $\ge 85\%$ aprobación).
  3. **Gráfico de Columnas por Departamento**: Comparativa de rendimiento entre Ciencias Exactas, Humanidades, Idiomas y Ciencias Naturales.
* **Segmentadores (Slicers)**:
  - Año Lectivo (`2026`).
  - Nivel / Grado (`10°`, `11°`).
  - Curso.

---

### 📌 Página 2: Rendimiento por Materia (Vista Departamentos y Jefes de Área)
* **Objetivo**: Identificar asignaturas críticas, evaluar curvas de notas y tipos de prueba.
* **Visualizaciones**:
  1. **Matriz / Tabla de Materias**:
     - Columnas: Nombre Materia, Docente/Depto, Estudiantes, Promedio, % Aprobados, % Reprobados.
     - Formato Condicional: Barras de datos para el promedio; mapa de calor de color verde/rojo para % de aprobación.
  2. **Gráfico de Barras Horizontales**: Top 5 Materias con mayor tasa de reprobación (conectado a `gold.subjects_highest_failure`).
  3. **Gráfico de Columnas por Tipo de Evaluación**: Desempeño comparativo entre Parciales, Talleres, Quizzes y Exámenes Finales (conectado a `gold.assessment_type_performance`).
* **Insights Clave**:
  - ¿Los estudiantes reprueban más por exámenes teóricos o por falta de entrega de talleres?

---

### 📌 Página 3: Desempeño del Estudiante (Vista Docentes y Orientación Escolar)
* **Objetivo**: Análisis granular por alumno para tutorías personalizadas y comités de evaluación.
* **Visualizaciones**:
  1. **Ficha de Búsqueda de Estudiante**: Slicer de búsqueda rápida por Nombre o Código (`EST-XXX`).
  2. **Tabla Detalle de Calificaciones**:
     - Asignatura, Tipo de Evaluación, Ponderación (%), Nota Obtenida, Puntos Aportados, Estado.
  3. **Gráfico de Radar o Barras**: Perfil de notas del estudiante comparado contra el promedio de su curso.
  4. **Tabla de Cuadro de Honor y Plan de Refuerzo** (conectada a `gold.top_bottom_students`):
     - Cuadro verde: Top 5 mejores promedios.
     - Cuadro ámbar: Bottom 5 estudiantes que requieren tutoría de nivelación.

---

### 📌 Página 4: Comparativa de Cursos y Cohortes (Vista Coordinación Académica)
* **Objetivo**: Comparar el avance pedagógico homogéneo entre salones del mismo grado (ej. 10-A vs 10-B).
* **Visualizaciones**:
  1. **Gráfico de Dispersión (Scatter Plot)**:
     - Eje X: Promedio de Asignatura.
     - Eje Y: Desviación Estándar / Varianza de Notas.
     - Tamaño de Burbuja: Número de estudiantes en riesgo.
  2. **Gráfico de Líneas Temporal**: Evolución de notas promedio por mes a lo largo del calendario semestral (`dim_date`).
  3. **Tabla Comparativa de Salones**: Promedio por salón, tasa de aprobación y materias críticas.

---

## 4. Guía de Conexión a PostgreSQL desde Power BI Desktop

1. Abrir **Power BI Desktop**.
2. Ir a **Inicio** > **Obtener Datos** > **Base de datos PostgreSQL**.
3. Configurar:
   - **Servidor**: `localhost:5432` (o IP del contenedor).
   - **Base de datos**: `school_dw`.
   - **Modo de conectividad**: `Import` (recomendado para modelos dimensionales < 100M filas) o `DirectQuery`.
4. En el Navegador, seleccionar las tablas del esquema `gold`:
   - `dim_student`, `dim_course`, `dim_subject`, `dim_date`, `fact_grades`.
   - Vistas analíticas: `final_grade_by_student_subject`, `subject_performance`, `student_performance`, `course_performance`, `assessment_type_performance`.
5. Clic en **Cargar** y verificar relaciones en la vista de modelo.
