import os
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
# Helper function to extract text including <br/> as new lines
# ------------------------------
def get_full_text(lines_el):
    """Extract full text from <lines>, replacing <br/> with newline and trimming spaces."""
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
    return ''.join(parts).strip()

# ------------------------------
# Function to process a single XML file
# ------------------------------
def process_song(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"[ParseError] Skipping file: {file_path}")
        print(f"  Error message: {e}")
        return "", float('inf')
    except Exception as e:
        print(f"[Error] Skipping file: {file_path}")
        print(f"  Unexpected error: {e}")
        return "", float('inf')

    # Extract titles
    titles_element = root.find('ol:properties/ol:titles', ns)
    if titles_element is None:
        print(f"[Warning] Missing <titles> in file: {file_path}")
        en_title = "Unknown Title"
        song_number = float('inf')
    else:
        title_list = titles_element.findall('ol:title', ns)
        en_title = title_list[0].text.strip() if len(title_list) > 0 and title_list[0].text else "Unknown Title"
        song_number_text = title_list[1].text.strip() if len(title_list) > 1 and title_list[1].text else "0"
        try:
            song_number = int(song_number_text)
        except ValueError:
            print(f"[Warning] Invalid song number '{song_number_text}' in file: {file_path}")
            song_number = float('inf')

    # Verse order
    verse_order_el = root.find('ol:properties/ol:verseOrder', ns)
    verse_order = verse_order_el.text.strip() if verse_order_el is not None and verse_order_el.text else ""

    # Lyrics
    verses = root.findall('ol:lyrics/ol:verse', ns)
    chorus_dict = {}  # Map chorus number to text
    verse_texts = []

    for v in verses:
        name = v.attrib.get('name', '').lower()
        lines_el = v.find('ol:lines', ns)
        lines = get_full_text(lines_el)
        if not lines:
            continue

        if name.startswith('c'):
            # Label choruses as Chorus1, Chorus2, ...
            try:
                number = int(name[1:])
                chorus_dict[number] = lines
            except ValueError:
                next_num = len(chorus_dict) + 1
                chorus_dict[next_num] = lines
        elif name.startswith('v'):
            verse_texts.append(lines)

    # Build song text WITHOUT any blank lines and trimmed
    song_lines = [
        f"SongNumber: {song_number if song_number != float('inf') else 'Unknown'}",
        f"SongTitle: {en_title}",
        f"VerseOrder: {verse_order}"
    ]

    # Add choruses in order immediately after VerseOrder
    for num in sorted(chorus_dict.keys()):
        song_lines.append(f"Chorus{num} : {chorus_dict[num]}")

    # Add verses immediately after choruses (no blank lines)
    for idx, verse in enumerate(verse_texts, 1):
        song_lines.append(f"{idx}. {verse}")

    # Separate songs with exactly one double newline
    return '\n'.join(song_lines) + '\n\n', song_number

# ------------------------------
# Process all XML files in folder and sort by song number
# ------------------------------
if not os.path.exists(input_folder):
    print(f"Input folder does not exist: {input_folder}")
else:
    songs_list = []

    # Read all songs and store (song_number, song_text)
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.xml'):
            file_path = os.path.join(input_folder, filename)
            song_text, song_number = process_song(file_path)
            if not song_text.strip():
                print(f"[Skipped] Empty or invalid song from file: {file_path}")
                continue
            songs_list.append((song_number, song_text))

    # Sort songs by number
    songs_list.sort(key=lambda x: x[0])

    # Combine all songs
    all_songs_text = ''.join(song_text for _, song_text in songs_list)

    # Write output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(all_songs_text)

    print(f"All songs exported to {output_file}")
    print(f"Total songs processed: {len(songs_list)}")
