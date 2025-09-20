import re
import csv
from pathlib import Path

# Base directories for Tamil and Hindi
LANG_DIRS = {
    "tamil": Path(r"C:\Users\ebene\Documents\Zion Songs\SourceFile\Tamil"),
    "hindi": Path(r"C:\Users\ebene\Documents\Zion Songs\SourceFile\Hindi")
}

# Output directory
OUT_DIR = Path(r"C:\Users\ebene\Documents\Zion Songs\SourceFile")

# CSV catalog file
CATALOG_CSV = Path(r"C:\Users\ebene\Documents\Zion Songs\songs_catalog.csv")

# Regex patterns
verse_re = re.compile(r'^(s\d+|ch\d+)\.(.*)', re.IGNORECASE)  # s1. s2. ch1. ch2.
chorus_re = re.compile(r'^(c:)(.*)', re.IGNORECASE)
echorus_re = re.compile(r'^(ec:)(.*)', re.IGNORECASE)
ch_colon_re = re.compile(r'^ch:(.*)', re.IGNORECASE)  # ch: without number

# Load CSV reference mapping: TamilNumber/HindiNumber -> Telugu SongNumber
tamil_ref_map = {}
hindi_ref_map = {}

# Reverse maps for duplicate detection
telugu_from_tamil = {}
telugu_from_hindi = {}

if CATALOG_CSV.exists():
    with CATALOG_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            song_num = row.get("SongNumber", "").strip()  # Telugu number
            tamil_num = row.get("TamilNumber", "").strip()
            hindi_num = row.get("HindiNumber", "").strip()

            if tamil_num:
                tamil_ref_map[tamil_num] = song_num
                telugu_from_tamil.setdefault(song_num, []).append(tamil_num)

            if hindi_num:
                hindi_ref_map[hindi_num] = song_num
                telugu_from_hindi.setdefault(song_num, []).append(hindi_num)

    # Check duplicates for Tamil
    for telugu_num, tamil_list in telugu_from_tamil.items():
        if len(tamil_list) > 1:
            print(f"⚠ Duplicate Tamil mappings → Telugu {telugu_num}: Tamil {', '.join(tamil_list)}")

    # Check duplicates for Hindi
    for telugu_num, hindi_list in telugu_from_hindi.items():
        if len(hindi_list) > 1:
            print(f"⚠ Duplicate Hindi mappings → Telugu {telugu_num}: Hindi {', '.join(hindi_list)}")

def clean_line(text: str) -> str:
    # Remove hyphens, invisible chars, normalize spaces
    text = text.replace('-', ' ').replace('–', ' ')
    text = re.sub(r'[\u200B\uFEFF]', '', text)  # zero width / BOM
    text = re.sub(r'\s+', ' ', text)
    # Remove all single or double pipes
    text = text.replace('|', '')
    text = text.replace('||', '')
    return text.strip().lstrip('.')  # remove leading dots

def process_song_file(filepath: Path, lang: str):
    song_number = str(int(filepath.stem.lstrip("0")))  # e.g., "002" -> "2"
    lines = filepath.read_text(encoding="utf-8").splitlines()

    pallavi_lines = []
    anupallavi_lines = []
    verses = {}
    title = None
    unknown_labels = []

    # Temporary buffer for consecutive ch: lines
    ch_buffer = []
    def flush_ch_buffer():
        nonlocal ch_buffer, title
        if ch_buffer:
            idx = len([k for k in verses.keys() if k.startswith(("s", "ch"))]) + 1
            tag = f"ch{idx}"
            verses.setdefault(tag, []).extend(ch_buffer)
            if not title and idx == 1:
                title = ch_buffer[0]
            ch_buffer = []

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue

        # Ignore v: and vc: lines completely
        if raw.lower().startswith(("v:", "vc:")):
            continue

        # Chorus (Pallavi)
        m = chorus_re.match(raw)
        if m:
            flush_ch_buffer()
            content = clean_line(m.group(2))
            if content:
                if not title:
                    title = content
                pallavi_lines.append(content)
            continue

        # Extended chorus (Anupallavi)
        m = echorus_re.match(raw)
        if m:
            flush_ch_buffer()
            content = clean_line(m.group(2))
            if content:
                anupallavi_lines.append(content)
            continue

        # ch: lines without number → buffer them
        m = ch_colon_re.match(raw)
        if m:
            content = clean_line(m.group(1))
            if content:
                ch_buffer.append(content)
            continue

        # Verses with number (s1, s2, ch1, ch2)
        m = verse_re.match(raw)
        if m:
            flush_ch_buffer()
            tag = m.group(1).lower()
            content = clean_line(m.group(2))
            if content:
                verses.setdefault(tag, []).append(content)
                if not title and tag in ("s1", "ch1"):
                    title = content
            continue

        # Unknown labels (skip but report)
        flush_ch_buffer()
        if ":" in raw:
            unknown_labels.append(f"{filepath.name}: {raw}")

    # flush any remaining ch lines at the end
    flush_ch_buffer()

    if unknown_labels:
        print(f"⚠ Unknown labels in {lang} songs:")
        for lbl in unknown_labels:
            print(" ", lbl)

    # Determine Telugu Reference Number from CSV mapping
    if lang.lower() == "tamil":
        ref_number = tamil_ref_map.get(song_number, "TBD")
    elif lang.lower() == "hindi":
        ref_number = hindi_ref_map.get(song_number, "TBD")
    else:
        ref_number = "TBD"

    # Build output
    out_lines = [
        f"Song Number: {song_number}",
        f"Telugu Reference Number: {ref_number}",
        f"Song Title: {title if title else ''}"
    ]

    if pallavi_lines:
        out_lines.append("Pallavi : " + pallavi_lines[0])
        out_lines.extend(pallavi_lines[1:])

    if anupallavi_lines:
        out_lines.append("Anupallavi : " + anupallavi_lines[0])
        out_lines.extend(anupallavi_lines[1:])

    # Sort and number verses
    verse_tags = sorted([k for k in verses.keys() if k.startswith(("s", "ch"))],
                        key=lambda x: int(re.findall(r'\d+', x)[0]))
    for idx, tag in enumerate(verse_tags, start=1):
        for line_no, line in enumerate(verses[tag]):
            if line_no == 0:
                out_lines.append(f"{idx}. {line}")
            else:
                out_lines.append(line)  # no leading spaces for continuation lines

    return "\n".join(out_lines)

def process_all(lang: str):
    src_dir = LANG_DIRS[lang]
    all_songs = []
    for txt_file in sorted(src_dir.rglob("*.txt")):
        try:
            cleaned = process_song_file(txt_file, lang=lang)
            if cleaned.strip():
                all_songs.append(cleaned)
        except Exception as e:
            print(f"Error processing {txt_file.name}: {e}")

    final_output = "\n\n".join(all_songs) + "\n"
    out_file = OUT_DIR / f"all_songs_{lang}_cleaned.txt"
    out_file.write_text(final_output, encoding="utf-8")
    print(f"✔ All {lang} songs cleaned → {out_file}")

if __name__ == "__main__":
    process_all("tamil")
    process_all("hindi")
