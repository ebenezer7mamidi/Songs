import os
import re
import xml.etree.ElementTree as ET

# ------------------------------
# Relative Paths
# ------------------------------
input_folder = os.path.join('.', 'OneDrive_2024-12-31', 'Christ in Song')
output_folder = os.path.join('.', 'SourceFiles')
output_file = os.path.join(output_folder, 'all_songs.txt')

# Ensure output folder exists
os.makedirs(output_folder, exist_ok=True)

# ------------------------------
# XML Namespace
# ------------------------------
ns = {'ol': 'http://openlyrics.info/namespace/2009/song'}

# ------------------------------
# Helper: clean text and remove chord lines
# ------------------------------
def clean_lines(text: str) -> str:
    """
    Remove chord-only lines (like D, D/E, G#m7, etc.)
    and labels like 'Verse 1', 'Chorus 2', 'Bridge'
    """
    cleaned = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Chord patterns
        if re.match(r'^[A-G][#b]?(m|min|maj|dim|aug)?\d*(/[A-G][#b]?(m|min|maj|dim|aug)?\d*)*$', stripped):
            continue
        # Labels
        if re.match(r'^(verse|chorus|bridge|tag|refrain)\b.*$', stripped, re.IGNORECASE):
            continue
        cleaned.append(stripped)
    return '\n'.join(cleaned)

# ------------------------------
# Helper function to extract text including <br/> as new lines
# ------------------------------
def get_full_text(lines_el):
    if lines_el is None:
        return ""
    parts = []
    if lines_el.text:
        parts.append(lines_el.text.strip())
    for child in lines_el:
        if child.tag.endswith('br'):
            parts.append('\n')
        if child.tail:
            parts.append(child.tail.strip())
    raw = ''.join(parts).strip()
    return clean_lines(raw)

# ------------------------------
# Function to process a single XML file
# ------------------------------
def process_song(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError:
        return "", float('inf')
    except Exception:
        return "", float('inf')

    # Extract song number and title
    titles_element = root.find('ol:properties/ol:titles', ns)
    en_title = "Unknown Title"
    song_number = float('inf')
    if titles_element is not None:
        title_list = titles_element.findall('ol:title', ns)
        if len(title_list) > 1 and title_list[0].text:
            en_title = title_list[0].text.strip()
            song_number_text = title_list[1].text.strip() if title_list[1].text else ""
            try:
                song_number = int(song_number_text)
            except Exception:
                song_number = float('inf')
        elif len(title_list) == 1 and title_list[0].text:
            full_title = title_list[0].text.strip()
            m = re.match(r'^\s*(\d+)\b\s*(.*)$', full_title)
            if m:
                try:
                    song_number = int(m.group(1))
                except Exception:
                    song_number = float('inf')
                en_title = m.group(2).strip() or full_title
            else:
                en_title = full_title
    else:
        sb = root.find('ol:properties/ol:songbooks/ol:songbook', ns)
        if sb is not None and sb.get('entry'):
            try:
                song_number = int(sb.get('entry'))
            except Exception:
                song_number = float('inf')

    # Extract verses
    verse_elems = root.findall('ol:lyrics/ol:verse', ns)
    chorus_dict = {}
    verse_texts_dict = {}

    for v in verse_elems:
        name = v.attrib.get('name', '').strip().lower()
        lines_el = v.find('ol:lines', ns)
        text = get_full_text(lines_el)
        if not text:
            continue

        # Choruses
        if name.startswith('c'):
            m = re.match(r'^c(\d+)$', name)
            num = int(m.group(1)) if m else max(chorus_dict.keys(), default=0) + 1
            if num in chorus_dict:
                chorus_dict[num] += '\n' + text
            else:
                chorus_dict[num] = text
        # Verses (merge v1a, v1b -> v1)
        elif name.startswith('v'):
            base_match = re.match(r'^(v\d+)', name)
            base_name = base_match.group(1) if base_match else name
            if base_name in verse_texts_dict:
                verse_texts_dict[base_name] += '\n' + text
            else:
                verse_texts_dict[base_name] = text
        else:
            # Other
            verse_texts_dict[name] = text

    # Build VerseOrder as v1 c1 v2 c1 v3 c1 ... if chorus exists
    sorted_verses = sorted(
        verse_texts_dict.keys(),
        key=lambda x: int(re.match(r'v(\d+)', x).group(1)) if re.match(r'v(\d+)', x) else float('inf')
    )

    verse_order_parts = []
    if chorus_dict:
        for v in sorted_verses:
            verse_order_parts.append(v)
            verse_order_parts.append(f"c1")
    else:
        verse_order_parts = sorted_verses

    verse_order_str = ' '.join(verse_order_parts)

    # Build song text
    song_lines = [
        f"SongNumber: {song_number if song_number != float('inf') else 'Unknown'}",
        f"SongTitle: {en_title}",
        f"VerseOrder: {verse_order_str}"
    ]

    # Add choruses
    for num in sorted(chorus_dict.keys()):
        song_lines.append(f"Chorus{num} : {chorus_dict[num]}")

    # Add verses
    for idx, v in enumerate(sorted_verses, 1):
        song_lines.append(f"{idx}. {verse_texts_dict[v]}")

    return '\n'.join(song_lines) + '\n\n', song_number

# ------------------------------
# Process all XML files
# ------------------------------
if not os.path.exists(input_folder):
    print(f"Input folder does not exist: {input_folder}")
else:
    songs_list = []

    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.xml'):
            file_path = os.path.join(input_folder, filename)
            song_text, song_number = process_song(file_path)
            if not song_text.strip():
                continue
            songs_list.append((song_number, song_text))

    # Sort songs by number
    songs_list.sort(key=lambda x: x[0])
    all_songs_text = ''.join(song_text for _, song_text in songs_list)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(all_songs_text)

    print(f"All songs exported to {output_file}")
    print(f"Total songs processed: {len(songs_list)}")
