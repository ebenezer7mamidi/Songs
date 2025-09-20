import re
from pathlib import Path
import xml.etree.ElementTree as ET
import csv

# ---------------------------
# File Paths
# ---------------------------
src_files = {
    "eng": Path(r"SourceFile/all_songs_english_cleaned.txt"),
    "tel": Path(r"SourceFile/all_songs_telugu_cleaned.txt"),
    "tam": Path(r"SourceFile/all_songs_tamil_cleaned.txt"),
    "hin": Path(r"SourceFile/all_songs_hindi_cleaned.txt"),
}

mapping_file = Path(r"songs_catalog.csv")
out_dir = Path("OutputXML_TelEngTamHin")
out_dir.mkdir(exist_ok=True)

# Trace log
trace_file = out_dir / "trace_log.txt"
trace_file.write_text("Song Processing Trace Log\n\n", encoding="utf-8")

# Duplicate report CSV
dup_csv = out_dir / "duplicates_report.csv"
with dup_csv.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "TeluguNo", "EnglishNo", "TamilNo", "HindiNo",
        "TeluguTitle", "EnglishTitle", "TamilTitle", "HindiTitle",
        "Reason"
    ])

# Summary CSV
export_csv = out_dir / "songs_export_summary.csv"
with export_csv.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "MasterID", "TeluguNo", "EnglishNo", "TamilNo", "HindiNo",
        "TeluguTitle", "EnglishTitle", "TamilTitle", "HindiTitle"
    ])

# Duplicate counter
duplicate_count = 0

# ---------------------------
# Regex Patterns
# ---------------------------
song_number_re = re.compile(r"^Song Number:\s*(\S+)")
title_lang_re = re.compile(r"^(EN|TE|TA|HI)\s+Title:\s*(.+)")
title_generic_re = re.compile(r"^Song Title:\s*(.+)")
verse_re = re.compile(r"^(\d+)\.\s*(.*)")

# ---------------------------
# Trace Logging
# ---------------------------
def log_trace(message):
    with trace_file.open("a", encoding="utf-8") as f:
        f.write(message + "\n")
    print(message)

# ---------------------------
# Clean line
# ---------------------------
def clean_line(line):
    if line is None:
        return ""
    line = line.strip()
    line = re.sub(r"^(పల్లవి|Pallavi|Anupallavi|అనుపల్లవి|Verse|Telugu Reference Number|Song Title)\s*:\s*", "", line, flags=re.IGNORECASE)
    if re.fullmatch(r"\d+", line):
        return ""
    line = re.sub(r"^\d+\.\s*", "", line)
    return line.strip()

# ---------------------------
# Parse Cleaned Song File
# ---------------------------
def parse_clean_file(filepath, lang=None):
    if not filepath.exists():
        log_trace(f"⚠ File {filepath} not found")
        return {}

    songs = {}
    with filepath.open(encoding="utf-8") as f:
        lines = [l.rstrip("\n\r") for l in f]

    song_num, title = None, None
    pallavi, anupallavi, verses = [], [], []
    tel_ref = None
    mode = None

    for line in lines + [""]:
        if line.startswith("Song Number:"):
            if song_num:
                songs[song_num] = {
                    "title": title or "",
                    "pallavi": pallavi,
                    "anupallavi": anupallavi,
                    "verses": verses,
                    "tel_ref": tel_ref or "TBD"
                }
            m = song_number_re.match(line)
            song_num = m.group(1) if m else None
            title = None
            pallavi, anupallavi, verses = [], [], []
            tel_ref = "TBD"
            mode = None
        elif line.startswith("Telugu Reference Number:"):
            tel_ref = clean_line(line) or "TBD"
        elif title_lang_re.match(line):
            m = title_lang_re.match(line)
            title = m.group(2).strip()
        elif title_generic_re.match(line):
            m = title_generic_re.match(line)
            title = m.group(1).strip()
        elif re.match(r"^(Pallavi|పల్లవి)\s*:", line, flags=re.IGNORECASE):
            text = clean_line(line)
            if text:
                pallavi.append(text)
            mode = "pallavi"
        elif re.match(r"^(Anupallavi|అనుపల్లవి)\s*:", line, flags=re.IGNORECASE):
            text = clean_line(line)
            if text:
                anupallavi.append(text)
            mode = "anupallavi"
        elif line.strip() == "":
            mode = None
        else:
            m = verse_re.match(line)
            if m:
                verse_text = clean_line(m.group(2))
                if verse_text:
                    verses.append([verse_text])
                mode = "verse"
            else:
                text = clean_line(line)
                if not text:
                    continue
                if mode == "pallavi":
                    pallavi.append(text)
                elif mode == "anupallavi":
                    anupallavi.append(text)
                elif mode == "verse" and verses:
                    verses[-1].append(text)
                else:
                    verses.append([text])
                    mode = "verse"

    if song_num:
        songs[song_num] = {
            "title": title or "",
            "pallavi": pallavi,
            "anupallavi": anupallavi,
            "verses": verses,
            "tel_ref": tel_ref or "TBD"
        }

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
        # read the historic/alt numbers as strings (keep empty string if missing)
        song_map[tel_no] = {
            "SongNumber": tel_no,
            "v1TeluguNo": row.get("v1TeluguNo", "").strip() or "",
            "v2TeluguNo": row.get("v2TeluguNo", "").strip() or "",
            "TamilNumber": row.get("TamilNumber", "").strip() or "",
            "HindiNumber": row.get("HindiNumber", "").strip() or "",
            "NepaliNumber": row.get("NepaliNumber", "").strip() or "",
        }

