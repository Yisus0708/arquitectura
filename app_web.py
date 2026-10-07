"""
School Grades Data Platform - Modern Full-Stack Web Application.
Built with FastAPI, Uvicorn, Tailwind CSS, and Chart.js.
Supports:
- Real-time Excel (.xlsx) file uploads and automated pipeline processing
- Downloading pre-formatted Excel template
- Executive dashboard with Chart.js analytics
- Student report cards and academic rankings
- Data quality audit and error quarantine viewer

Run:
    python app_web.py
"""
import io
import sys
import webbrowser
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.utils.db import fetch_query, ensure_database_exists, ensure_schemas_exist
from src.utils.config import ERRORS_DATA_DIR, RAW_DATA_DIR
from src.ingestion.excel_handler import create_excel_template, process_uploaded_excel_file
from src.ingestion.generate_data import main as run_data_generation
from scripts.run_pipeline import execute_pipeline

app = FastAPI(
    title="Plataforma de Calificaciones Escolares",
    description="Sistema de Ingeniería de Datos y Analítica Académica",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/metrics", response_class=JSONResponse)
def get_metrics():
    """Returns top-level KPIs and chart data from gold schema."""
    try:
        final_grades = fetch_query("SELECT final_grade, is_approved FROM gold.final_grade_by_student_subject;")
        students = fetch_query("SELECT overall_average FROM gold.student_performance;")
        subjects = fetch_query("SELECT subject_name, course_name, average_final_grade, fail_rate_percentage, pass_rate_percentage FROM gold.subject_performance ORDER BY fail_rate_percentage DESC;")
        courses = fetch_query("SELECT course_name, course_gpa, overall_pass_rate_percentage FROM gold.course_performance ORDER BY course_gpa DESC;")
        eval_types = fetch_query("SELECT assessment_type, average_score, passing_count, failing_count FROM gold.assessment_type_performance ORDER BY average_score DESC;")
        top_bottom = fetch_query("SELECT cohort_group, ranking_position, student_id, full_name, course_name, overall_average FROM gold.top_bottom_students ORDER BY overall_average DESC;")

        total_students = len(students)
        avg_gpa = round(sum(s["overall_average"] for s in students) / total_students, 2) if total_students else 0.0
        total_evals = len(final_grades)
        total_approved = sum(1 for g in final_grades if g["is_approved"])
        pass_rate = round((total_approved / total_evals * 100), 2) if total_evals else 0.0

        return {
            "kpis": {
                "total_students": total_students,
                "average_gpa": avg_gpa,
                "pass_rate_percentage": pass_rate,
                "fail_rate_percentage": round(100.0 - pass_rate, 2) if total_evals else 0.0,
                "total_evaluations": total_evals,
                "total_subjects": len(subjects)
            },
            "subjects": subjects,
            "courses": courses,
            "eval_types": eval_types,
            "top_bottom": top_bottom
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/students", response_class=JSONResponse)
def get_students():
    """Returns students list and report cards."""
    try:
        students = fetch_query("""
            SELECT student_id, full_name, course_name, overall_average,
                   academic_ranking_overall, academic_ranking_in_course, performance_category
            FROM gold.student_performance
            ORDER BY academic_ranking_overall ASC;
        """)
        grades = fetch_query("""
            SELECT student_id, subject_name, department, final_grade, is_approved, approval_status
            FROM gold.final_grade_by_student_subject
            ORDER BY subject_name ASC;
        """)
        return {"students": students, "grades": grades}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/errors", response_class=JSONResponse)
def get_errors():
    """Returns quarantined errors with error_reason."""
    try:
        result = {}
        for ef in ERRORS_DATA_DIR.glob("*_errors.csv"):
            entity = ef.name.replace("_errors.csv", "")
            df = pd.read_csv(ef)
            result[entity] = {
                "count": len(df),
                "records": df.head(50).fillna("").to_dict(orient="records")
            }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download-template")
def download_excel_template():
    """Downloads structured Excel template (.xlsx)."""
    excel_bytes = create_excel_template()
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plantilla_calificaciones.xlsx"}
    )


@app.post("/api/upload-excel", response_class=JSONResponse)
async def upload_excel(file: UploadFile = File(...)):
    """Receives uploaded Excel, parses sheets, and runs data pipeline."""
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="El archivo debe ser en formato Excel (.xlsx o .xls)")

    try:
        content = await file.read()
        summary = process_uploaded_excel_file(content)
        return {
            "status": "success",
            "message": f"Archivo '{file.filename}' procesado y pipeline ejecutado exitosamente.",
            "details": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando archivo Excel: {str(e)}")


@app.post("/api/run-pipeline", response_class=JSONResponse)
def run_pipeline_api():
    """Triggers the full pipeline execution."""
    try:
        success = execute_pipeline()
        if success:
            return {"status": "success", "message": "Pipeline end-to-end ejecutado con éxito."}
        else:
            raise HTTPException(status_code=500, detail="La ejecución del pipeline reportó errores.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-synthetic", response_class=JSONResponse)
def generate_synthetic_api():
    """Regenerates synthetic data and runs pipeline."""
    try:
        run_data_generation()
        execute_pipeline()
        return {"status": "success", "message": "Datos sintéticos regenerados y pipeline ejecutado exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset-data", response_class=JSONResponse)
def reset_data_api():
    """Truncates all tables in PostgreSQL and clears errors, leaving the system in a clean blank state."""
    try:
        from src.utils.db import execute_query
        truncate_sql = """
            TRUNCATE TABLE raw.grades, raw.assessments, raw.students, raw.subjects, raw.courses CASCADE;
            TRUNCATE TABLE staging.grades, staging.assessments, staging.students, staging.subjects, staging.courses CASCADE;
            TRUNCATE TABLE silver.grades, silver.assessments, silver.students, silver.subjects, silver.courses CASCADE;
            TRUNCATE TABLE gold.fact_grades, gold.dim_student, gold.dim_subject, gold.dim_course, gold.dim_date CASCADE;
            TRUNCATE TABLE gold.final_grade_by_student_subject, gold.subject_performance, gold.student_performance,
                           gold.course_performance, gold.assessment_type_performance, gold.top_bottom_students,
                           gold.subjects_highest_failure CASCADE;
        """
        execute_query(truncate_sql)

        # Clear error files
        for f in ERRORS_DATA_DIR.glob("*_errors.csv"):
            if f.is_file():
                pd.DataFrame(columns=["error_reason"]).to_csv(f, index=False)

        return {"status": "success", "message": "Base de datos y archivos reiniciados con éxito. La plataforma está totalmente en blanco."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
def get_dashboard_html():
    """Serves the complete interactive HTML/Tailwind/Chart.js Single Page Dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plataforma de Calificaciones Escolares | Data Pipeline</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- FontAwesome CDN -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .active-tab {
            border-bottom: 3px solid #2563eb;
            color: #2563eb;
            font-weight: 600;
        }
    </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col font-sans">

    <!-- Top Navigation Bar -->
    <header class="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
            <div class="flex items-center space-x-3">
                <div class="bg-blue-600 text-white p-2 rounded-lg shadow">
                    <i class="fa-solid fa-graduation-cap text-xl"></i>
                </div>
                <div>
                    <h1 class="text-lg font-bold text-slate-900 leading-tight">School Grades Data Platform</h1>
                    <p class="text-xs text-slate-500">Pipeline Medallion &bull; PostgreSQL <span class="text-blue-600 font-semibold">school_dw</span></p>
                </div>
            </div>

            <!-- Action Buttons -->
            <div class="flex items-center space-x-3">
                <a href="/api/download-template" download="plantilla_calificaciones.xlsx"
                   class="inline-flex items-center px-3 py-1.5 border border-emerald-600 text-xs font-medium rounded-md text-emerald-700 bg-emerald-50 hover:bg-emerald-100 transition shadow-sm">
                    <i class="fa-solid fa-file-excel mr-1.5 text-emerald-600"></i> Descargar Plantilla
                </a>
                <button onclick="confirmResetData()"
                        class="inline-flex items-center px-3 py-1.5 border border-rose-300 text-xs font-medium rounded-md text-rose-700 bg-rose-50 hover:bg-rose-100 transition shadow-sm"
                        title="Vaciar base de datos y reiniciar la plataforma a blanco">
                    <i class="fa-solid fa-trash-can mr-1.5 text-rose-500"></i> Reiniciar a Blanco
                </button>
                <button onclick="triggerRunPipeline()"
                        class="inline-flex items-center px-3 py-1.5 bg-blue-600 text-xs font-medium rounded-md text-white hover:bg-blue-700 transition shadow-sm">
                    <i class="fa-solid fa-play mr-1.5"></i> Ejecutar Pipeline
                </button>
            </div>
        </div>
    </header>

    <!-- Main Navigation Tabs -->
    <div class="bg-white border-b border-slate-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <nav class="flex space-x-8 overflow-x-auto text-sm" id="navTabs">
                <button onclick="switchTab('resumen')" id="tab-resumen" class="py-4 px-1 text-slate-600 hover:text-blue-600 font-medium active-tab flex items-center">
                    <i class="fa-solid fa-chart-pie mr-2"></i> Resumen Ejecutivo
                </button>
                <button onclick="switchTab('materias')" id="tab-materias" class="py-4 px-1 text-slate-600 hover:text-blue-600 font-medium flex items-center">
                    <i class="fa-solid fa-book-open mr-2"></i> Rendimiento por Materia
                </button>
                <button onclick="switchTab('estudiantes')" id="tab-estudiantes" class="py-4 px-1 text-slate-600 hover:text-blue-600 font-medium flex items-center">
                    <i class="fa-solid fa-user-graduate mr-2"></i> Ficha de Estudiantes
                </button>
                <button onclick="switchTab('subir-excel')" id="tab-subir-excel" class="py-4 px-1 text-slate-600 hover:text-blue-600 font-medium flex items-center">
                    <i class="fa-solid fa-cloud-arrow-up mr-2 text-blue-600"></i> Subir Archivo Excel
                </button>
                <button onclick="switchTab('calidad')" id="tab-calidad" class="py-4 px-1 text-slate-600 hover:text-blue-600 font-medium flex items-center">
                    <i class="fa-solid fa-shield-halved mr-2 text-rose-500"></i> Errores de Calidad
                </button>
            </nav>
        </div>
    </div>

    <!-- Alert / Toast Container -->
    <div id="toastContainer" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4 hidden">
        <div id="toastContent" class="p-4 rounded-lg flex items-center justify-between shadow">
            <span id="toastMessage" class="text-sm font-medium"></span>
            <button onclick="closeToast()" class="text-slate-500 hover:text-slate-800 text-lg">&times;</button>
        </div>
    </div>

    <!-- Main Content Area -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full">

        <!-- ============================================================== -->
        <!-- TAB 1: RESUMEN EJECUTIVO -->
        <!-- ============================================================== -->
        <section id="section-resumen" class="space-y-6">
            <!-- Empty State Hero Banner -->
            <div id="emptyStateBanner" class="hidden bg-white border border-slate-200 rounded-2xl p-10 text-center shadow-sm">
                <div class="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 text-3xl shadow-inner">
                    <i class="fa-solid fa-file-excel"></i>
                </div>
                <h3 class="text-xl font-bold text-slate-900 mb-2">Plataforma en Blanco (Lista para Ingesta)</h3>
                <p class="text-slate-500 text-sm max-w-xl mx-auto mb-6">
                    No hay datos cargados en el Data Warehouse en este momento. Puedes subir cualquier archivo Excel (.xlsx) con los datos académicos de un colegio o descargar nuestra plantilla estructurada.
                </p>
                <div class="flex justify-center flex-wrap gap-3">
                    <button onclick="switchTab('subir-excel')" class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-xl shadow-md transition inline-flex items-center">
                        <i class="fa-solid fa-cloud-arrow-up mr-2"></i> Subir Archivo Excel
                    </button>
                    <a href="/api/download-template" download="plantilla_calificaciones.xlsx" class="px-5 py-2.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-semibold text-xs rounded-xl shadow-sm transition inline-flex items-center">
                        <i class="fa-solid fa-file-excel mr-2 text-emerald-600"></i> Descargar Plantilla
                    </a>
                    <button onclick="generateSynthetic()" class="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs rounded-xl shadow-md transition inline-flex items-center">
                        <i class="fa-solid fa-dice mr-2"></i> Generar Datos Demo
                    </button>
                </div>
            </div>

            <!-- Content Area (KPIs + Charts + Tables) -->
            <div id="dataContentArea" class="space-y-6">
                <!-- KPI Cards -->
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                    <div>
                        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Estudiantes Activos</p>
                        <h3 class="text-2xl font-bold text-slate-900 mt-1" id="kpi-students">--</h3>
                        <p class="text-xs text-emerald-600 mt-1"><i class="fa-solid fa-check"></i> 100% Matriculados</p>
                    </div>
                    <div class="w-12 h-12 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center text-xl">
                        <i class="fa-solid fa-users"></i>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                    <div>
                        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Promedio General (GPA)</p>
                        <h3 class="text-2xl font-bold text-slate-900 mt-1" id="kpi-gpa">--</h3>
                        <p class="text-xs text-slate-500 mt-1">Escala 0.0 - 5.0</p>
                    </div>
                    <div class="w-12 h-12 bg-amber-50 text-amber-600 rounded-lg flex items-center justify-center text-xl">
                        <i class="fa-solid fa-star"></i>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                    <div>
                        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Tasa de Aprobación</p>
                        <h3 class="text-2xl font-bold text-slate-900 mt-1" id="kpi-pass-rate">--</h3>
                        <p class="text-xs text-slate-500 mt-1" id="kpi-fail-rate">--</p>
                    </div>
                    <div class="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center text-xl">
                        <i class="fa-solid fa-award"></i>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                    <div>
                        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Asignaturas Evaluadas</p>
                        <h3 class="text-2xl font-bold text-slate-900 mt-1" id="kpi-subjects">--</h3>
                        <p class="text-xs text-blue-600 mt-1">Ponderación 100%</p>
                    </div>
                    <div class="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-lg flex items-center justify-center text-xl">
                        <i class="fa-solid fa-layer-group"></i>
                    </div>
                </div>
            </div>

            <!-- Charts Row -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Bar Chart: GPA by Course -->
                <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                    <h3 class="font-bold text-slate-900 text-sm mb-4 flex items-center">
                        <i class="fa-solid fa-chart-column mr-2 text-blue-600"></i> Promedio General por Curso / Cohorte
                    </h3>
                    <div class="h-64">
                        <canvas id="chartCourses"></canvas>
                    </div>
                </div>

                <!-- Doughnut Chart: Pass Rate vs Fail Rate -->
                <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                    <h3 class="font-bold text-slate-900 text-sm mb-4 flex items-center">
                        <i class="fa-solid fa-chart-pie mr-2 text-emerald-600"></i> Distribución General: Aprobados vs Reprobados
                    </h3>
                    <div class="h-64 flex justify-center">
                        <canvas id="chartApproval"></canvas>
                    </div>
                </div>
            </div>

            <!-- Top 5 Honor vs Bottom 5 Reinforcement -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                    <h3 class="font-bold text-slate-900 text-sm mb-3 flex items-center text-emerald-700">
                        <i class="fa-solid fa-medal mr-2"></i> 🏆 Cuadro de Honor (Top 5 Estudiantes)
                    </h3>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs text-slate-600">
                            <thead class="bg-slate-50 text-slate-700 uppercase font-semibold">
                                <tr>
                                    <th class="py-2.5 px-3">Puesto</th>
                                    <th class="py-2.5 px-3">Estudiante</th>
                                    <th class="py-2.5 px-3">Curso</th>
                                    <th class="py-2.5 px-3 text-right">Promedio</th>
                                </tr>
                            </thead>
                            <tbody id="topStudentsTable" class="divide-y divide-slate-100 font-medium"></tbody>
                        </table>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                    <h3 class="font-bold text-slate-900 text-sm mb-3 flex items-center text-rose-700">
                        <i class="fa-solid fa-triangle-exclamation mr-2"></i> ⚠️ Plan de Refuerzo Prioritario (Bottom 5)
                    </h3>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs text-slate-600">
                            <thead class="bg-slate-50 text-slate-700 uppercase font-semibold">
                                <tr>
                                    <th class="py-2.5 px-3">Puesto</th>
                                    <th class="py-2.5 px-3">Estudiante</th>
                                    <th class="py-2.5 px-3">Curso</th>
                                    <th class="py-2.5 px-3 text-right">Promedio</th>
                                </tr>
                            </thead>
                            <tbody id="bottomStudentsTable" class="divide-y divide-slate-100 font-medium"></tbody>
                        </table>
                    </div>
                </div>
            </div>
            </div>
        </section>

        <!-- ============================================================== -->
        <!-- TAB 2: RENDIMIENTO POR MATERIA -->
        <!-- ============================================================== -->
        <section id="section-materias" class="space-y-6 hidden">
            <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-3">
                    <div>
                        <h2 class="text-base font-bold text-slate-900">Rendimiento por Materia</h2>
                        <p class="text-xs text-slate-500">Métricas consolidadas de aprobación y promedios por asignatura</p>
                    </div>
                    <div class="w-full sm:w-64">
                        <input type="text" id="filterSubjectInput" onkeyup="filterSubjectsTable()"
                               placeholder="Buscar materia o curso..."
                               class="w-full text-xs px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500">
                    </div>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs text-slate-600" id="subjectsTable">
                        <thead class="bg-slate-50 text-slate-700 uppercase font-semibold">
                            <tr>
                                <th class="py-3 px-3">Asignatura</th>
                                <th class="py-3 px-3">Curso</th>
                                <th class="py-3 px-3">Área / Depto</th>
                                <th class="py-3 px-3 text-center">Alumnos</th>
                                <th class="py-3 px-3 text-center">Promedio Final</th>
                                <th class="py-3 px-3 text-center">% Aprobados</th>
                                <th class="py-3 px-3 text-center">% Reprobados</th>
                            </tr>
                        </thead>
                        <tbody id="subjectsTableBody" class="divide-y divide-slate-100"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ============================================================== -->
        <!-- TAB 3: FICHA DE ESTUDIANTES -->
        <!-- ============================================================== -->
        <section id="section-estudiantes" class="space-y-6 hidden">
            <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4">
                    <div>
                        <h2 class="text-base font-bold text-slate-900">Boletín Individual del Estudiante</h2>
                        <p class="text-xs text-slate-500">Selecciona o busca un estudiante para consultar su estado académico</p>
                    </div>
                    <div class="w-full sm:w-80">
                        <select id="studentSelect" onchange="renderStudentCard()"
                                class="w-full text-xs px-3 py-2 border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium">
                        </select>
                    </div>
                </div>

                <!-- Student Summary Badges -->
                <div id="studentCardContainer" class="hidden">
                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-lg border border-slate-200 mb-6 text-xs">
                        <div>
                            <span class="text-slate-500 block">Código:</span>
                            <span class="font-bold text-slate-900 text-sm" id="st-id">--</span>
                        </div>
                        <div>
                            <span class="text-slate-500 block">Curso:</span>
                            <span class="font-bold text-slate-900 text-sm" id="st-course">--</span>
                        </div>
                        <div>
                            <span class="text-slate-500 block">Promedio GPA:</span>
                            <span class="font-bold text-blue-600 text-sm" id="st-gpa">--</span>
                        </div>
                        <div>
                            <span class="text-slate-500 block">Puesto en Ranking:</span>
                            <span class="font-bold text-emerald-700 text-sm" id="st-rank">--</span>
                        </div>
                    </div>

                    <h4 class="font-bold text-slate-900 text-xs uppercase tracking-wider mb-3">Calificaciones Definitivas Ponderadas</h4>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs text-slate-600">
                            <thead class="bg-slate-100 text-slate-700 uppercase font-semibold">
                                <tr>
                                    <th class="py-2.5 px-3">Materia</th>
                                    <th class="py-2.5 px-3">Departamento</th>
                                    <th class="py-2.5 px-3 text-center">Nota Definitiva</th>
                                    <th class="py-2.5 px-3 text-center">Estado</th>
                                </tr>
                            </thead>
                            <tbody id="studentGradesBody" class="divide-y divide-slate-100"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </section>

        <!-- ============================================================== -->
        <!-- TAB 4: SUBIR ARCHIVO EXCEL (FUNCIONALIDAD CRÍTICA) -->
        <!-- ============================================================== -->
        <section id="section-subir-excel" class="space-y-6 hidden">
            <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm max-w-3xl mx-auto">
                <div class="text-center mb-6">
                    <div class="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto text-2xl mb-3">
                        <i class="fa-solid fa-file-excel"></i>
                    </div>
                    <h2 class="text-lg font-bold text-slate-900">Ingesta Directa de Archivo Excel (.xlsx)</h2>
                    <p class="text-xs text-slate-500 max-w-md mx-auto mt-1">
                        Carga tu archivo de notas. El pipeline procesará las hojas de cálculo, validará contratos, enviará registros erróneos a cuarentena y actualizará la base de datos PostgreSQL en tiempo real.
                    </p>
                </div>

                <!-- Template Download Card -->
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 flex items-center justify-between">
                    <div class="flex items-center space-x-3">
                        <i class="fa-solid fa-circle-info text-blue-600 text-xl"></i>
                        <div class="text-xs text-blue-800">
                            <p class="font-semibold">¿Necesitas el formato correcto?</p>
                            <p>Descarga la plantilla con las pestañas requeridas: <code>cursos</code>, <code>materias</code>, <code>estudiantes</code>, <code>evaluaciones</code>, <code>calificaciones</code>.</p>
                        </div>
                    </div>
                    <a href="/api/download-template" download="plantilla_calificaciones.xlsx"
                       class="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 transition shrink-0 ml-3 shadow-sm">
                        <i class="fa-solid fa-download mr-1"></i> Descargar
                    </a>
                </div>

                <!-- Drag & Drop / File Input Box -->
                <form id="excelUploadForm" onsubmit="handleExcelUpload(event)">
                    <div class="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:border-blue-500 transition cursor-pointer bg-slate-50"
                         onclick="document.getElementById('excelFileInput').click()">
                        <i class="fa-solid fa-cloud-arrow-up text-4xl text-slate-400 mb-2"></i>
                        <p class="text-sm font-semibold text-slate-700" id="fileLabel">Haz clic o arrastra aquí tu archivo Excel (.xlsx)</p>
                        <p class="text-xs text-slate-400 mt-1">Formatos soportados: .xlsx, .xls (Máximo 25MB)</p>
                        <input type="file" id="excelFileInput" accept=".xlsx,.xls" class="hidden" onchange="onFileSelected(this)">
                    </div>

                    <div class="mt-6 flex justify-end">
                        <button type="submit" id="btnUploadSubmit" disabled
                                class="inline-flex items-center px-5 py-2.5 bg-emerald-600 text-white text-xs font-semibold rounded-lg shadow hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition">
                            <i class="fa-solid fa-upload mr-2"></i> Procesar y Ejecutar Pipeline
                        </button>
                    </div>
                </form>

                <!-- Processing Spinner -->
                <div id="uploadLoading" class="hidden mt-6 text-center py-4">
                    <i class="fa-solid fa-spinner fa-spin text-2xl text-blue-600"></i>
                    <p class="text-xs font-medium text-slate-600 mt-2">Validando datos y transformando en PostgreSQL...</p>
                </div>

                <!-- Result Card -->
                <div id="uploadResultCard" class="hidden mt-6 p-4 rounded-lg border text-xs"></div>
            </div>
        </section>

        <!-- ============================================================== -->
        <!-- TAB 5: AUDITORÍA Y CALIDAD (DATA ERRORS) -->
        <!-- ============================================================== -->
        <section id="section-calidad" class="space-y-6 hidden">
            <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h2 class="text-base font-bold text-slate-900 flex items-center">
                            <i class="fa-solid fa-shield-halved text-rose-500 mr-2"></i> Cuarentena de Calidad (data/errors/)
                        </h2>
                        <p class="text-xs text-slate-500">Registros anómalos rechazados con su motivo exacto. El raw original no fue alterado.</p>
                    </div>
                    <span class="px-2.5 py-1 bg-rose-100 text-rose-800 text-xs font-bold rounded-full" id="totalErrorsBadge">-- Errores</span>
                </div>

                <div class="flex space-x-2 border-b border-slate-200 mb-4 overflow-x-auto text-xs" id="errorSubTabs">
                    <!-- Populated via JS -->
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs text-slate-600" id="errorsTable">
                        <thead class="bg-rose-50 text-rose-900 uppercase font-semibold" id="errorsTableHeader">
                            <!-- Populated via JS -->
                        </thead>
                        <tbody id="errorsTableBody" class="divide-y divide-slate-100"></tbody>
                    </table>
                </div>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer class="bg-white border-t border-slate-200 py-4 mt-auto text-center text-xs text-slate-400">
        School Grades Data Engineering Pipeline &bull; Python, PostgreSQL 18, FastAPI, Chart.js &bull; 100% Idempotente
    </footer>

    <!-- JavaScript Application Logic -->
    <script>
        let currentData = null;
        let studentsData = null;
        let errorsData = null;
        let coursesChart = null;
        let approvalChart = null;

        document.addEventListener("DOMContentLoaded", () => {
            loadDashboardData();
        });

        async function loadDashboardData() {
            try {
                const res = await fetch("/api/metrics");
                if (!res.ok) throw new Error("Error cargando métricas");
                currentData = await res.json();
                renderMetrics(currentData);
                renderCharts(currentData);
                renderSubjects(currentData.subjects);
            } catch (err) {
                showToast("Error conectando a la API: " + err.message, "error");
            }
        }

        function renderMetrics(data) {
            const kpi = data.kpis;
            const emptyBanner = document.getElementById("emptyStateBanner");
            const dataContent = document.getElementById("dataContentArea");

            if (!kpi || kpi.total_students === 0) {
                if (emptyBanner) emptyBanner.classList.remove("hidden");
                if (dataContent) dataContent.classList.add("hidden");
                return;
            } else {
                if (emptyBanner) emptyBanner.classList.add("hidden");
                if (dataContent) dataContent.classList.remove("hidden");
            }

            document.getElementById("kpi-students").innerText = kpi.total_students;
            document.getElementById("kpi-gpa").innerText = kpi.average_gpa + " / 5.0";
            document.getElementById("kpi-pass-rate").innerText = kpi.pass_rate_percentage + "%";
            document.getElementById("kpi-fail-rate").innerText = kpi.fail_rate_percentage + "% Reprobados";
            document.getElementById("kpi-subjects").innerText = kpi.total_subjects;

            // Render Top & Bottom Tables
            const topTbody = document.getElementById("topStudentsTable");
            const bottomTbody = document.getElementById("bottomStudentsTable");
            topTbody.innerHTML = "";
            bottomTbody.innerHTML = "";

            if (data.top_bottom && data.top_bottom.length > 0) {
                data.top_bottom.forEach(item => {
                    const isTop = item.cohort_group.includes("Top");
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td class="py-2 px-3 font-bold ${isTop ? 'text-emerald-600' : 'text-rose-600'}">#${item.ranking_position}</td>
                        <td class="py-2 px-3 font-semibold text-slate-800">${item.full_name}</td>
                        <td class="py-2 px-3">${item.course_name}</td>
                        <td class="py-2 px-3 text-right font-bold">${Number(item.overall_average).toFixed(2)}</td>
                    `;
                    if (isTop) topTbody.appendChild(row);
                    else bottomTbody.appendChild(row);
                });
            }
        }

        function renderCharts(data) {
            if (!data.kpis || data.kpis.total_students === 0 || !data.courses || data.courses.length === 0) {
                if (coursesChart) { coursesChart.destroy(); coursesChart = null; }
                if (approvalChart) { approvalChart.destroy(); approvalChart = null; }
                return;
            }

            // 1. Courses GPA Chart
            const ctxCourses = document.getElementById("chartCourses").getContext("2d");
            const courseLabels = data.courses.map(c => c.course_name);
            const courseGpa = data.courses.map(c => Number(c.course_gpa));

            if (coursesChart) coursesChart.destroy();
            coursesChart = new Chart(ctxCourses, {
                type: 'bar',
                data: {
                    labels: courseLabels,
                    datasets: [{
                        label: 'Promedio General (0.0 - 5.0)',
                        data: courseGpa,
                        backgroundColor: '#3b82f6',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { min: 0, max: 5.0 }
                    }
                }
            });

            // 2. Approval Doughnut Chart
            const ctxAppr = document.getElementById("chartApproval").getContext("2d");
            if (approvalChart) approvalChart.destroy();
            approvalChart = new Chart(ctxAppr, {
                type: 'doughnut',
                data: {
                    labels: ['% Aprobados', '% Reprobados'],
                    datasets: [{
                        data: [data.kpis.pass_rate_percentage, data.kpis.fail_rate_percentage],
                        backgroundColor: ['#10b981', '#ef4444'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }

        function renderSubjects(subjects) {
            const tbody = document.getElementById("subjectsTableBody");
            tbody.innerHTML = "";
            if (!subjects || subjects.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400 font-medium">No hay materias cargadas. Sube un archivo Excel para comenzar.</td></tr>`;
                return;
            }
            subjects.forEach(s => {
                const tr = document.createElement("tr");
                const failRate = Number(s.fail_rate_percentage);
                const isCritical = failRate >= 30.0;
                tr.innerHTML = `
                    <td class="py-2.5 px-3 font-semibold text-slate-900">${s.subject_name}</td>
                    <td class="py-2.5 px-3">${s.course_name}</td>
                    <td class="py-2.5 px-3 text-slate-500">${s.department}</td>
                    <td class="py-2.5 px-3 text-center">${s.enrolled_students}</td>
                    <td class="py-2.5 px-3 text-center font-bold">${Number(s.average_final_grade).toFixed(2)}</td>
                    <td class="py-2.5 px-3 text-center text-emerald-600 font-semibold">${Number(s.pass_rate_percentage).toFixed(1)}%</td>
                    <td class="py-2.5 px-3 text-center ${isCritical ? 'text-rose-600 font-bold' : 'text-slate-600'}">${failRate.toFixed(1)}%</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function filterSubjectsTable() {
            const query = document.getElementById("filterSubjectInput").value.toLowerCase();
            const rows = document.querySelectorAll("#subjectsTableBody tr");
            rows.forEach(r => {
                const text = r.innerText.toLowerCase();
                r.style.display = text.includes(query) ? "" : "none";
            });
        }

        async function switchTab(tabName) {
            document.querySelectorAll("#navTabs button").forEach(b => b.classList.remove("active-tab"));
            document.getElementById("tab-" + tabName).classList.add("active-tab");

            const sections = ["resumen", "materias", "estudiantes", "subir-excel", "calidad"];
            sections.forEach(s => {
                document.getElementById("section-" + s).classList.add("hidden");
            });
            document.getElementById("section-" + tabName).classList.remove("hidden");

            if (tabName === "estudiantes" && !studentsData) {
                loadStudentsData();
            } else if (tabName === "calidad" && !errorsData) {
                loadErrorsData();
            }
        }

        async function loadStudentsData() {
            try {
                const res = await fetch("/api/students");
                studentsData = await res.json();
                const select = document.getElementById("studentSelect");
                select.innerHTML = '<option value="">-- Selecciona un Estudiante --</option>';
                studentsData.students.forEach(st => {
                    const opt = document.createElement("option");
                    opt.value = st.student_id;
                    opt.innerText = `${st.full_name} (${st.course_name}) - Prom: ${Number(st.overall_average).toFixed(2)}`;
                    select.appendChild(opt);
                });
            } catch (err) {
                showToast("Error cargando estudiantes: " + err.message, "error");
            }
        }

        function renderStudentCard() {
            const stId = document.getElementById("studentSelect").value;
            const container = document.getElementById("studentCardContainer");
            if (!stId) {
                container.classList.add("hidden");
                return;
            }

            const student = studentsData.students.find(s => s.student_id === stId);
            if (!student) return;

            document.getElementById("st-id").innerText = student.student_id;
            document.getElementById("st-course").innerText = student.course_name;
            document.getElementById("st-gpa").innerText = Number(student.overall_average).toFixed(2) + " / 5.0";
            document.getElementById("st-rank").innerText = `#${student.academic_ranking_overall} Colegio (#${student.academic_ranking_in_course} Salón)`;

            const studentGrades = studentsData.grades.filter(g => g.student_id === stId);
            const tbody = document.getElementById("studentGradesBody");
            tbody.innerHTML = "";
            studentGrades.forEach(g => {
                const tr = document.createElement("tr");
                const isPassed = g.is_approved;
                tr.innerHTML = `
                    <td class="py-2.5 px-3 font-semibold text-slate-900">${g.subject_name}</td>
                    <td class="py-2.5 px-3 text-slate-500">${g.department}</td>
                    <td class="py-2.5 px-3 text-center font-bold">${Number(g.final_grade).toFixed(2)}</td>
                    <td class="py-2.5 px-3 text-center">
                        <span class="px-2 py-0.5 rounded text-[11px] font-bold ${isPassed ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}">
                            ${g.approval_status}
                        </span>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            container.classList.remove("hidden");
        }

        async function loadErrorsData() {
            try {
                const res = await fetch("/api/errors");
                errorsData = await res.json();
                renderErrorsTab();
            } catch (err) {
                showToast("Error cargando registros en cuarentena: " + err.message, "error");
            }
        }

        function renderErrorsTab() {
            let total = 0;
            const subTabsContainer = document.getElementById("errorSubTabs");
            subTabsContainer.innerHTML = "";

            const entities = Object.keys(errorsData);
            entities.forEach((entity, idx) => {
                total += errorsData[entity].count;
                const btn = document.createElement("button");
                btn.className = `py-2 px-3 font-medium capitalize rounded-t ${idx === 0 ? 'bg-rose-50 text-rose-700 font-bold border-b-2 border-rose-600' : 'text-slate-600 hover:text-slate-900'}`;
                btn.innerText = `${entity} (${errorsData[entity].count})`;
                btn.onclick = () => selectErrorEntity(entity, btn);
                subTabsContainer.appendChild(btn);
            });

            document.getElementById("totalErrorsBadge").innerText = `${total} Registros en Cuarentena`;

            if (entities.length > 0) {
                displayEntityErrors(entities[0]);
            }
        }

        function selectErrorEntity(entity, clickedBtn) {
            document.querySelectorAll("#errorSubTabs button").forEach(b => {
                b.className = "py-2 px-3 font-medium capitalize text-slate-600 hover:text-slate-900";
            });
            clickedBtn.className = "py-2 px-3 font-medium capitalize bg-rose-50 text-rose-700 font-bold border-b-2 border-rose-600";
            displayEntityErrors(entity);
        }

        function displayEntityErrors(entity) {
            const data = errorsData[entity];
            const thead = document.getElementById("errorsTableHeader");
            const tbody = document.getElementById("errorsTableBody");
            thead.innerHTML = "";
            tbody.innerHTML = "";

            if (!data.records || data.records.length === 0) {
                tbody.innerHTML = `<tr><td class="py-4 text-center text-slate-400" colspan="10">No hay registros con error en esta entidad.</td></tr>`;
                return;
            }

            const columns = Object.keys(data.records[0]);
            const headerRow = document.createElement("tr");
            columns.forEach(col => {
                const th = document.createElement("th");
                th.className = "py-2.5 px-3";
                th.innerText = col.replace("_", " ");
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);

            data.records.forEach(row => {
                const tr = document.createElement("tr");
                columns.forEach(col => {
                    const td = document.createElement("td");
                    td.className = "py-2 px-3";
                    if (col === "error_reason") {
                        td.innerHTML = `<span class="px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-semibold text-[11px]">${row[col]}</span>`;
                    } else {
                        td.innerText = row[col];
                    }
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
        }

        function onFileSelected(input) {
            if (input.files && input.files[0]) {
                const f = input.files[0];
                document.getElementById("fileLabel").innerText = `Archivo seleccionado: ${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
                document.getElementById("btnUploadSubmit").disabled = false;
            }
        }

        async function handleExcelUpload(event) {
            event.preventDefault();
            const input = document.getElementById("excelFileInput");
            if (!input.files || !input.files[0]) {
                showToast("Por favor selecciona un archivo Excel primero.", "error");
                return;
            }

            const formData = new FormData();
            formData.append("file", input.files[0]);

            const submitBtn = document.getElementById("btnUploadSubmit");
            const loader = document.getElementById("uploadLoading");
            const resCard = document.getElementById("uploadResultCard");

            submitBtn.disabled = true;
            loader.classList.remove("hidden");
            resCard.classList.add("hidden");

            try {
                const res = await fetch("/api/upload-excel", {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();
                loader.classList.add("hidden");
                submitBtn.disabled = false;

                if (!res.ok) {
                    throw new Error(data.detail || "Error en el procesamiento");
                }

                resCard.className = "mt-6 p-4 rounded-lg border bg-emerald-50 border-emerald-300 text-emerald-900";
                resCard.innerHTML = `
                    <div class="flex items-center space-x-2 font-bold mb-2">
                        <i class="fa-solid fa-circle-check text-emerald-600 text-base"></i>
                        <span>¡Archivo Excel Procesado y Pipeline Ejecutado con Éxito!</span>
                    </div>
                    <p class="mb-2">Se leyeron e importaron las siguientes hojas: <strong>${data.details.sheets_imported.join(", ")}</strong></p>
                    <p class="text-xs text-emerald-700">Las métricas analíticas en PostgreSQL (school_dw) han sido recalculadas en tiempo real.</p>
                `;
                resCard.classList.remove("hidden");

                showToast("¡Archivo Excel procesado con éxito!", "success");
                // Reload dashboard data
                loadDashboardData();
                studentsData = null;
                errorsData = null;
            } catch (err) {
                loader.classList.add("hidden");
                submitBtn.disabled = false;
                resCard.className = "mt-6 p-4 rounded-lg border bg-rose-50 border-rose-300 text-rose-900";
                resCard.innerHTML = `
                    <div class="flex items-center space-x-2 font-bold mb-1">
                        <i class="fa-solid fa-circle-xmark text-rose-600 text-base"></i>
                        <span>Error al procesar el archivo Excel</span>
                    </div>
                    <p>${err.message}</p>
                `;
                resCard.classList.remove("hidden");
                showToast("Error: " + err.message, "error");
            }
        }

        async function triggerRunPipeline() {
            showToast("Ejecutando pipeline end-to-end...", "info");
            try {
                const res = await fetch("/api/run-pipeline", { method: "POST" });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail);
                showToast("¡Pipeline completado exitosamente!", "success");
                loadDashboardData();
                studentsData = null;
                errorsData = null;
            } catch (err) {
                showToast("Fallo al ejecutar pipeline: " + err.message, "error");
            }
        }

        async function confirmResetData() {
            if (!confirm("¿Deseas vaciar la base de datos para iniciar en blanco? Todas las tablas de raw, staging, silver y gold se vaciarán.")) {
                return;
            }
            showToast("Vaciando base de datos y dejando plataforma en blanco...", "info");
            try {
                const res = await fetch("/api/reset-data", { method: "POST" });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail);
                showToast(data.message, "success");
                loadDashboardData();
                studentsData = null;
                errorsData = null;
            } catch (e) {
                showToast("Error al reiniciar: " + e.message, "error");
            }
        }

        async function generateSynthetic() {
            showToast("Generando datos sintéticos de demostración...", "info");
            try {
                const res = await fetch("/api/generate-synthetic", { method: "POST" });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail);
                showToast(data.message, "success");
                loadDashboardData();
                studentsData = null;
                errorsData = null;
            } catch (e) {
                showToast("Error generando datos: " + e.message, "error");
            }
        }

        function showToast(msg, type = "info") {
            const c = document.getElementById("toastContainer");
            const content = document.getElementById("toastContent");
            const m = document.getElementById("toastMessage");

            m.innerText = msg;
            content.className = "p-4 rounded-lg flex items-center justify-between shadow " +
                (type === "success" ? "bg-emerald-100 text-emerald-900 border border-emerald-300" :
                 type === "error" ? "bg-rose-100 text-rose-900 border border-rose-300" :
                 "bg-blue-100 text-blue-900 border border-blue-300");

            c.classList.remove("hidden");
            setTimeout(() => { c.classList.add("hidden"); }, 5000);
        }

        function closeToast() {
            document.getElementById("toastContainer").classList.add("hidden");
        }
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    ensure_database_exists()
    ensure_schemas_exist()
    print("=" * 70)
    print("[SERVER] INICIANDO SERVIDOR WEB DE CALIFICACIONES (FASTAPI + UVICORN)")
    print("=" * 70)
    print("[URL] Abre en tu navegador: http://localhost:8000")
    print("[INFO] Funcionalidades: Dashboard, Subida de Excel, Plantilla, Reportes")
    print("=" * 70)
    uvicorn.run("app_web:app", host="127.0.0.1", port=8000, reload=False)
