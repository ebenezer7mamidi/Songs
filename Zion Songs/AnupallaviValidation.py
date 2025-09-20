import re
from pathlib import Path

# File paths
src_dir = Path("SourceFile")
telugu_file = src_dir / "all_songs_telugu_cleaned.txt"
english_file = src_dir / "all_songs_english_cleaned.txt"

# Regex
song_number_re = re.compile(r"^Song Number:\s*(\d+)")
pallavi_te_re = re.compile(r"^పల్లవి\s*:")
pallavi_en_re = re.compile(r"^Pallavi\s*:", re.IGNORECASE)
anup_te_re = re.compile(r"^అనుపల్లవి\s*:")
anup_en_re = re.compile(r"^Anupallavi\s*:", re.IGNORECASE)

def load_songs(file):
    songs = {}
    current_num = None
    current_lines = []

    with file.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            m = song_number_re.match(line)
            if m:
                # Save previous
                if current_num:
                    songs[current_num] = current_lines
                # Start new
                current_num = m.group(1)
                current_lines = []
            else:
                current_lines.append(line)

        # Save last song
        if current_num:
            songs[current_num] = current_lines

    return songs

# Load Telugu and English songs
telugu_songs = load_songs(telugu_file)
english_songs = load_songs(english_file)

missing_report = []

for num in sorted(set(telugu_songs.keys()) | set(english_songs.keys()), key=int):
    te_lines = telugu_songs.get(num, [])
    en_lines = english_songs.get(num, [])

    # Pallavi checks
    has_te_pallavi = any(pallavi_te_re.match(l) for l in te_lines)
    has_en_pallavi = any(pallavi_en_re.match(l) for l in en_lines)

    if has_te_pallavi and not has_en_pallavi:
        missing_report.append(f"⚠ Telugu has Pallavi but English missing → Song {num}")
    elif has_en_pallavi and not has_te_pallavi:
        missing_report.append(f"⚠ English has Pallavi but Telugu missing → Song {num}")

    # Anupallavi checks
    has_te_anup = any(anup_te_re.match(l) for l in te_lines)
    has_en_anup = any(anup_en_re.match(l) for l in en_lines)

    if has_te_anup and not has_en_anup:
        missing_report.append(f"⚠ Telugu has Anupallavi but English missing → Song {num}")
    elif has_en_anup and not has_te_anup:
        missing_report.append(f"⚠ English has Anupallavi but Telugu missing → Song {num}")

# Print report
if missing_report:
    print("\n".join(missing_report))
else:
    print("✔ All songs have Pallavi/Anupallavi presence aligned between Telugu and English")
