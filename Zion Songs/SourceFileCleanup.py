import re
from pathlib import Path

# Source directory
src_dir = Path("SourceFile")
if not src_dir.exists():
    src_dir = Path(r"\SourceFile")  # fallback for Windows

# Files to process
files = {
    "telugu": "all_songs_telugu.txt",
    "english": "all_songs_english.txt",
    "interleaved": "all_songs_interleaved.txt",
}

# Regex
telugu_char_re = re.compile(r'[\u0C00-\u0C7F]')
inline_clean_re = re.compile(r'(\|\|.*?\|\|)|(॥.*?\|\|)|\|\|')
verse_number_re = re.compile(r'^(\d+)\.')
double_quote_re = re.compile(r'“.*?”|".*?"')

# Split English and Telugu by first Telugu character or pipes
def split_en_te(rest, file_type="telugu"):
    rest = rest.strip()
    if file_type == "english":
        split_match = re.split(r'\s*\|\|\s*|\s*\|\s*\|\s*', rest, 1)
        en = split_match[0].strip()
        te = ''
    else:
        m = telugu_char_re.search(rest)
        if m:
            idx = m.start()
            en = rest[:idx].strip()
            te = rest[idx:].strip()
        else:
            en = rest.strip()
            te = ''
        en = re.sub(r'(\|\||\| \|)+$', '', en).strip()
    return en, te

def capitalize_first_letter(line):
    if not line:
        return line
    return line[0].upper() + line[1:]

def clean_file(file_type, fname):
    infile = src_dir / fname
    if not infile.exists():
        print(f"SKIP: {infile} not found.")
        return

    lines = infile.read_text(encoding="utf-8").splitlines()
    
    # Replace leading dot with Title:
    lines = [line if not line.startswith(".") else "Title:" + line[1:] for line in lines]

    out_lines = []
    first_song = True
    song_buffer = []
    before_first_section = False  # true until Pallavi/Anupallavi/first verse

    for line in lines + [""]:  # Add dummy blank line to process last song
        raw = line.rstrip()
        if raw.startswith("Title:"):
            # Process previous song
            if song_buffer:
                # Remove text in double quotes
                song_buffer = [double_quote_re.sub('', l) for l in song_buffer]

                # Append to output
                if not first_song:
                    out_lines.append("")  # blank line between songs
                out_lines.extend(song_buffer)
                song_buffer = []
                first_song = False

            # Start new song
            raw_clean = raw.replace("Title:", "").strip()
            num_match = re.match(r'^(\d+)\.', raw_clean)
            num = num_match.group(1) if num_match else ''
            rest = raw_clean[len(num)+1:].strip() if num else raw_clean
            en, te = split_en_te(rest, file_type)

            song_buffer.append(f"Song Number: {num}")
            song_buffer.append(f"EN Title: {en}")
            if file_type in ("telugu", "interleaved") and te:
                song_buffer.append(f"TE Title: {te}")

            before_first_section = True
            continue

        # Remove inline markers
        cleaned = inline_clean_re.sub('', raw)

        # Remove all hyphens
        cleaned = cleaned.replace('-', ' ').replace('–', ' ')

        # Collapse multiple spaces into one
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Skip junk/subheadings until we hit Pallavi, Anupallavi, or first verse
        if before_first_section:
            if verse_number_re.match(cleaned) or \
               ("pallavi" in cleaned.lower() and file_type == "english") or \
               ("పల్లవి" in cleaned and file_type != "english") or \
               ("anupallavi" in cleaned.lower() and file_type == "english") or \
               ("అనుపల్లవి" in cleaned and file_type != "english"):
                before_first_section = False
            else:
                continue  # skip subheading

        # Fix verse numbering spacing for Telugu
        if file_type in ("telugu", "interleaved") and verse_number_re.match(cleaned):
            num = verse_number_re.match(cleaned).group(1)
            rest_line = cleaned[len(num):].lstrip('.').strip()
            cleaned = f"{num}. {rest_line}"

        # Capitalize English lines
        if file_type in ("english", "interleaved") and cleaned:
            cleaned = capitalize_first_letter(cleaned)

        # Normalize Anupallavi in English
        if file_type == "english":
            cleaned = re.sub(r'^(A\.?\s?P\.?\s?:\s*)', 'Anupallavi : ', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'Anupallavi :\s*:+', 'Anupallavi :', cleaned)

        # Ensure space after colon for Anupallavi and Pallavi
        cleaned = re.sub(r'(Pallavi|Anupallavi)\s*:\s*', r'\1 : ', cleaned)
        cleaned = re.sub(r'(పల్లవి)\s*:\s*', r'\1 : ', cleaned)

        if cleaned != "":
            song_buffer.append(cleaned)

    # Ensure exactly one blank line at the end
    while out_lines and out_lines[-1] == "":
        out_lines.pop()
    out_lines.append("")

    # Write to _cleaned.txt
    out_file = infile.with_name(infile.stem + "_cleaned.txt")
    out_file.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"✔ Cleaned {fname} → {out_file.name}")

# Process all files
for ftype, fname in files.items():
    clean_file(ftype, fname)