# ---------------------------
# Parse All Languages
# ---------------------------
all_songs = {lang: parse_clean_file(path, lang) for lang, path in src_files.items()}

# ---------------------------
# Exported IDs to avoid duplicates
# ---------------------------
exported_ids = set()
processed_master_ids = set()
processed_unmatched_tamil_ids = set()
processed_unmatched_hindi_ids = set()

# ---------------------------
# Duplicate CSV Helper
# ---------------------------
def write_duplicate_csv(tel_no, eng_no, tam_no, hin_no, titles, reason):
    global duplicate_count
    duplicate_count += 1
    with dup_csv.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            tel_no or "", eng_no or "", tam_no or "", hin_no or "",
            titles.get("tel", ""), titles.get("eng", ""), titles.get("tam", ""), titles.get("hin", ""),
            reason
        ])

# ---------------------------
# Remove title/TBD from verses
# ---------------------------
def remove_title_from_verses_if_present(lang_data, title):
    if not title:
        return False
    verses = lang_data.get("verses", [])
    for vi, verse in enumerate(list(verses)):
        for li, line in enumerate(list(verse)):
            if line and (line.strip() == title.strip() or line.strip() == "TBD"):
                if len(verse) == 1:
                    verses.pop(vi)
                    return True
                else:
                    return False
    return False

