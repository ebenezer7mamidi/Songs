import xml.etree.ElementTree as ET
from pathlib import Path
import csv
import re

# ---------------------------
# Settings
# ---------------------------
output_dir = Path("OutputXML_TelEngTamHin")  # folder with XML files
verse_mismatch_csv = output_dir / "verse_chorus_mismatch.csv"
missing_lang_csv = output_dir / "missing_languages.csv"
chorus_mismatch_csv = output_dir / "chorus_mismatch.csv"
languages = ["eng", "tel", "tam", "hin"]

# ---------------------------
# Initialize CSVs
# ---------------------------
with verse_mismatch_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["FileName", "VerseName", "MissingLanguages"])

with missing_lang_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["FileName", "MissingLanguages"])

with chorus_mismatch_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["FileName", "ChorusName", "MissingLanguages"])

# ---------------------------
# Helper to extract languages from a line
# ---------------------------
lang_re = re.compile(r"\{lang-(\w+)\}")

def get_line_langs(text):
    return lang_re.findall(text)

# ---------------------------
# Track songs missing a language entirely
# ---------------------------
songs_missing_lang = set()

# ---------------------------
# Process each XML file
# ---------------------------
for xml_file in output_dir.glob("*.xml"):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Namespaces
        ns = {"ns": "http://openlyrics.info/namespace/2009/song"}

        lyrics = root.find("ns:lyrics", ns)
        if lyrics is None:
            continue

        # Track languages per verse
        verse_missing = {}  # verse_name -> list of missing langs
        chorus_missing = {} # c1/c2 -> list of missing langs
        langs_in_song = set()  # langs that appear at least once

        for verse in lyrics.findall("ns:verse", ns):
            verse_name = verse.attrib.get("name")
            present_langs = set()
            for lines in verse.findall("ns:lines", ns):
                text = lines.text or ""
                for lang in get_line_langs(text):
                    present_langs.add(lang)
                    langs_in_song.add(lang)

            missing_langs = [l for l in languages if l not in present_langs]

            # Separate chorus vs verses
            if verse_name in ["c1", "c2"]:
                if missing_langs:
                    chorus_missing[verse_name] = missing_langs
            else:
                if missing_langs:
                    verse_missing[verse_name] = missing_langs

        # ---------------------------
        # Check for missing language entirely
        # ---------------------------
        missing_lang_entire = [l for l in languages if l not in langs_in_song]
        if missing_lang_entire:
            songs_missing_lang.add(xml_file.name)
            with missing_lang_csv.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([xml_file.name, ",".join(missing_lang_entire)])
        else:
            # ---------------------------
            # Write verse/chorus mismatch report
            # Only if song is not missing any language entirely
            # ---------------------------
            if verse_missing:
                with verse_mismatch_csv.open("a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for verse_name, missing_langs in verse_missing.items():
                        writer.writerow([xml_file.name, verse_name, ",".join(missing_langs)])

            # ---------------------------
            # Write chorus mismatch report
            # ---------------------------
            if chorus_missing:
                with chorus_mismatch_csv.open("a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for chorus_name, missing_langs in chorus_missing.items():
                        writer.writerow([xml_file.name, chorus_name, ",".join(missing_langs)])

    except Exception as e:
        print(f"⚠ Failed to process {xml_file.name}: {e}")

print("✅ Validation completed.")
print(f"Verse/chorus mismatch report: {verse_mismatch_csv}")
print(f"Missing language report: {missing_lang_csv}")
print(f"Chorus mismatch report: {chorus_mismatch_csv}")
