import re
from pathlib import Path
import xml.etree.ElementTree as ET

# Source cleaned files
src_te = Path(r"SourceFile/all_songs_telugu_cleaned.txt")
src_en = Path(r"SourceFile/all_songs_english_cleaned.txt")
out_dir = Path("OutputXML_interleaved")
out_dir.mkdir(exist_ok=True)

# Trace log file
trace_file = out_dir / "trace_log.txt"
trace_file.write_text("Song Processing Trace Log\n\n", encoding="utf-8")

# Regex patterns
song_number_re = re.compile(r"^Song Number: (\d+)")
title_re = re.compile(r"^(EN|TE) Title: (.+)")
pallavi_re = re.compile(r"^(పల్లవి|Pallavi)\s*:\s*(.*)")
anupallavi_re = re.compile(r"^(అనుపల్లవి|Anupallavi)\s*:\s*(.*)")
verse_re = re.compile(r"^(\d+)\.\s*(.*)")


def log_trace(message):
    with trace_file.open("a", encoding="utf-8") as f:
        f.write(message + "\n")
    print(message)


def parse_clean_file(filepath):
    """Parse cleaned Telugu or English file into dict of songs."""
    if not filepath.exists():
        log_trace(f"⚠ File {filepath} not found.")
        return {}

    songs = {}
    with filepath.open(encoding="utf-8") as f:
        lines = [l.rstrip() for l in f]

    song_num, title = None, None
    pallavi, anupallavi, verses = [], [], []
    mode = None  # 'pallavi', 'anupallavi', 'verse'

    for line in lines + [""]:  # sentinel to flush last song
        if line.startswith("Song Number:"):
            if song_num:
                songs[song_num] = {
                    "title": title or "",
                    "pallavi": pallavi,
                    "anupallavi": anupallavi,
                    "verses": verses,
                }
            m = song_number_re.match(line)
            song_num = m.group(1)
            title = None
            pallavi, anupallavi, verses = [], [], []
            mode = None
        elif line.startswith(("EN Title:", "TE Title:")):
            m = title_re.match(line)
            title = m.group(2)
        elif pallavi_re.match(line):
            m = pallavi_re.match(line)
            pallavi.append(m.group(2))
            mode = "pallavi"
        elif anupallavi_re.match(line):
            m = anupallavi_re.match(line)
            anupallavi.append(m.group(2))
            mode = "anupallavi"
        elif verse_re.match(line):
            m = verse_re.match(line)
            verses.append([m.group(2)])
            mode = "verse"
        elif line.strip() == "":
            mode = None
        else:
            if mode == "pallavi":
                pallavi.append(line)
            elif mode == "anupallavi":
                anupallavi.append(line)
            elif mode == "verse" and verses:
                verses[-1].append(line)

    # Flush last song
    if song_num:
        songs[song_num] = {
            "title": title or "",
            "pallavi": pallavi,
            "anupallavi": anupallavi,
            "verses": verses,
        }

    return songs


def create_interleaved_song_xml(song_num, te_song, en_song):
    song = ET.Element(
        "song",
        {
            "xmlns": "http://openlyrics.info/namespace/2009/song",
            "version": "0.8",
            "createdIn": "OpenLP 2.9.5",
            "modifiedIn": "OpenLP 2.9.5",
            "modifiedDate": "2025-09-13T12:00:00",
        },
    )

    # Properties
    props = ET.SubElement(song, "properties")
    titles = ET.SubElement(props, "titles")
    ET.SubElement(titles, "title").text = en_song["title"]
    ET.SubElement(titles, "title").text = te_song["title"]
    ET.SubElement(titles, "title").text = song_num

    # --- Verse order logic (three cases) ---
    verses_count = len(te_song["verses"])
    order_parts = []

    if not te_song["pallavi"] and not te_song["anupallavi"]:
        # Case 1: Only verses
        order_parts = [f"v{i+1}" for i in range(verses_count)]
    elif te_song["pallavi"] and not te_song["anupallavi"]:
        # Case 2: Pallavi only
        for i in range(verses_count):
            order_parts.append("c1")
            order_parts.append(f"v{i+1}")
        order_parts.append("c1")
    elif te_song["pallavi"] and te_song["anupallavi"]:
        # Case 3: Pallavi + Anupallavi
        order_parts = ["c1", "c2"]
        for i in range(verses_count):
            order_parts.append(f"v{i+1}")
            order_parts.append("c2")
        order_parts.append("c1")

    ET.SubElement(props, "verseOrder").text = " ".join(order_parts)

    # Authors
    authors = ET.SubElement(props, "authors")
    ET.SubElement(authors, "author").text = "His Servant"

    # Songbooks
    songbooks = ET.SubElement(props, "songbooks")
    ET.SubElement(
        songbooks, "songbook", {"name": "Zion Songs Telugu Roman", "entry": song_num}
    )

    # Lyrics
    lyrics = ET.SubElement(song, "lyrics")

    def add_lines(en_texts, te_texts, verse_name):
        verse = ET.SubElement(lyrics, "verse", {"name": verse_name})
        try:
            ET.SubElement(verse, "lines").text = (
                "{lang-eng}" + "\n".join(en_texts) + "{/lang-eng}"
            )
            ET.SubElement(verse, "lines").text = (
                "{lang-tel}" + "\n".join(te_texts) + "{/lang-tel}"
            )
        except Exception as e:
            log_trace(
                f"⚠ Error in {verse_name} of song {song_num}: {e}\nEN: {en_texts}\nTE: {te_texts}"
            )

    # Pallavi c1
    if te_song["pallavi"]:
        add_lines(en_song.get("pallavi", []), te_song["pallavi"], "c1")

    # Anupallavi c2
    if te_song["anupallavi"]:
        add_lines(en_song.get("anupallavi", []), te_song["anupallavi"], "c2")

    # Verses
    for idx, (te_lines, en_lines) in enumerate(
        zip(te_song["verses"], en_song["verses"]), 1
    ):
        add_lines(en_lines, te_lines, f"v{idx}")

    return song


def save_song_xml(song_element, song_num, en_title):
    safe_title = re.sub(r"[<>:\"/\\|?*]", "_", en_title)
    filename = f"{song_num}_{safe_title}.xml"
    filepath = out_dir / filename
    try:
        ET.ElementTree(song_element).write(
            filepath, encoding="utf-8", xml_declaration=True
        )
        log_trace(f"✔ Wrote {filename}")
    except Exception as e:
        log_trace(f"⚠ Failed to write {filename}: {e}")


# Parse files
te_songs = parse_clean_file(src_te)
en_songs = parse_clean_file(src_en)

# Generate interleaved XML
for sn in te_songs:
    if sn not in en_songs:
        log_trace(f"⚠ Song {sn} missing in English file. Skipping.")
        continue
    try:
        xml_song = create_interleaved_song_xml(sn, te_songs[sn], en_songs[sn])
        save_song_xml(xml_song, sn, en_songs[sn]["title"])
    except Exception as e:
        log_trace(f"⚠ An error occurred for song {sn}: {e}")

log_trace("\n✅ Processing finished.")
