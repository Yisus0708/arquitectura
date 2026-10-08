import os
import shutil
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class NumberedCanvas(canvas.Canvas):
    """Canvas con numeración de página dinámica 'Página X de Y' y encabezado."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor('#64748B'))

        # Encabezado (a partir de la página 2)
        if self._pageNumber > 1:
            self.drawString(36, 756, "School Grades Data Platform • Documento Explicativo del Proyecto")
            self.drawRightString(576, 756, "http://localhost:8000")
            self.setStrokeColor(colors.HexColor('#CBD5E1'))
            self.setLineWidth(0.5)
            self.line(36, 750, 576, 750)

        # Pie de página en todas las páginas
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(576, 22, page_text)
        self.drawString(36, 22, "Arquitectura Medallion en PostgreSQL • Data Quality & Cuarentena • Octubre 2026")
        self.setStrokeColor(colors.HexColor('#E2E8F0'))
        self.setLineWidth(0.5)
        self.line(36, 30, 576, 30)
        self.restoreState()


def build_guide_pdf():
    desktop_onedrive = Path(r"C:\Users\SOPORTE\OneDrive\Desktop\Guia_Explicativa_Arquitectura_y_Filtros.pdf")
    desktop_local = Path(r"C:\Users\SOPORTE\Desktop\Guia_Explicativa_Arquitectura_y_Filtros.pdf")

    doc = SimpleDocTemplate(
        str(desktop_onedrive),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Colores corporativos
    c_primary = colors.HexColor('#1E3A8A')    # Azul oscuro
    c_secondary = colors.HexColor('#2563EB')  # Azul real
    c_accent = colors.HexColor('#0D9488')     # Teal
    c_danger = colors.HexColor('#DC2626')     # Rojo
    bg_card = colors.HexColor('#F8FAFC')      # Slate 50
    border_card = colors.HexColor('#E2E8F0')  # Slate 200
    text_main = colors.HexColor('#0F172A')    # Slate 900
    text_muted = colors.HexColor('#475569')   # Slate 600

    # Estilos tipográficos
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14.5,
        leading=18,
        textColor=c_primary,
        spaceAfter=2
    )

    sec_title = ParagraphStyle(
        'SecTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13.5,
        textColor=c_primary,
        spaceBefore=6,
        spaceAfter=3
    )

    p_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.2,
        textColor=text_main,
        spaceAfter=3
    )

    p_bold = ParagraphStyle(
        'BodyBold',
        parent=p_style,
        fontName='Helvetica-Bold'
    )

    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10.2,
        textColor=text_muted
    )

    story = []

    # =========================================================================
    # PÁGINA 1: CONTEXTO DEL PROYECTO Y ARQUITECTURA MEDALLÓN COMPLETA
    # =========================================================================
    header_tbl = Table([
        [
            Paragraph("<b>GUIA EXPLICATIVA: ARQUITECTURA MEDALLON Y FILTROS DE DATOS</b><br/><font size='7.5' color='#64748B'>School Grades Analytics Platform &bull; De Archivos Excel a un Almacen Analitico Auditado</font>", title_style),
            Paragraph("<para align='right'><font size='7.5' color='#16A34A'><b>SISTEMA EN EJECUCION ACTIVA</b></font><br/><font size='7' color='#64748B'>Web: http://localhost:8000</font></para>", p_style)
        ]
    ], colWidths=[390, 150])
    header_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_tbl)
    story.append(HRFlowable(width="100%", thickness=2, color=c_secondary, spaceAfter=6, spaceBefore=2))

    story.append(Paragraph("1. &iquest;QUE ES ESTE PROYECTO Y CUAL ES SU OBJETIVO?", sec_title))
    story.append(Paragraph(
        "Es una <b>plataforma integral de ingenieria de datos y analitica academica</b> construida para instituciones educativas. "
        "Su objetivo primordial es resolver un dolor critico en la educacion: los colegios recopilan miles de calificaciones en archivos de Excel "
        "manuales que suelen contener errores humanos, duplicados, inconsistencias y nombres de columnas heterogeneos. "
        "Este proyecto <b>automatiza por completo el procesamiento</b>: toma cualquier Excel escolar, lo valida, separa los errores para revision, "
        "organiza la informacion en <b>PostgreSQL</b> mediante una arquitectura profesional de 4 capas y disponibiliza tableros interactivos en tiempo real.",
        p_style
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("2. &iquest;QUE ES LA ARQUITECTURA MEDALLON Y POR QUE SE UTILIZA?", sec_title))
    story.append(Paragraph(
        "La <b>Arquitectura Medallon</b> (popularizada en la industria de datos por Databricks y adoptada en los estandares modernos de Data Lakehouse) "
        "es un patron de diseno que organiza la informacion en <b>capas secuenciales de madurez, limpieza y refinamiento logico</b>. "
        "En lugar de cargar datos brutos directamente a las tablas de reporte (lo cual genera errores y colapsos), los datos se refinan progresivamente.",
        p_style
    ))
    story.append(Paragraph(
        "Este diseno garantiza dos principios fundamentales en ingenieria de datos: "
        "<b>1) Inmutabilidad y Auditoria:</b> nunca se pierde ni se altera el dato original recibido (si surge una duda legal de una nota, el registro original sigue intacto); "
        "y <b>2) Calidad de Consumo:</b> las consultas analiticas, coordinadores y tableros solo consumen datos matematicamente consistentes, sin notas fantasmas ni calculos rotos.",
        p_style
    ))
    story.append(Spacer(1, 4))

    medallion_table_data = [
        [Paragraph("<b>Capa Medallon</b>", p_bold), Paragraph("<b>&iquest;Que es y que funcion cumple?</b>", p_bold), Paragraph("<b>Implementacion Tecnica en este Proyecto</b>", p_bold)],
        [
            Paragraph("<b>1. Raw (Bronce)<br/><font size='6.5' color='#64748B'>Dato Crudo Original</font></b>", p_style),
            Paragraph("<b>Almacena la copia fiel y original del archivo recibido.</b><br/>No se aplica ninguna modificacion de negocio ni filtro restrictivo. Preserva todo tal cual llego del docente.", small_style),
            Paragraph("&bull; Esquema <code>raw.*</code> en PostgreSQL (todas las columnas son de texto amplio).<br/>&bull; Registro de Checksum criptografico <b>SHA-256</b> en <code>ingestion_metadata.json</code> para auditoria legal y trazabilidad.", small_style)
        ],
        [
            Paragraph("<b>2. Staging<br/><font size='6.5' color='#64748B'>Zona de Limpieza</font></b>", p_style),
            Paragraph("<b>Zona de preparacion tecnica y normalizacion sintactica.</b><br/>Convierte textos a numeros y fechas formales, elimina duplicados identicos y descarta espacios en blanco.", small_style),
            Paragraph("&bull; Esquema <code>staging.*</code> generado via scripts SQL.<br/>&bull; Uso de <b>Common Table Expressions (CTEs)</b> y funciones de ventana como <code>ROW_NUMBER() OVER (...)</code> para deduplicar registros.", small_style)
        ],
        [
            Paragraph("<b>3. Silver (Plata)<br/><font size='6.5' color='#64748B'>Fuente de Verdad 3NF</font></b>", p_style),
            Paragraph("<b>Modelo Relacional en Tercera Forma Normal (3NF).</b><br/>Es la estructura central del colegio: garantiza relaciones validas entre cursos, materias, docentes y estudiantes.", small_style),
            Paragraph("&bull; Esquema <code>silver.*</code> con restricciones fuertes del motor:<br/>- <b>Primary Keys (PK)</b> para unicidad de registros.<br/>- <b>Foreign Keys (FK)</b> para impedir notas o materias huerfanas.<br/>- Constraints <b>CHECK (score BETWEEN 0.0 AND 5.0)</b>.", small_style)
        ],
        [
            Paragraph("<b>4. Gold (Oro)<br/><font size='6.5' color='#64748B'>Capa Analitica / BI</font></b>", p_style),
            Paragraph("<b>Modelo Dimensional Estrella (Star Schema) y Marts.</b><br/>Optimizada para velocidad de consulta y visualizacion analitica sin necesidad de realizar calculos pesados al abrir un reporte.", small_style),
            Paragraph("&bull; <b>Dimensiones:</b> <code>dim_student</code>, <code>dim_course</code>, <code>dim_subject</code>, <code>dim_date</code>.<br/>&bull; <b>Hechos:</b> <code>fact_grades</code>.<br/>&bull; <b>Data Marts:</b> Vistas precalculadas de promedios ponderados, cuadros de honor y materias criticas listas para Power BI.", small_style)
        ],
    ]
    t_med = Table(medallion_table_data, colWidths=[85, 215, 240])
    t_med.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, border_card),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_card]),
    ]))
    story.append(t_med)
    story.append(Spacer(1, 6))

    # Beneficio arquitectural
    ben_data = [
        [
            Paragraph("<b>&iquest;Por que no cargar el Excel directo a la tabla final?</b><br/>"
                      "Porque si un profesor sube una nota erronea (ej. 50 en vez de 5.0), un sistema directo o bien corrompe todos los promedios del colegio "
                      "o bien lanza un error fatal y bloquea el trabajo de toda la institucion. La arquitectura Medallon permite aislar el error, preservar la evidencia "
                      "y mantener el 100% de la plataforma operativa en todo momento.", small_style)
        ]
    ]
    t_ben = Table(ben_data, colWidths=[540])
    t_ben.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BFDBFE')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_ben)

    # SALTO DE PÁGINA PARA PÁGINA 2
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 2: LOS FILTROS, CUARENTENA, FLUJO EN 6 ETAPAS Y RESULTADOS REALES
    # =========================================================================
    story.append(Paragraph("3. LOS FILTROS DE CALIDAD DE DATOS (DATA QUALITY) Y EL SISTEMA DE CUARENTENA", sec_title))
    story.append(Paragraph(
        "En este proyecto se implemento una estrategia de <b>Mecanismo de Cuarentena (Data Quarantine)</b> y <b>Auto-Sanitizacion</b>. "
        "Los registros correctos continuan sin pausa al almacen de datos, mientras que los registros defectuosos se desvian automaticamente "
        "a la carpeta <code>data/errors/</code> con una columna obligatoria <code>error_reason</code> que especifica el motivo exacto del fallo para su correccion.",
        p_style
    ))

    filters_data = [
        [Paragraph("<b>Nombre del Filtro</b>", p_bold), Paragraph("<b>Regla de Negocio / Validacion Matematica</b>", p_bold), Paragraph("<b>Accion del Pipeline y Destino</b>", p_bold)],
        [
            Paragraph("<b>1. Filtro de Rango de Notas<br/>(Escala 0.0 - 5.0)</b>", p_style),
            Paragraph("Valida que toda nota cumpla estrictamente <code>0.0 &le; nota &le; 5.0</code>.<br/>Detecta notas imposibles (-1.0, 7.2, 50.0) y textos ('ND', 'pendiente', '--').", small_style),
            Paragraph("<b>Cuarentena:</b> Aisladas en <code>grades_errors.csv</code> con el motivo (ej. <i>'nota fuera de rango (7.2)'</i> o <i>'nota no numerica'</i>).", small_style)
        ],
        [
            Paragraph("<b>2. Filtro de Ponderacion<br/>(Suma Pesos = 100%)</b>", p_style),
            Paragraph("Cada grupo de evaluaciones de una materia en un periodo <b>debe sumar exactamente el 100.0%</b> de los pesos porcentuales.", small_style),
            Paragraph("<b>Cuarentena:</b> Si las evaluaciones suman 90% o 110%, el grupo se aisla en <code>assessments_errors.csv</code> indicando el desfase porcentual.", small_style)
        ],
        [
            Paragraph("<b>3. Auto-Sanitizacion<br/>(Comas por Puntos)</b>", p_style),
            Paragraph("Corrige la costumbre comun de escribir <code>4,5</code> en vez de <code>4.5</code> por configuracion regional del teclado.", small_style),
            Paragraph("<b>Auto-Correccion:</b> El pipeline convierte la coma a punto (4.5) y registra el cambio en <code>corrections_log.csv</code> sin rechazar la nota.", small_style)
        ],
        [
            Paragraph("<b>4. Integridad Temporal<br/>(Fechas Coherentes)</b>", p_style),
            Paragraph("Detecta fechas de entrega con anos futuros (ej. 2027) o fechas de nacimiento fuera de limites biologicos escolares (nacidos en 1900 o 2031).", small_style),
            Paragraph("<b>Cuarentena:</b> Aisladas en <code>students_errors.csv</code> y <code>grades_errors.csv</code> (ej. <i>'Impossible birth_date: 1900-01-01'</i>).", small_style)
        ],
        [
            Paragraph("<b>5. Integridad Referencial<br/>(Anti-Orfandad)</b>", p_style),
            Paragraph("Verifica que no se carguen notas de alumnos o materias que no existen en la lista institucional de matriculados.", small_style),
            Paragraph("<b>Cuarentena:</b> Notas huerfanas aisladas en <code>grades_errors.csv</code> (ej. <i>'estudiante_id inexistente (80)'</i>).", small_style)
        ],
        [
            Paragraph("<b>6. Control de Asistencias</b>", p_style),
            Paragraph("Valida que las inasistencias no superen las clases programadas ni sean numeros negativos.", small_style),
            Paragraph("<b>Cuarentena:</b> Aisladas en <code>attendance_errors.csv</code> (ej. <i>'inasistencias > dias de clase'</i>).", small_style)
        ]
    ]
    t_fil = Table(filters_data, colWidths=[105, 210, 225])
    t_fil.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_secondary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, border_card),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_card]),
    ]))
    story.append(t_fil)
    story.append(Spacer(1, 4))

    # Flujo secuencial
    story.append(Paragraph("4. EL FLUJO COMPLETO DEL PIPELINE (PASO A PASO EN 6 ETAPAS)", sec_title))
    flow_steps = [
        [
            Paragraph("<b>Etapa 1: Ingesta Dinamica</b><br/><font size='6.8' color='#475569'>Lectura del Excel sin importar el orden ni nombres rigidos de columnas.</font>", small_style),
            Paragraph("<b>&rarr;</b>", ParagraphStyle('arr1', parent=p_style, alignment=1, fontSize=10, textColor=c_secondary)),
            Paragraph("<b>Etapa 2: Validacion & Cuarentena</b><br/><font size='6.8' color='#475569'>Ejecucion de los 6 filtros; separacion de fallos a data/errors/.</font>", small_style),
            Paragraph("<b>&rarr;</b>", ParagraphStyle('arr2', parent=p_style, alignment=1, fontSize=10, textColor=c_secondary)),
            Paragraph("<b>Etapa 3: Carga Idempotente Raw</b><br/><font size='6.8' color='#475569'>Insercion segura en PostgreSQL raw con hash SHA-256.</font>", small_style),
        ],
        [
            Paragraph("<b>Etapa 4: Transformacion Staging</b><br/><font size='6.8' color='#475569'>CTEs SQL, casteo de tipos de datos y eliminacion de duplicados.</font>", small_style),
            Paragraph("<b>&rarr;</b>", ParagraphStyle('arr3', parent=p_style, alignment=1, fontSize=10, textColor=c_secondary)),
            Paragraph("<b>Etapa 5: Capa Relacional Silver</b><br/><font size='6.8' color='#475569'>Poblado en 3NF con llaves PK/FK activas y reglas CHECK.</font>", small_style),
            Paragraph("<b>&rarr;</b>", ParagraphStyle('arr4', parent=p_style, alignment=1, fontSize=10, textColor=c_secondary)),
            Paragraph("<b>Etapa 6: Modelo Estrella Gold</b><br/><font size='6.8' color='#475569'>Poblado de dimensiones, fact_grades y Data Marts para BI.</font>", small_style),
        ]
    ]
    t_fl = Table(flow_steps, colWidths=[165, 15, 170, 15, 175])
    t_fl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_fl)
    story.append(Spacer(1, 4))

    # Resultados reales
    story.append(Paragraph("5. EVIDENCIA Y RESULTADOS DE LA ULTIMA EJECUCION EN VIVO", sec_title))
    metrics_kpi = [
        [
            Paragraph("<para align='center'><font size='10' color='#1D4ED8'><b>240</b></font><br/><font size='6.5' color='#475569'><b>ESTUDIANTES ACTIVOS</b></font></para>", p_style),
            Paragraph("<para align='center'><font size='10' color='#1D4ED8'><b>34,492</b></font><br/><font size='6.5' color='#475569'><b>CALIFICACIONES VALIDAS</b></font></para>", p_style),
            Paragraph("<para align='center'><font size='10' color='#DC2626'><b>2,865</b></font><br/><font size='6.5' color='#475569'><b>FILAS EN CUARENTENA</b></font></para>", p_style),
            Paragraph("<para align='center'><font size='10' color='#0D9488'><b>3.59 / 5.0</b></font><br/><font size='6.5' color='#475569'><b>PROMEDIO GENERAL</b></font></para>", p_style),
            Paragraph("<para align='center'><font size='10' color='#16A34A'><b>79.35%</b></font><br/><font size='6.5' color='#475569'><b>TASA APROBACION</b></font></para>", p_style),
            Paragraph("<para align='center'><font size='10' color='#B91C1C'><b>23.69 s</b></font><br/><font size='6.5' color='#475569'><b>TIEMPO PIPELINE</b></font></para>", p_style),
        ]
    ]
    t_mkpi = Table(metrics_kpi, colWidths=[90, 90, 90, 90, 90, 90])
    t_mkpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BFDBFE')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DBEAFE')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_mkpi)

    findings_data = [
        [
            Paragraph("<b>🏆 Hallazgos de Rendimiento Academico</b><br/>&bull; <b>Lider Institucional:</b> Grado 11B (Promedio 3.80 | 89.08% de aprobacion).<br/>&bull; <b>Zona de Atencion Prioritaria:</b> Grado 7A (Promedio 3.44 | 67.63% de aprobacion).", small_style),
            Paragraph("<b>🎯 Cuadro de Honor vs. Plan de Refuerzo</b><br/>&bull; <b>1° Puesto:</b> Sofia Caballero Rodriguez (7B) - Promedio <b>4.96</b>.<br/>&bull; <b>Alerta Temprana:</b> 5 alumnos detectados con promedio &lt; 2.20 para tutoria preventiva inmediata.", small_style)
        ]
    ]
    t_fnd = Table(findings_data, colWidths=[270, 270])
    t_fnd.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_card),
        ('BOX', (0,0), (-1,-1), 1, border_card),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_fnd)
    story.append(Spacer(1, 3))

    # Puntos de acceso
    access_data = [
        [Paragraph("<b>Componente</b>", p_bold), Paragraph("<b>Ubicacion / Comando</b>", p_bold), Paragraph("<b>Funcionamiento</b>", p_bold)],
        [
            Paragraph("Dashboard Web", p_style),
            Paragraph("<code>http://localhost:8000</code>", small_style),
            Paragraph("Interfaz web en vivo (FastAPI + Chart.js): subida de Excel, reportes de estudiantes y graficos interactivos.", small_style)
        ],
        [
            Paragraph("Almacen PostgreSQL", p_style),
            Paragraph("Base: <code>school_dw</code> (puerto 5432)", small_style),
            Paragraph("Contiene los 4 esquemas Medallion (raw, staging, silver, gold) listos para conexion desde Power BI Desktop.", small_style)
        ],
        [
            Paragraph("Auditoria y Cuarentena", p_style),
            Paragraph("Carpeta: <code>data/errors/</code>", small_style),
            Paragraph("Archivos CSV descargables con cada fila rechazada y la explicacion exacta del error para los docentes.", small_style)
        ]
    ]
    t_acc = Table(access_data, colWidths=[95, 145, 300])
    t_acc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, border_card),
    ]))
    story.append(t_acc)

    # Construir PDF con NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)

    # Copiar a la otra ruta del escritorio si existe
    if desktop_local.parent.exists() and desktop_local != desktop_onedrive:
        try:
            shutil.copy2(str(desktop_onedrive), str(desktop_local))
            print("Copiado con exito a:", desktop_local)
        except Exception as e:
            print("Aviso al copiar:", e)

    print(f"PDF generado exitosamente en: {desktop_onedrive}")
    print(f"Tamano: {desktop_onedrive.stat().st_size} bytes")

if __name__ == '__main__':
    build_guide_pdf()
