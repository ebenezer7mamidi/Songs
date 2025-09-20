import re
from pathlib import Path
import xml.etree.ElementTree as ET

# Source English cleaned file
src_file = Path(r"SourceFile/all_songs_english_cleaned.txt")
out_dir = Path("OutputXML_english")
out_dir.mkdir(exist_ok=True)

# Regex patterns
song_number_re = re.compile(r"^Song Number: (\d+)")
en_title_re = re.compile(r"^EN Title: (.+)")
pallavi_re = re.compile(r"^Pallavi\s*:\s*(.*)", re.IGNORECASE)
anupallavi_re = re.compile(r"^Anupallavi\s*:\s*(.*)", re.IGNORECASE)
verse_re = re.compile(r"^(\d+)\.\s*(.*)")


def safe_filename(text):
    return re.sub(r'[<>:"/\\|?*]', '_', text)


def create_song_xml(song_num, en_title, pallavi_lines, anupallavi_lines, verses_lines):
    song = ET.Element("song", {
        "xmlns": "http://openlyrics.info/namespace/2009/song",
        "version": "0.8",
        "createdIn": "OpenLP 2.9.5",
        "modifiedIn": "OpenLP 2.9.5",
        "modifiedDate": "2025-09-10T12:00:00"
    })

    # Properties
    props = ET.SubElement(song, "properties")
    titles = ET.SubElement(props, "titles")
    ET.SubElement(titles, "title").text = en_title
    ET.SubElement(titles, "title").text = song_num

    # Build verseOrder (3-case logic)
    verses_count = len(verses_lines)
    order_parts = []

    if not pallavi_lines and not anupallavi_lines:
        # Case 1: Only verses
        order_parts = [f"v{i}" for i in range(1, verses_count + 1)]
    elif pallavi_lines and not anupallavi_lines:
        # Case 2: Pallavi only
        for i in range(1, verses_count + 1):
            order_parts.append("c1")
            order_parts.append(f"v{i}")
        order_parts.append("c1")
    elif pallavi_lines and anupallavi_lines:
        # Case 3: Pallavi + Anupallavi
        order_parts = ["c1", "c2"]
        for i in range(1, verses_count + 1):
            order_parts.append(f"v{i}")
            order_parts.append("c2")
        order_parts.append("c1")

    ET.SubElement(props, "verseOrder").text = " ".join(order_parts)

    # Authors & Songbooks
    authors = ET.SubElement(props, "authors")
    ET.SubElement(authors, "author").text = "His Servant"
    songbooks = ET.SubElement(props, "songbooks")
    ET.SubElement(songbooks, "songbook", {"name": "Zion Songs English", "entry": song_num})

    # Lyrics
    lyrics = ET.SubElement(song, "lyrics")

    def add_lines(verse_name, lines_list):
        verse = ET.SubElement(lyrics, "verse", {"name": verse_name})
        verse_text = "\n".join(lines_list)
        ET.SubElement(verse, "lines").text = f"{{lang-eng}}{verse_text}{{/lang-eng}}"

    # c1 (Pallavi)
    if pallavi_lines:
        add_lines("c1", pallavi_lines)

    # c2 (Anupallavi)
    if anupallavi_lines:
        add_lines("c2", anupallavi_lines)

    # Verses
    for idx, verse_lines in enumerate(verses_lines, 1):
        add_lines(f"v{idx}", verse_lines)

    return song


# Parsing logic
try:
    with src_file.open(encoding="utf-8") as f:
        lines = [l.rstrip() for l in f]
except FileNotFoundError:
    print(f"⚠ File {src_file} not found. Please run cleanup script first.")
    exit(1)

song_num, en_title = None, None
pallavi_lines, anupallavi_lines = [], []
verses_lines = []
current_verse_lines = []
current_state = None  # "c1", "c2", "verse"


def flush_song():
    global song_num, en_title, pallavi_lines, anupallavi_lines, verses_lines, current_verse_lines, current_state
    if song_num:
        # Add last verse lines if any
        if current_state == "verse" and current_verse_lines:
            verses_lines.append(current_verse_lines)
        song_xml = create_song_xml(song_num, en_title or "", pallavi_lines, anupallavi_lines, verses_lines)
        filename = f"{song_num}_{safe_filename(en_title)}.xml"
        try:
            ET.ElementTree(song_xml).write(out_dir / filename, encoding="utf-8", xml_declaration=True)
            print(f"✔ Wrote {filename}")
        except Exception as e:
            print(f"⚠ Failed to write {filename}: {e}")
    # Reset
    song_num, en_title = None, None
    pallavi_lines, anupallavi_lines = [], []
    verses_lines = []
    current_verse_lines = []
    current_state = None


for line in lines + [""]:
    if not line.strip():
        flush_song()
        continue

    if line.startswith("Song Number:"):
        flush_song()
        song_num = song_number_re.match(line).group(1)
    elif line.startswith("EN Title:"):
        en_title = en_title_re.match(line).group(1)
    elif pallavi_re.match(line):
        current_state = "c1"
        pallavi_lines.append(pallavi_re.match(line).group(1))
    elif anupallavi_re.match(line):
        current_state = "c2"
        anupallavi_lines.append(anupallavi_re.match(line).group(1))
    elif verse_re.match(line):
        if current_state == "verse" and current_verse_lines:
            verses_lines.append(current_verse_lines)
        current_state = "verse"
        current_verse_lines = [verse_re.match(line).group(2)]
    else:
        if current_state == "c1":
            pallavi_lines.append(line)
        elif current_state == "c2":
            anupallavi_lines.append(line)
        elif current_state == "verse":
            current_verse_lines.append(line)