# ---------------------------
# Create Interleaved XML
# ---------------------------
def create_interleaved_song_xml(master_id, lang_songs, map_row):
    song = ET.Element(
        "song",
        {
            "xmlns": "http://openlyrics.info/namespace/2009/song",
            "version": "0.8",
            "createdIn": "OpenLP 2.9.5",
            "modifiedIn": "OpenLP 2.9.5",
            "modifiedDate": "2025-09-17T12:00:00",
        },
    )

    tel_eng_exist = bool((lang_songs.get("eng", {}).get("title")) or (lang_songs.get("tel", {}).get("title")))

    if not tel_eng_exist:
        for lang in ("tam", "hin"):
            ld = lang_songs.get(lang, {})
            if ld and ld.get("title"):
                remove_title_from_verses_if_present(ld, ld["title"])

    pallavi_dict = {lang: lang_songs.get(lang, {}).get("pallavi", []) for lang in ["eng","tel","tam","hin"]}
    anupallavi_dict = {lang: lang_songs.get(lang, {}).get("anupallavi", []) for lang in ["eng","tel","tam","hin"]}
    has_c1 = any(bool(v) for v in pallavi_dict.values())
    has_c2 = any(bool(v) for v in anupallavi_dict.values())
    max_verses = max(len(lang_songs.get(lang, {}).get("verses", [])) for lang in ["eng","tel","tam","hin"])

    props = ET.SubElement(song, "properties")
    titles_el = ET.SubElement(props, "titles")
    title_set = []

    if tel_eng_exist:
        for lang in ["eng","tel"]:
            if lang_songs.get(lang) and lang_songs[lang].get("title"):
                title_set.append(lang_songs[lang]["title"])
        title_set.append(master_id)
        for key in ["SongNumber","TamilNumber","HindiNumber"]:
            val = map_row.get(key)
            if val and val != "0" and val not in title_set:
                title_set.append(val)
    else:
        lang_to_mapkey = {"tam":"TamilNumber","hin":"HindiNumber"}
        for lang in ("tam","hin"):
            ld = lang_songs.get(lang, {})
            if ld and ld.get("title"):
                if ld["title"] not in title_set:
                    title_set.append(ld["title"])
                mapkey = lang_to_mapkey.get(lang)
                mapped_num = map_row.get(mapkey) if mapkey else None
                if mapped_num and mapped_num != "0" and mapped_num not in title_set:
                    title_set.append(mapped_num)
                else:
                    if master_id not in title_set:
                        title_set.append(master_id)

    for t in title_set:
        ET.SubElement(titles_el, "title").text = str(t)

    # Verse order logic
    order_list = []
    if max_verses == 0 and not has_c1 and not has_c2:
        order_list = []
    else:
        if not has_c1 and not has_c2:
            order_list = [f"v{i+1}" for i in range(max_verses)]
        elif has_c1 and not has_c2:
            for i in range(max_verses):
                order_list.append("c1")
                order_list.append(f"v{i+1}")
            order_list.append("c1")
        elif not has_c1 and has_c2:
            for i in range(max_verses):
                order_list.append("c2")
                order_list.append(f"v{i+1}")
            order_list.append("c2")
        else:
            order_list.append("c1")
            order_list.append("c2")
            for i in range(max_verses):
                order_list.append(f"v{i+1}")
                order_list.append("c2")
            order_list.append("c1")

    ET.SubElement(props, "verseOrder").text = " ".join(order_list).strip()
    authors = ET.SubElement(props, "authors")
    ET.SubElement(authors, "author").text = "His Servant"
    songbooks = ET.SubElement(props, "songbooks")
    ET.SubElement(songbooks, "songbook", {"name":"Zion Songs","entry":str(master_id)})

    lyrics = ET.SubElement(song, "lyrics")

    def add_lines(lyrics_el, lang_texts_dict, verse_name):
        verse = ET.SubElement(lyrics_el, "verse", {"name": verse_name})
        for lang_code, texts in lang_texts_dict.items():
            if texts:
                verse_text = "{lang-" + lang_code + "}" + "\n".join(texts) + "{/lang-" + lang_code + "}"
                ET.SubElement(verse, "lines").text = verse_text

    if has_c1:
        add_lines(lyrics, pallavi_dict, "c1")
    if has_c2:
        add_lines(lyrics, anupallavi_dict, "c2")
    for idx in range(max_verses):
        lang_lines = {lang: lang_songs.get(lang, {}).get("verses", [])[idx] if idx < len(lang_songs.get(lang, {}).get("verses", [])) else [] for lang in ["eng","tel","tam","hin"]}
        add_lines(lyrics, lang_lines, f"v{idx+1}")

    # ---------------------------
    # Add the "o1" verse with alt numbers from CSV (SongNumber, v1, v2, Tamil, Hindi)
    # ---------------------------
    o1_verse = ET.SubElement(lyrics, "verse", {"name": "o1"})
    o1_lines = ET.SubElement(o1_verse, "lines")
    # We'll produce multiple <tag name="alt_number">value</tag> entries separated by <br/>
    alt_values = []
    # master SongNumber (map_row may or may not contain it)
    master_val = map_row.get("SongNumber") or master_id or ""
    if master_val and master_val != "0":
        alt_values.append(str(master_val))
    # older telugu numbers
    v1 = map_row.get("v1TeluguNo", "") or ""
    v2 = map_row.get("v2TeluguNo", "") or ""
    if v1 and v1 != "0":
        alt_values.append(str(v1))
    if v2 and v2 != "0":
        alt_values.append(str(v2))
    # Tamil and Hindi numbers
    tamnum = map_row.get("TamilNumber", "") or ""
    hinnum = map_row.get("HindiNumber", "") or ""
    if tamnum and tamnum != "0":
        alt_values.append(str(tamnum))
    if hinnum and hinnum != "0":
        alt_values.append(str(hinnum))

    # Create XML children: <tag name="alt_number">value</tag> and <br/> between them
    first = True
    alttext = ""
    for val in alt_values:
        # tag_el = ET.SubElement(o1_lines, "tag", {"name": "alt_number"})
        alttext = "{alt_number}" + str(val) + "{/alt_number}\n" + alttext
        # add a line break element after each tag except maybe the last (adding is harmless)
        # ET.SubElement(o1_lines, "br")
    if alttext:
        o1_lines.text = alttext
    if alt_values:
        log_trace(f"ℹ Added o1 alt numbers for master={master_id}: {alt_values}")

    return song

