import os
import shutil
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_pdf():
    # Paths to Desktop
    pdf_path_onedrive = Path(r"C:\Users\SOPORTE\OneDrive\Desktop\Resumen_Ejecutivo_Proyecto.pdf")
    pdf_path_local = Path(r"C:\Users\SOPORTE\Desktop\Resumen_Ejecutivo_Proyecto.pdf")

    doc = SimpleDocTemplate(
        str(pdf_path_onedrive),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Colors
    primary_color = colors.HexColor('#1E3A8A')    # Dark blue
    secondary_color = colors.HexColor('#2563EB')  # Royal blue
    bg_card = colors.HexColor('#F8FAFC')          # Slate 50
    border_card = colors.HexColor('#E2E8F0')      # Slate 200
    text_main = colors.HexColor('#0F172A')        # Slate 900
    text_muted = colors.HexColor('#475569')       # Slate 600

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=19,
        textColor=primary_color,
        spaceAfter=2
    )

    h1_style = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=primary_color,
        spaceBefore=7,
        spaceAfter=3
    )

    p_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=text_main,
        spaceAfter=3
    )

    p_bold = ParagraphStyle(
        'BodyTextBold',
        parent=p_style,
        fontName='Helvetica-Bold'
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=text_muted
    )

    story = []

    # 1. Header
    header_data = [
        [
            Paragraph("<b>School Grades Data Platform</b><br/><font size='8' color='#64748B'>Pipeline de Ingenieria de Datos &bull; Arquitectura Medallion End-to-End</font>", title_style),
            Paragraph("<para align='right'><font size='8' color='#1D4ED8'><b>ESTADO: EN EJECUCION</b></font><br/><font size='7' color='#64748B'>Web App: http://localhost:8000</font></para>", p_style)
        ]
    ]
    t_header = Table(header_data, colWidths=[380, 160])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=2, color=secondary_color, spaceAfter=6, spaceBefore=2))

    # 2. Que es este proyecto
    story.append(Paragraph("1. &iquest;QUE ES ESTE PROYECTO? (RESUMEN DIRECTO)", h1_style))
    story.append(Paragraph(
        "Es una <b>plataforma integral de ingenieria de datos y analitica academica</b> que automatiza la ingesta de notas escolares "
        "desde hojas de calculo Excel, las limpia y valida bajo reglas de negocio estrictas, las almacena estructuradamente en <b>PostgreSQL</b> "
        "usando una <b>Arquitectura Medallion (Raw &rarr; Staging &rarr; Silver &rarr; Gold)</b> y las presenta en un <b>Dashboard Web interactivo en tiempo real</b> y en <b>Power BI</b>.",
        p_style
    ))

    # 3. Problema vs Solucion
    story.append(Paragraph("2. EL PROBLEMA QUE RESUELVE", h1_style))
    problem_data = [
        [
            Paragraph("<b>&#10060; El Problema Tradicional</b>", p_bold),
            Paragraph("<b>&#9989; La Solucion Implementada</b>", p_bold)
        ],
        [
            Paragraph("&bull; Hojas Excel dispersas con formatos inconsistentes.<br/>&bull; Errores humanos: notas &gt; 5.0, comas por puntos, alumnos no matriculados.<br/>&bull; Semanas de consolidacion manual sin deteccion oportuna de reprobacion.", callout_style),
            Paragraph("&bull; Ingesta universal flexible sin plantillas rigidas obligatorias.<br/>&bull; Cuarentena automatica de registros anomalos sin detener el flujo.<br/>&bull; Pipeline en <b>23 segundos</b> con alertas tempranas y cuadro de honor.", callout_style)
        ]
    ]
    t_prob = Table(problem_data, colWidths=[265, 275])
    t_prob.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#FEF2F2')),
        ('BACKGROUND', (1,0), (1,-1), colors.HexColor('#F0FDF4')),
        ('BOX', (0,0), (0,-1), 1, colors.HexColor('#FECACA')),
        ('BOX', (1,0), (1,-1), 1, colors.HexColor('#BBF7D0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_prob)

    # 4. Flujo del Pipeline
    story.append(Paragraph("3. FLUJO DEL PIPELINE END-TO-END", h1_style))
    flow_data = [
        [
            Paragraph("<b>1. Ingesta Flexible</b><br/><font size='7' color='#475569'>Sube Excel; detecta hojas y columnas semanticamente.</font>", p_style),
            Paragraph("<b>&rarr;</b>", ParagraphStyle('a1', parent=p_style, alignment=1, fontSize=12, textColor=secondary_color)),
            Paragraph("<b>2. Data Quality</b><br/><font size='7' color='#475569'>Filtro 0-5.0, pesos 100%, autocorreccion de comas.</font>", p_style),
            Paragraph("<b>&rarr;</b>", ParagraphStyle('a2', parent=p_style, alignment=1, fontSize=12, textColor=secondary_color)),
            Paragraph("<b>3. Medallion Postgres</b><br/><font size='7' color='#475569'>Raw (bronce) &rarr; Staging &rarr; Silver &rarr; Gold (Estrella).</font>", p_style),
            Paragraph("<b>&rarr;</b>", ParagraphStyle('a3', parent=p_style, alignment=1, fontSize=12, textColor=secondary_color)),
            Paragraph("<b>4. Visualizacion</b><br/><font size='7' color='#475569'>Dashboard Web (FastAPI) &bull; Power BI Desktop.</font>", p_style),
        ]
    ]
    t_flow = Table(flow_data, colWidths=[120, 15, 130, 15, 125, 15, 120])
    t_flow.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_flow)

    # 5. Capas Medallion
    story.append(Paragraph("4. ARQUITECTURA MEDALLION EN POSTGRESQL", h1_style))
    medallion_data = [
        [Paragraph("<b>Capa</b>", p_bold), Paragraph("<b>Proposito de Negocio</b>", p_bold), Paragraph("<b>Detalle Tecnico</b>", p_bold)],
        [
            Paragraph("<b>1. Raw (Bronce)</b>", p_style),
            Paragraph("Copia inalterable del origen.", callout_style),
            Paragraph("Tablas raw.* (tipos texto) + checksums SHA-256 para auditoria forense.", callout_style)
        ],
        [
            Paragraph("<b>2. Staging</b>", p_style),
            Paragraph("Limpieza tecnica y tipado de datos.", callout_style),
            Paragraph("Tablas staging.* mediante SQL CTEs, deduplicacion y sanitizacion.", callout_style)
        ],
        [
            Paragraph("<b>3. Silver (Plata)</b>", p_style),
            Paragraph("Modelo Relacional 3NF consistente.", callout_style),
            Paragraph("Tablas silver.* con Primary Keys, Foreign Keys y constraints CHECK (0.0-5.0).", callout_style)
        ],
        [
            Paragraph("<b>4. Gold (Oro)</b>", p_style),
            Paragraph("Modelo Dimensional Estrella y Marts.", callout_style),
            Paragraph("Dimensiones (estudiante, curso, materia, fecha), fact_grades y vistas analiticas.", callout_style)
        ]
    ]
    t_medallion = Table(medallion_data, colWidths=[85, 180, 275])
    t_medallion.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, border_card),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_card]),
    ]))
    story.append(t_medallion)

    # 6. Metricas Reales
    story.append(Paragraph("5. RESULTADOS REALES DE LA EJECUCION EN VIVO", h1_style))
    story.append(Paragraph("Metricas obtenidas tras procesar el archivo <b>colegio_test_completo.xlsx</b> (957 KB):", callout_style))

    kpi_data = [
        [
            Paragraph("<para align='center'><font size='12' color='#1D4ED8'><b>240</b></font><br/><font size='7' color='#475569'><b>ESTUDIANTES ACTIVOS</b></font></para>", p_style),
            Paragraph("<para align='center'><font size='12' color='#1D4ED8'><b>34,492</b></font><br/><font size='7' color='#475569'><b>NOTAS VALIDAS</b></font></para>", p_style),
            Paragraph("<para align='center'><font size='12' color='#0D9488'><b>3.59 / 5.0</b></font><br/><font size='7' color='#475569'><b>PROMEDIO GENERAL</b></font></para>", p_style),
            Paragraph("<para align='center'><font size='12' color='#16A34A'><b>79.35%</b></font><br/><font size='7' color='#475569'><b>TASA APROBACION</b></font></para>", p_style),
            Paragraph("<para align='center'><font size='12' color='#B91C1C'><b>23.69 s</b></font><br/><font size='7' color='#475569'><b>TIEMPO PIPELINE</b></font></para>", p_style),
        ]
    ]
    t_kpi = Table(kpi_data, colWidths=[108, 108, 108, 108, 108])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BFDBFE')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DBEAFE')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_kpi)

    insights_data = [
        [
            Paragraph("<b>&#127942; Rendimiento por Cursos</b><br/>&bull; <b>Mejor curso:</b> 11B (Promedio 3.80 | 89.08% aprobacion)<br/>&bull; <b>Curso 11A:</b> Promedio 3.77 | 86.01% aprobacion<br/>&bull; <b>Curso en alerta:</b> 7A (Promedio 3.44 | 67.63% aprobacion)", callout_style),
            Paragraph("<b>&#127919; Cuadro de Honor & Alerta Temprana</b><br/>&bull; <b>1&deg; Puesto:</b> Sofia Caballero Rodriguez (7B) - <b>4.96</b><br/>&bull; <b>2&deg; Puesto:</b> Antonia Hernandez Garcia (6A) - <b>4.84</b><br/>&bull; <b>Plan de Refuerzo:</b> 5 estudiantes con promedio &lt; 2.20 identificados.", callout_style)
        ]
    ]
    t_ins = Table(insights_data, colWidths=[270, 270])
    t_ins.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_card),
        ('BOX', (0,0), (-1,-1), 1, border_card),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_ins)

    # 7. Componentes Clave
    story.append(Paragraph("6. COMPONENTES CLAVE Y PUNTOS DE ACCESO", h1_style))
    components_data = [
        [Paragraph("<b>Componente</b>", p_bold), Paragraph("<b>Ruta / Enlace</b>", p_bold), Paragraph("<b>Descripcion</b>", p_bold)],
        [Paragraph("Dashboard Web", p_style), Paragraph("http://localhost:8000", callout_style), Paragraph("Interfaz web interactiva con KPIs, graficos y fichas de alumnos.", callout_style)],
        [Paragraph("Servidor Web", p_style), Paragraph("app_web.py", callout_style), Paragraph("FastAPI con carga de Excel, descarga de plantillas y API REST.", callout_style)],
        [Paragraph("Pipeline Runner", p_style), Paragraph("scripts/run_pipeline.py", callout_style), Paragraph("Ejecutor de las 6 etapas secuenciales del pipeline.", callout_style)],
        [Paragraph("Auditoria y Errores", p_style), Paragraph("data/errors/", callout_style), Paragraph("Archivos CSV con registros aislados y columna error_reason.", callout_style)],
    ]
    t_comp = Table(components_data, colWidths=[95, 135, 310])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, border_card),
    ]))
    story.append(t_comp)

    # Build
    doc.build(story)

    # Copy to local desktop if exists
    if pdf_path_local.parent.exists() and pdf_path_local != pdf_path_onedrive:
        try:
            shutil.copy2(str(pdf_path_onedrive), str(pdf_path_local))
            print("Copiado exitosamente a Escritorio local.")
        except Exception as e:
            print("Aviso al copiar a local:", e)

    print(f"PDF generado con exito en: {pdf_path_onedrive}")
    print(f"Tamano: {pdf_path_onedrive.stat().st_size} bytes")

if __name__ == '__main__':
    create_pdf()
