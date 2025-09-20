import os
import xml.etree.ElementTree as ET
from datetime import datetime

# ------------------------------
# Paths
# ------------------------------
source_file = os.path.join('.', 'SourceFiles', 'all_songs.txt')
output_folder = os.path.join('.', 'XMLOutput')
os.makedirs(output_folder, exist_ok=True)

# XML namespace
NS = "http://openlyrics.info/namespace/2009/song"
ET.register_namespace('', NS)

# ------------------------------
# Helper to create XML structure
# ------------------------------
def create_song_xml(song_number, song_title, verse_order, choruses, verses):
    modified_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    song_el = ET.Element("song", {
        "xmlns": NS,
        "version": "0.8",
        "createdIn": "OpenLP 2.9.5",
        "modifiedIn": "OpenLP 2.9.5",
        "modifiedDate": modified_date
    })

    # properties
    props_el = ET.SubElement(song_el, "properties")
    titles_el = ET.SubElement(props_el, "titles")
    ET.SubElement(titles_el, "title").text = song_title
    ET.SubElement(titles_el, "title").text = str(song_number)
    ET.SubElement(props_el, "verseOrder").text = verse_order
    authors_el = ET.SubElement(props_el, "authors")
    ET.SubElement(authors_el, "author").text = "His Servant"
    songbooks_el = ET.SubElement(props_el, "songbooks")
    ET.SubElement(songbooks_el, "songbook", {"name": "Christ in Song", "entry": str(song_number)})

    # lyrics
    lyrics_el = ET.SubElement(song_el, "lyrics")

    # Helper to wrap text in {lang-eng}...{/lang-eng}
    def wrap_lang(text):
        return f"{{lang-eng}}{text}{{/lang-eng}}"

    # Add choruses c1, c2...
    for num, chorus_text in choruses.items():
        v = ET.SubElement(lyrics_el, "verse", {"name": f"c{num}"})
        lines_el = ET.SubElement(v, "lines")
        lines_el.text = wrap_lang(chorus_text.strip())

    # Add verses v1, v2...
    for idx, verse_text in enumerate(verses, 1):
        v = ET.SubElement(lyrics_el, "verse", {"name": f"v{idx}"})
        lines_el = ET.SubElement(v, "lines")
        lines_el.text = wrap_lang(verse_text.strip())

    return ET.ElementTree(song_el)

# ------------------------------
# Read and split source file carefully
# ------------------------------
with open(source_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Split by double newlines
raw_songs = [s.strip() for s in content.split('\n\n') if s.strip()]

# Filter: only include blocks starting with SongNumber:
valid_songs = []
orphan_text = []
for s in raw_songs:
    if s.startswith("SongNumber:"):
        valid_songs.append(s)
    else:
        orphan_text.append(s)

print(f"Total valid songs found in source file: {len(valid_songs)}")
if orphan_text:
    print(f"Found {len(orphan_text)} orphan text blocks between songs (ignored).")

# ------------------------------
# Process each valid song
# ------------------------------
for song_idx, song_text in enumerate(valid_songs, 1):
    lines = song_text.splitlines()
    song_number = None
    song_title = None
    verse_order = ""
    choruses = {}
    verses = []

    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()

        if line.startswith("SongNumber:"):
            song_number = line.replace("SongNumber:", "").strip()

        elif line.startswith("SongTitle:"):
            song_title = line.replace("SongTitle:", "").strip()

        elif line.startswith("VerseOrder:"):
            verse_order = line.replace("VerseOrder:", "").strip()

        elif line.startswith("Chorus"):
            # New chorus block
            parts = line.split(":", 1)
            if len(parts) == 2:
                num_part = parts[0].strip()
                text = parts[1].strip()
                try:
                    num = int(num_part.replace("Chorus", ""))
                    chorus_lines = [text] if text else []
                    idx += 1
                    # collect all following lines until next block
                    while idx < len(lines) and not (
                        lines[idx].strip().startswith(("Chorus", "SongNumber", "SongTitle", "VerseOrder"))
                        or (lines[idx].strip() and lines[idx].strip()[0].isdigit() and lines[idx].strip()[1] == '.')
                    ):
                        chorus_lines.append(lines[idx].strip())
                        idx += 1
                    # remove extra spaces from each line
                    chorus_clean = "\n".join(l.strip() for l in chorus_lines if l.strip())
                    choruses[num] = chorus_clean
                    continue
                except ValueError:
                    print(f"[Warning] Invalid chorus number in song {song_number}: {line}")

        elif line and line[0].isdigit() and line[1] == '.':
            # Verse block
            verse_lines = [line.split('.', 1)[1].strip()]
            idx += 1
            while idx < len(lines) and not (
                lines[idx].strip().startswith(("Chorus", "SongNumber", "SongTitle", "VerseOrder"))
                or (lines[idx].strip() and lines[idx].strip()[0].isdigit() and lines[idx].strip()[1] == '.')
            ):
                verse_lines.append(lines[idx].strip())
                idx += 1
            # remove extra spaces from each line
            verse_clean = "\n".join(l.strip() for l in verse_lines if l.strip())
            verses.append(verse_clean)
            continue

        idx += 1

    # Validations
    if not song_number:
        print(f"[Warning] Missing SongNumber in song index {song_idx}")
        song_number = f"Unknown{song_idx}"
    if not song_title:
        print(f"[Warning] Missing SongTitle in song number {song_number}")
        song_title = f"UnknownTitle{song_idx}"
    if not verse_order:
        print(f"[Warning] Missing VerseOrder in song number {song_number}")
        verse_order = ""
    if not verses and not choruses:
        print(f"[Warning] No lyrics found in song number {song_number}")

    # Create XML
    tree = create_song_xml(song_number, song_title, verse_order, choruses, verses)

    # Save file
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in song_title)
    filename = f"{song_number}_{safe_title}.xml"
    file_path = os.path.join(output_folder, filename)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)

    # Log only SongNumber and filename
    print(f"[Saved] SongNumber: {song_number} -> {filename}")

print(f"All XML files generated in folder: {output_folder}")