# ---------------------------
# Save XML
# ---------------------------
def save_song_xml(song_element, master_id, safe_title):
    filename = f"{master_id}_{safe_title}.xml"
    filepath = out_dir / filename
    try:
        ET.ElementTree(song_element).write(filepath, encoding="utf-8", xml_declaration=True)
        log_trace(f"✔ Wrote {filename}")
    except Exception as e:
        log_trace(f"⚠ Failed to write {filename}: {e}")

# ---------------------------
# Main Export Logic
# ---------------------------

# --- Matched songs ---
for tel_no, map_row in song_map.items():
    master_id = map_row.get("SongNumber") or tel_no
    if not master_id or master_id == "0":
        continue

    lang_songs = {}
    # English/Telugu: English keyed by master SongNumber, Telugu keyed by master SongNumber (as before)
    for lang in ["eng","tel"]:
        lang_songs[lang] = all_songs.get(lang, {}).get(master_id, {"title": "", "pallavi": [], "anupallavi": [], "verses": []})

    # Tamil/Hindi pulled by the mapped TamilNumber/HindiNumber (if present)
    for lang, key in [("tam","TamilNumber"),("hin","HindiNumber")]:
        num = map_row.get(key)
        if num and num != "0":
            lang_songs[lang] = all_songs.get(lang, {}).get(num, {"title":"","pallavi":[],"anupallavi":[],"verses":[]})
        else:
            lang_songs[lang] = {"title":"","pallavi":[],"anupallavi":[],"verses":[]}

    # dedupe and write
    dedup_id = (master_id,
                lang_songs["eng"]["title"], lang_songs["tel"]["title"],
                lang_songs["tam"]["title"], lang_songs["hin"]["title"])
    if dedup_id in exported_ids:
        write_duplicate_csv(tel_no, master_id, map_row.get("TamilNumber"), map_row.get("HindiNumber"),
                            {"eng": lang_songs["eng"]["title"], "tel": lang_songs["tel"]["title"],
                             "tam": lang_songs["tam"]["title"], "hin": lang_songs["hin"]["title"]},
                            "Duplicate entry")
        continue
    exported_ids.add(dedup_id)
    processed_master_ids.add(master_id)

    xml_song = create_interleaved_song_xml(master_id, lang_songs, map_row)
    safe_base = lang_songs.get("eng", {}).get("title") or lang_songs.get("tel", {}).get("title") or lang_songs.get("tam", {}).get("title") or lang_songs.get("hin", {}).get("title") or master_id
    safe_title = re.sub(r"[<>:\"/\\|?*]", "_", safe_base)
    save_song_xml(xml_song, master_id, safe_title)

    with export_csv.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            master_id,
            tel_no,
            master_id,
            map_row.get("TamilNumber") or "",
            map_row.get("HindiNumber") or "",
            lang_songs["tel"]["title"],
            lang_songs["eng"]["title"],
            lang_songs["tam"]["title"],
            lang_songs["hin"]["title"]
        ])

