import re
from pathlib import Path
import csv
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

# ---------------------------
# File Paths
# ---------------------------
telugu_file = Path(r"SourceFile/all_songs_telugu_cleaned.txt")
tamil_file = Path(r"SourceFile/all_songs_tamil_cleaned.txt")
hindi_file = Path(r"SourceFile/all_songs_hindi_cleaned.txt")
mapping_file = Path(r"C:\Users\ebene\Documents\Zion Songs\songs_catalog.csv")

out_dir = Path("OutputCSV_Report")
out_dir.mkdir(exist_ok=True)
report_csv = out_dir / "songs_report.csv"
report_pdf = out_dir / "songs_report_table.pdf"
fonts_dir = out_dir / "fonts"

# ---------------------------
# Regex Patterns
# ---------------------------
song_number_re = re.compile(r"^Song Number:\s*(\S+)")
en_title_re = re.compile(r"^EN Title:\s*(.+)")
title_generic_re = re.compile(r"^Song Title:\s*(.+)")

# ---------------------------
# Parse Telugu file to get English titles
# ---------------------------
def parse_telugu_file(filepath):
    songs = {}
    with filepath.open(encoding="utf-8") as f:
        lines = [l.rstrip("\n\r") for l in f]
    song_num, en_title = None, None
    for line in lines + [""]:
        if line.startswith("Song Number:"):
            if song_num:
                songs[song_num] = {"EN": en_title or "Not available"}
            m = song_number_re.match(line)
            song_num = m.group(1) if m else None
            en_title = None
        elif line.startswith("EN Title:"):
            m = en_title_re.match(line)
            if m:
                en_title = m.group(1).strip()
    if song_num:
        songs[song_num] = {"EN": en_title or "Not available"}
    return songs

# ---------------------------
# Parse Tamil/Hindi cleaned file to get title
# ---------------------------
def parse_clean_file(filepath):
    songs = {}
    song_num = None
    title = None
    with filepath.open(encoding="utf-8") as f:
        lines = [l.rstrip("\n\r") for l in f]
    for line in lines + [""]:
        if line.startswith("Song Number:"):
            if song_num:
                songs[song_num] = title or "Not available"
            m = song_number_re.match(line)
            song_num = m.group(1) if m else None
            title = None
        elif line.startswith("Song Title:") or line.startswith("TE Title:") or line.startswith("TA Title:") or line.startswith("HI Title:"):
            m = title_generic_re.match(line)
            if m:
                title = m.group(1).strip()
    if song_num:
        songs[song_num] = title or "Not available"
    return songs

# ---------------------------
# Load Mapping CSV
# ---------------------------
song_map = {}
with mapping_file.open(encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        tel_no = row.get("SongNumber", "").strip()
        if not tel_no:
            continue
        song_map[tel_no] = {
            "TamilNumber": row.get("TamilNumber","0").strip() or "0",
            "HindiNumber": row.get("HindiNumber","0").strip() or "0",
        }

# ---------------------------
# Parse files
# ---------------------------
tel_songs = parse_telugu_file(telugu_file)
tam_songs = parse_clean_file(tamil_file)
hin_songs = parse_clean_file(hindi_file)

# ---------------------------
# Write CSV report
# ---------------------------
with report_csv.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["TeluguNumber","EnglishTitle","TamilNumber","TamilTitle","HindiNumber","HindiTitle"])
    
    # Matched songs from mapping
    for tel_no, map_row in song_map.items():
        en_title = tel_songs.get(tel_no, {}).get("EN", "Not available")
        tam_no = map_row.get("TamilNumber", "0") or "0"
        hin_no = map_row.get("HindiNumber", "0") or "0"
        tam_title = tam_songs.get(tam_no, "Not available") if tam_no != "0" else "Not available"
        hin_title = hin_songs.get(hin_no, "Not available") if hin_no != "0" else "Not available"
        writer.writerow([tel_no, en_title, tam_no, tam_title, hin_no, hin_title])
    
    # Unmatched Tamil songs
    for tam_no, tam_title in tam_songs.items():
        if tam_no not in [row.get("TamilNumber") for row in song_map.values()]:
            writer.writerow(["0","Not available", tam_no, tam_title, "0","Not available"])
    
    # Unmatched Hindi songs
    for hin_no, hin_title in hin_songs.items():
        if hin_no not in [row.get("HindiNumber") for row in song_map.values()]:
            writer.writerow(["0","Not available","0","Not available", hin_no, hin_title])

print("CSV report generated successfully!")

# ---------------------------
# Generate PDF with table
# ---------------------------
# Register fonts
pdfmetrics.registerFont(TTFont("NotoSans", str(fonts_dir / "NotoSans-Regular.ttf")))
pdfmetrics.registerFont(TTFont("NotoTamil", str(fonts_dir / "NotoSansTamil-Regular.ttf")))
pdfmetrics.registerFont(TTFont("NotoDevanagari", str(fonts_dir / "NotoSansDevanagari-Regular.ttf")))

# Load CSV data for PDF
all_rows = []
with report_csv.open(encoding="utf-8") as f:
    reader = csv.reader(f)
    headers = next(reader)
    all_rows.append(headers)
    for row in reader:
        all_rows.append(row)

# Font mapping per column
font_map = ["NotoSans", "NotoSans", "NotoSans", "NotoTamil", "NotoSans", "NotoDevanagari"]

# Paragraph styles
style_map = {}
for i, font in enumerate(font_map):
    style_map[i] = ParagraphStyle(
        name=f"col{i}_style",
        fontName=font,
        fontSize=4,
        leading=5
    )

# Table data with Paragraphs
table_data = []
for row in all_rows:
    row_cells = []
    for i, cell in enumerate(row):
        para = Paragraph(cell.replace('\n','<br />'), style_map[i])
        row_cells.append(para)
    table_data.append(row_cells)

# Column widths (narrow numbers, wider titles)
col_widths = [30, 150, 30, 180, 30, 180]

# Create PDF
doc = SimpleDocTemplate(
    str(report_pdf),
    pagesize=A4,
    rightMargin=10,
    leftMargin=10,
    topMargin=10,
    bottomMargin=10
)

table = Table(table_data, colWidths=col_widths, repeatRows=1)

# Table styling with borders and alternating row colors
style = TableStyle([
    ("GRID", (0,0), (-1,-1), 0.25, colors.black),
    ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("ALIGN", (0,0), (-1,-1), "LEFT"),
    
    # Reduce cell padding
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 2),
    ("TOPPADDING", (0,0), (-1,-1), 1),
    ("BOTTOMPADDING", (0,0), (-1,-1), 1),
])

for i in range(1, len(table_data)):
    if i % 2 == 0:
        style.add("BACKGROUND", (0,i), (-1,i), colors.whitesmoke)

table.setStyle(style)
doc.build([table])

print("PDF with proper table borders and multilingual text generated successfully!")
