"""
Script to create data/colegio_test.xlsx matching the exact data provided by the user.
"""
import io
import csv
from pathlib import Path
import openpyxl

RAW_USER_INPUT = Path(__file__).resolve().parent.parent / "scripts" / "user_data_dump.txt"

def build_test_excel():
    # Read user data dump
    with open(RAW_USER_INPUT, "r", encoding="utf-8") as f:
        content = f.read()

    sections = content.strip().split("\n\n")
    # Alternatively parse based on known headers
    lines = content.strip().splitlines()

    sheets_data = {}
    current_sheet = None
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("estudiante_id,"):
            if current_sheet:
                sheets_data[current_sheet] = current_lines
            current_sheet = "estudiantes"
            current_lines = [stripped]
        elif stripped.startswith("curso_id,"):
            if current_sheet:
                sheets_data[current_sheet] = current_lines
            current_sheet = "cursos"
            current_lines = [stripped]
        elif stripped.startswith("materia_id,"):
            if current_sheet:
                sheets_data[current_sheet] = current_lines
            current_sheet = "materias"
            current_lines = [stripped]
        elif stripped.startswith("evaluacion_id,"):
            if current_sheet:
                sheets_data[current_sheet] = current_lines
            current_sheet = "evaluaciones"
            current_lines = [stripped]
        elif stripped.startswith("nota_id,"):
            if current_sheet:
                sheets_data[current_sheet] = current_lines
            current_sheet = "calificaciones"
            current_lines = [stripped]
        elif stripped.startswith("hoja,"):
            if current_sheet:
                sheets_data[current_sheet] = current_lines
            current_sheet = "problemas"
            current_lines = [stripped]
        else:
            if current_lines is not None:
                current_lines.append(stripped)

    if current_sheet:
        sheets_data[current_sheet] = current_lines

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    for sheet_name, sheet_lines in sheets_data.items():
        ws = wb.create_sheet(title=sheet_name)
        reader = csv.reader(sheet_lines)
        for r_idx, row in enumerate(reader, start=1):
            for c_idx, val in enumerate(row, start=1):
                # Try parsing numeric or date
                ws.cell(row=r_idx, column=c_idx, value=val)

    out_file = Path(__file__).resolve().parent.parent / "data" / "colegio_test.xlsx"
    wb.save(out_file)
    print(f"colegio_test.xlsx created successfully at {out_file} with sheets: {list(sheets_data.keys())}")

if __name__ == "__main__":
    build_test_excel()
