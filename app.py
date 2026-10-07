"""
School Grades Analytics & Data Quality Dashboard.
Interactive Web Interface powered by Streamlit and PostgreSQL (school_dw).

Run:
    streamlit run app.py
"""
import sys
from pathlib import Path
import pandas as pd
import streamlit as st

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.utils.db import fetch_query
from src.utils.config import ERRORS_DATA_DIR, RAW_DATA_DIR

st.set_page_config(
    page_title="Sistema de Calificaciones | Data Pipeline",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .badge-approved {
        background-color: #d4edda;
        color: #155724;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-failed {
        background-color: #f8d7da;
        color: #721c24;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_gold_data():
    """Loads datasets from PostgreSQL gold schema."""
    final_grades = pd.DataFrame(fetch_query("""
        SELECT student_id, full_name, course_name, subject_name, department, final_grade, is_approved, approval_status
        FROM gold.final_grade_by_student_subject;
    """))

    subjects = pd.DataFrame(fetch_query("""
        SELECT subject_id, subject_name, course_name, department, enrolled_students, average_final_grade,
               min_final_grade, max_final_grade, approved_count, failed_count, pass_rate_percentage, fail_rate_percentage
        FROM gold.subject_performance
        ORDER BY fail_rate_percentage DESC;
    """))

    students = pd.DataFrame(fetch_query("""
        SELECT student_id, full_name, course_name, subjects_enrolled, subjects_passed, subjects_failed,
               overall_average, lowest_subject_grade, highest_subject_grade, academic_ranking_overall,
               academic_ranking_in_course, performance_category
        FROM gold.student_performance
        ORDER BY academic_ranking_overall ASC;
    """))

    courses = pd.DataFrame(fetch_query("""
        SELECT course_id, course_name, grade_level, academic_year, total_students, course_gpa,
               total_subjects_passed, total_subjects_failed, overall_pass_rate_percentage, overall_fail_rate_percentage
        FROM gold.course_performance
        ORDER BY course_gpa DESC;
    """))

    eval_types = pd.DataFrame(fetch_query("""
        SELECT assessment_type, total_evaluations_taken, average_score, min_score, max_score,
               passing_count, failing_count, pass_rate_percentage
        FROM gold.assessment_type_performance
        ORDER BY average_score DESC;
    """))

    top_bottom = pd.DataFrame(fetch_query("""
        SELECT cohort_group, ranking_position, student_id, full_name, course_name, overall_average
        FROM gold.top_bottom_students;
    """))

    return final_grades, subjects, students, courses, eval_types, top_bottom


# Sidebar Navigation
st.sidebar.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=80)
st.sidebar.title("Sistema de Calificaciones")
st.sidebar.caption("Pipeline Medallion (PostgreSQL `school_dw`)")

menu = st.sidebar.radio(
    "Selecciona la Vista:",
    [
        "🏛️ Resumen Ejecutivo",
        "📚 Rendimiento por Materia",
        "👨‍🎓 Ficha de Estudiantes",
        "🏫 Comparativa de Cursos",
        "📤 Subir Archivo Excel (.xlsx)",
        "🛡️ Auditoría y Calidad (Data Errors)"
    ]
)

try:
    final_grades_df, subjects_df, students_df, courses_df, eval_types_df, top_bottom_df = load_gold_data()
    db_connected = True
except Exception as e:
    st.error(f"Error conectando a la base de datos PostgreSQL: {e}")
    st.stop()


# -----------------------------------------------------------------------------
# 1. RESUMEN EJECUTIVO
# -----------------------------------------------------------------------------
if menu == "🏛️ Resumen Ejecutivo":
    st.title("🏛️ Tablero de Mando Ejecutivo - Colegio")
    st.markdown("Métricas consolidadas de rendimiento académico en la capa **Gold**.")

    col1, col2, col3, col4 = st.columns(4)
    total_students = len(students_df)
    colegio_gpa = round(students_df["overall_average"].mean(), 2)
    total_evals = len(final_grades_df)
    overall_pass_rate = round((final_grades_df["is_approved"].sum() / total_evals) * 100, 2)

    with col1:
        st.metric("Total Estudiantes Activos", total_students, "100% Cobertura")
    with col2:
        st.metric("Promedio General (GPA)", f"{colegio_gpa} / 5.0", "Escala 0.0 - 5.0")
    with col3:
        st.metric("Tasa General de Aprobación", f"{overall_pass_rate}%", f"{round(100 - overall_pass_rate, 2)}% Reprobados", delta_color="normal")
    with col4:
        st.metric("Asignaturas Evaluadas", len(subjects_df), "100% Ponderado")

    st.divider()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🏆 Cuadro de Honor (Top 5 Estudiantes)")
        top_5 = top_bottom_df[top_bottom_df["cohort_group"].str.contains("Top")][["ranking_position", "student_id", "full_name", "course_name", "overall_average"]]
        st.dataframe(top_5, use_container_width=True, hide_index=True)

        st.subheader("⚠️ Plan de Refuerzo Prioritario (Bottom 5)")
        bottom_5 = top_bottom_df[top_bottom_df["cohort_group"].str.contains("Bottom")][["ranking_position", "student_id", "full_name", "course_name", "overall_average"]]
        st.dataframe(bottom_5, use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("📊 Rendimiento por Tipo de Evaluación")
        st.bar_chart(
            data=eval_types_df.set_index("assessment_type")[["average_score"]],
            color="#4CAF50"
        )

        st.subheader("📌 Promedio General por Curso")
        st.bar_chart(
            data=courses_df.set_index("course_name")[["course_gpa"]],
            color="#2196F3"
        )


# -----------------------------------------------------------------------------
# 2. RENDIMIENTO POR MATERIA
# -----------------------------------------------------------------------------
elif menu == "📚 Rendimiento por Materia":
    st.title("📚 Rendimiento Académico por Asignatura")
    st.markdown("Análisis granular por materia, promedio final y porcentaje de aprobación/reprobación.")

    depts = ["Todos"] + list(subjects_df["department"].unique())
    selected_dept = st.selectbox("Filtrar por Departamento Pedagógico:", depts)

    filtered_subjects = subjects_df if selected_dept == "Todos" else subjects_df[subjects_df["department"] == selected_dept]

    st.dataframe(
        filtered_subjects[[
            "subject_name", "course_name", "department", "enrolled_students",
            "average_final_grade", "pass_rate_percentage", "fail_rate_percentage"
        ]].rename(columns={
            "subject_name": "Asignatura",
            "course_name": "Curso",
            "department": "Departamento",
            "enrolled_students": "Estudiantes",
            "average_final_grade": "Promedio Final",
            "pass_rate_percentage": "% Aprobados",
            "fail_rate_percentage": "% Reprobados"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("🚨 Asignaturas con Mayor Tasa de Pérdida")
    top_failure = subjects_df.head(6)[["subject_name", "course_name", "fail_rate_percentage"]].set_index("subject_name")
    st.bar_chart(top_failure, color="#FF5722")


# -----------------------------------------------------------------------------
# 3. FICHA DE ESTUDIANTES
# -----------------------------------------------------------------------------
elif menu == "👨‍🎓 Ficha de Estudiantes":
    st.title("👨‍🎓 Consulta y Ficha Académica del Estudiante")
    st.markdown("Detalle individual de notas definitivas ponderadas y posición en el ranking.")

    student_names = students_df["full_name"].tolist()
    selected_student = st.selectbox("Selecciona o busca un estudiante:", student_names)

    student_data = students_df[students_df["full_name"] == selected_student].iloc[0]
    st_id = student_data["student_id"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Código", st_id)
    with col2:
        st.metric("Curso", student_data["course_name"])
    with col3:
        st.metric("Promedio Acumulado (GPA)", f"{student_data['overall_average']} / 5.0")
    with col4:
        st.metric("Puesto en Ranking", f"#{student_data['academic_ranking_overall']} Colegio", f"#{student_data['academic_ranking_in_course']} Salón")

    st.subheader("Boletín de Calificaciones Ponderadas por Materia")
    student_report = final_grades_df[final_grades_df["student_id"] == st_id][[
        "subject_name", "department", "final_grade", "approval_status"
    ]].rename(columns={
        "subject_name": "Materia",
        "department": "Área",
        "final_grade": "Nota Definitiva Ponderada",
        "approval_status": "Estado"
    })
    st.dataframe(student_report, use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# 4. COMPARATIVA DE CURSOS
# -----------------------------------------------------------------------------
elif menu == "🏫 Comparativa de Cursos":
    st.title("🏫 Comparativa de Cursos y Grados")
    st.markdown("Comparación de desempeño homogéneo entre cohortes y niveles escolares.")

    st.dataframe(
        courses_df[[
            "course_name", "grade_level", "total_students", "course_gpa",
            "overall_pass_rate_percentage", "overall_fail_rate_percentage"
        ]].rename(columns={
            "course_name": "Curso",
            "grade_level": "Nivel",
            "total_students": "Estudiantes",
            "course_gpa": "Promedio Salón",
            "overall_pass_rate_percentage": "% Aprobación",
            "overall_fail_rate_percentage": "% Reprobación"
        }),
        use_container_width=True,
        hide_index=True
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Promedio de Notas por Curso")
        st.bar_chart(courses_df.set_index("course_name")["course_gpa"], color="#3F51B5")
    with col_b:
        st.subheader("% Aprobación por Curso")
        st.bar_chart(courses_df.set_index("course_name")["overall_pass_rate_percentage"], color="#009688")


# -----------------------------------------------------------------------------
# 5. SUBIR ARCHIVO EXCEL (.XLSX)
# -----------------------------------------------------------------------------
elif menu == "📤 Subir Archivo Excel (.xlsx)":
    st.title("📤 Ingesta Directa de Archivo Excel (.xlsx)")
    st.markdown("""
    Carga tu archivo de calificaciones en formato Excel. El pipeline extraerá automáticamente las hojas,
    aplicará validaciones de calidad, aislará registros con inconsistencias en `data/errors/` y
    actualizará el modelo analítico en PostgreSQL (`school_dw`) en tiempo real.
    """)

    from src.ingestion.excel_handler import create_excel_template, process_uploaded_excel_file

    col_info, col_dl = st.columns([3, 1])
    with col_info:
        st.info("💡 **Hojas requeridas**: `cursos`, `materias`, `estudiantes`, `evaluaciones`, `calificaciones`.")
    with col_dl:
        template_bytes = create_excel_template()
        st.download_button(
            label="📥 Descargar Plantilla Excel",
            data=template_bytes,
            file_name="plantilla_calificaciones.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.divider()

    uploaded_file = st.file_uploader(
        "Arrastra o selecciona un archivo Excel (.xlsx o .xls):",
        type=["xlsx", "xls"]
    )

    if uploaded_file is not None:
        st.success(f"Archivo cargado: **{uploaded_file.name}** ({round(uploaded_file.size / 1024, 1)} KB)")

        if st.button("🚀 Procesar Archivo y Ejecutar Pipeline", type="primary"):
            with st.spinner("Procesando hojas de cálculo, validando calidad y actualizando PostgreSQL..."):
                try:
                    summary = process_uploaded_excel_file(uploaded_file.getvalue())
                    st.cache_data.clear()
                    st.success("🎉 ¡Archivo Excel procesado y pipeline ejecutado exitosamente!")
                    st.write("**Hojas importadas:**", ", ".join(summary["sheets_imported"]))
                    st.write("**Filas importadas:**", summary["rows_imported"])
                    st.info("Ve a la pestaña '🏛️ Resumen Ejecutivo' o '📚 Rendimiento por Materia' para ver los datos actualizados.")
                except Exception as err:
                    st.error(f"❌ Error al procesar el archivo: {err}")


# -----------------------------------------------------------------------------
# 6. AUDITORÍA Y CALIDAD DE DATOS (DATA ERRORS)
# -----------------------------------------------------------------------------
elif menu == "🛡️ Auditoría y Calidad (Data Errors)":
    st.title("🛡️ Auditoría de Calidad de Datos y Cuarentena")
    st.markdown("""
    En este módulo de Ingeniería de Datos se visualizan los registros anómalos que fueron detectados
    durante la etapa de validación (`src/validation/validate_data.py`) y aislados en `data/errors/`.
    **El dataset raw original permanece 100% inmutable.**
    """)

    error_files = list(ERRORS_DATA_DIR.glob("*_errors.csv"))

    tabs = st.tabs([f.name.replace("_errors.csv", "").capitalize() for f in error_files])

    for tab, err_file in zip(tabs, error_files):
        with tab:
            err_df = pd.read_csv(err_file)
            st.write(f"**Total de registros rechazados:** `{len(err_df)}`")
            if not err_df.empty:
                st.dataframe(err_df, use_container_width=True)
            else:
                st.success("No se encontraron registros erróneos en esta entidad.")