# --- Unmatched Tamil ---
for num, song in all_songs.get("tam", {}).items():
    if num in processed_unmatched_tamil_ids:
        continue
    # skip if mapped in the CSV (SongNumber column non-zero references this TamilNumber)
    if any(row.get("TamilNumber") == num for row in song_map.values() if row.get("SongNumber") != "0"):
        continue
    master_id = num
    lang_songs = {"eng":{"title":"","pallavi":[],"anupallavi":[],"verses":[]},
                  "tel":{"title":"","pallavi":[],"anupallavi":[],"verses":[]},
                  "tam": song,
                  "hin":{"title":"","pallavi":[],"anupallavi":[],"verses":[]}}
    dedup_id = (master_id, "", "", song.get("title",""), "")
    if dedup_id in exported_ids:
        write_duplicate_csv("", "", num, "", {"eng":"","tel":"","tam":song.get("title",""),"hin":""},"Duplicate unmatched Tamil")
        continue
    exported_ids.add(dedup_id)
    processed_unmatched_tamil_ids.add(num)

    map_row = {"SongNumber":"", "v1TeluguNo":"", "v2TeluguNo":"", "TamilNumber":num, "HindiNumber":""}
    xml_song = create_interleaved_song_xml(master_id, lang_songs, map_row)
    safe_title = re.sub(r"[<>:\"/\\|?*]", "_", song.get("title","") or master_id)
    save_song_xml(xml_song, master_id, safe_title)
    with export_csv.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([master_id,"","",num,"","","", song.get("title",""),""])

# --- Unmatched Hindi ---
for num, song in all_songs.get("hin", {}).items():
    tel_ref = song.get("tel_ref","TBD").strip()
    if num in processed_unmatched_hindi_ids:
        continue
    # if this hindi number appears in mapping CSV (and mapped SongNumber is non-zero), skip as it's already covered
    if any(row.get("HindiNumber") == num and row.get("SongNumber") != "0" for row in song_map.values()):
        continue
    # If tel_ref is not TBD then it does have a tel ref — skip (we only want truly unmatched)
    if tel_ref.upper() != "TBD":
        continue

    master_id = num
    lang_songs = {"eng":{"title":"","pallavi":[],"anupallavi":[],"verses":[]},
                  "tel":{"title":"","pallavi":[],"anupallavi":[],"verses":[]},
                  "tam":{"title":"","pallavi":[],"anupallavi":[],"verses":[]},
                  "hin": song}
    dedup_id = (master_id, "", "", "", song.get("title",""))
    if dedup_id in exported_ids:
        write_duplicate_csv("", "", "", num, {"eng":"","tel":"","tam":"","hin":song.get("title","")},"Duplicate unmatched Hindi")
        continue
    exported_ids.add(dedup_id)
    processed_unmatched_hindi_ids.add(num)

    map_row = {"SongNumber":"", "v1TeluguNo":"", "v2TeluguNo":"", "TamilNumber":"", "HindiNumber":num}
    xml_song = create_interleaved_song_xml(master_id, lang_songs, map_row)
    safe_title = re.sub(r"[<>:\"/\\|?*]", "_", song.get("title","") or master_id)
    save_song_xml(xml_song, master_id, safe_title)
    with export_csv.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([master_id,"","","",num,"","","", song.get("title","")])

# ---------------------------
# Final Summary
# ---------------------------
total_matched = len(processed_master_ids)
total_unmatched_tamil = len(processed_unmatched_tamil_ids)
total_unmatched_hindi = len(processed_unmatched_hindi_ids)
total_exported = total_matched + total_unmatched_tamil + total_unmatched_hindi

log_trace("\n======================")
log_trace(f"✅ Export Summary:")
log_trace(f"  Matched songs (Telugu/English ± Tamil/Hindi): {total_matched}")
log_trace(f"  Unmatched Tamil songs exported: {total_unmatched_tamil} -> {sorted(processed_unmatched_tamil_ids)}")
log_trace(f"  Unmatched Hindi songs exported: {total_unmatched_hindi} -> {sorted(processed_unmatched_hindi_ids)}")
log_trace(f"  Duplicates skipped: {duplicate_count}")
log_trace(f"  Total songs exported: {total_exported}")
log_trace("======================\n")
