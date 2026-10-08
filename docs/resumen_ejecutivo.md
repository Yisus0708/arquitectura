# 📌 Resumen Ejecutivo: ¿Qué es y Cómo Funciona este Proyecto?

---

## 1. ¿Qué es este proyecto? (En pocas palabras)
Es una **Plataforma Integral de Ingeniería de Datos y Analítica Académica**. 
Permite que un colegio o institución educativa tome sus archivos de calificaciones en Excel (que suelen venir desordenados, con errores humanos y formatos inconsistentes), los procese y limpie automáticamente en segundos, los guarde de forma segura en una base de datos analítica profesional (**PostgreSQL**), y los visualice en un **Tablero Web en tiempo real** o en **Power BI**.

---

## 2. ¿Qué problema resuelve?
* **Archivos desordenados:** Cada docente o administrativo llena el Excel a su manera (unos usan coma `,`, otros punto `.`, columnas con nombres distintos).
* **Errores humanos inadvertidos:** Calificaciones fuera de escala (ej. un `7.0` o `-1.0` en escala de 0 a 5), notas de evaluaciones que no suman el 100%, o fechas imposibles.
* **Falta de visibilidad a tiempo:** La dirección académica suele enterarse de qué estudiantes van perdiendo cuando el año escolar ya terminó, sin tiempo de actuar.

---

## 3. ¿Cómo funciona? (El flujo paso a paso)

El sistema opera en **4 pasos automáticos**:

```
[1. Archivo Excel] 
       │
       ▼
[2. Detección Inteligente] ───> Mapea nombres de columnas y hojas automáticamente
       │
       ▼
[3. Filtro de Calidad & Cuarentena] 
       │  ├── Datos Inválidos ──> data/errors/ (Aislados con motivo del error)
       │  └── Datos Válidos   ──> Continúan al almacén
       ▼
[4. Arquitectura Medallion en PostgreSQL]
       ├── RAW      : Copia original inalterable (con firma SHA-256).
       ├── STAGING  : Datos limpios, sin duplicados y normalizados.
       ├── SILVER   : Modelo relacional estricto con llaves (PK/FK).
       └── GOLD     : Modelo Estrella para consultas analíticas instantáneas.
       │
       ▼
[5. Visualización] ───> Dashboard Web (FastAPI + Chart.js) / Power BI
```

### Paso 1: Ingesta Inteligente (Sin esquemas fijos)
El usuario sube el Excel a la aplicación web. El sistema no le exige nombres exactos de columnas: analiza los encabezados en español y el contenido de las celdas para identificar automáticamente estudiantes, materias, cursos, notas y asistencias.

### Paso 2: Filtro de Calidad y Cuarentena (Data Quality)
* **Auto-corrección:** Convierte automáticamente comas en puntos (ej. `4,5` pasa a `4.5`).
* **Aislamiento Seguro:** Si una fila tiene un error grave (ej. nota mayor a 5.0, estudiante que no existe o evaluación que no suma el 100%), **no frena el sistema**. Aparta esa fila en una carpeta de errores (`data/errors/`) explicando exactamente por qué falló, y procesa todo lo que sí está bien.

### Paso 3: Almacén de Datos (Arquitectura Medallion en PostgreSQL)
Los datos pasan por 4 niveles de madurez:
1. **Raw (Bronce):** Respaldo idéntico al origen para auditorías.
2. **Staging:** Limpieza técnica y eliminación de duplicados.
3. **Silver (Plata):** Base de datos relacional sólida en 3ra Forma Normal (3NF), asegurando que no haya materias ni alumnos huérfanos.
4. **Gold (Oro):** Modelo dimensional tipo estrella (Star Schema) que calcula automáticamente:
   - Promedio general institucional (GPA).
   - Tasas de aprobación y reprobación por materia y curso.
   - Cuadro de honor (Top estudiantes) y planes de refuerzo (estudiantes en riesgo).

### Paso 4: Visualización en Tiempo Real
* **Aplicación Web Activa (`http://localhost:8000`):** Muestra tarjetas con KPIs, gráficas interactivas de rendimiento, ranking de cursos y fichas individuales de estudiantes.
* **Power BI:** Conexión directa a las tablas `gold` para reportes gerenciales listos para imprimir o compartir.

---

## 4. Estructura de Componentes Clave

| Archivo / Carpeta | ¿Para qué sirve? |
| :--- | :--- |
| [`app_web.py`](../app_web.py) | La aplicación web completa (FastAPI). Gestiona la interfaz, la subida de archivos y los endpoints del dashboard. |
| [`src/ingestion/`](../src/ingestion/) | Motores que leen el Excel, detectan columnas y analizan los datos. |
| [`src/validation/`](../src/validation/) | Reglas de negocio que validan notas (0.0 a 5.0), pesos (100%) y separan errores. |
| [`sql/`](../sql/) | Scripts SQL que crean y transforman las tablas en las 4 capas de PostgreSQL. |
| [`scripts/run_pipeline.py`](../scripts/run_pipeline.py) | El motor que orquesta todo el proceso de inicio a fin en un solo comando. |
| [`data/errors/`](../data/errors/) | Reportes de auditoría donde se guardan las filas que contenían inconsistencias. |

---

## 5. Datos Reales de la Última Ejecución

* **Archivo procesado:** `colegio_test_completo.xlsx` (957 KB)
* **Tiempo total de ejecución:** **23.69 segundos**
* **Estudiantes evaluados:** **240** alumnos
* **Calificaciones procesadas:** **34,492** notas validadas
* **Promedio General del Colegio:** **3.59 / 5.0**
* **Tasa de Aprobación:** **79.35%** (20.65% reprobación)
* **Curso más destacado:** **11B** (Promedio 3.80 | 89.08% de aprobación)
* **Curso que requiere mayor refuerzo:** **7A** (Promedio 3.44 | 67.63% de aprobación)
