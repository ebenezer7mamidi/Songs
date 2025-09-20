import csv
import re
from pathlib import Path

# Input cleaned Telugu file
src_file = Path(r"SourceFile/all_songs_telugu_cleaned.txt")
out_csv = Path("songs_catalog.csv")

# Regex patterns
song_number_re = re.compile(r"^Song Number: (\d+)")
en_title_re = re.compile(r"^EN Title: (.+)")
te_title_re = re.compile(r"^TE Title: (.+)")
tamil_number_re = re.compile(r"^TamilNumber: (.+)")
hindi_number_re = re.compile(r"^HindiNumber: (.+)")

rows = []
current_song = {
    "SongNumber": "",
    "Telugu Title": "",
    "English Title": "",
    "TamilNumber": "",
    "HindiNumber": ""
}

with src_file.open(encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        if line.startswith("Song Number:"):
            # If previous song exists, save it
            if current_song["SongNumber"]:
                rows.append(current_song)
            # Start a new song
            m = song_number_re.match(line)
            current_song = {
                "SongNumber": m.group(1) if m else "",
                "Telugu Title": "",
                "English Title": "",
                "TamilNumber": "",
                "HindiNumber": ""
            }

        elif line.startswith("EN Title:"):
            m = en_title_re.match(line)
            if m:
                current_song["English Title"] = m.group(1)

        elif line.startswith("TE Title:"):
            m = te_title_re.match(line)
            if m:
                current_song["Telugu Title"] = m.group(1)

        elif line.startswith("TamilNumber:"):
            m = tamil_number_re.match(line)
            if m:
                current_song["TamilNumber"] = m.group(1)

        elif line.startswith("HindiNumber:"):
            m = hindi_number_re.match(line)
            if m:
                current_song["HindiNumber"] = m.group(1)

    # Add last song
    if current_song["SongNumber"]:
        rows.append(current_song)

# Write CSV
with out_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f, 
        fieldnames=["SongNumber", "Telugu Title", "English Title", "TamilNumber", "HindiNumber"]
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"✔ CSV created: {out_csv}")
