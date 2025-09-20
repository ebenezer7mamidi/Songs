import re
from pathlib import Path

# Directory containing cleaned files
src_dir = Path("SourceFile")
if not src_dir.exists():
    src_dir = Path(r"\SourceFile")  # fallback

# Files to check
eng_file = src_dir / "all_songs_english_cleaned.txt"
tel_file = src_dir / "all_songs_telugu_cleaned.txt"

# Regex to detect verse numbers
verse_number_re = re.compile(r'^(\d+)\.')

def parse_songs(file_path):
    songs = {}
    empty_number_songs = []
    current_song = None
    verse_numbers = []

    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("Song Number:"):
            # Save previous song
            if current_song is not None:
                if current_song.isdigit():  # only store if numeric song number
                    songs[current_song] = verse_numbers
                else:
                    # Store verse numbers as strings to avoid TypeError
                    empty_number_songs.append("\n".join(str(v) for v in verse_numbers))
            # Start new song
            song_num = line.replace("Song Number:", "").strip()
            current_song = song_num
            verse_numbers = []
        else:
            m = verse_number_re.match(line)
            if m:
                verse_numbers.append(int(m.group(1)))

    # Save last song
    if current_song is not None:
        if current_song.isdigit():
            songs[current_song] = verse_numbers
        else:
            empty_number_songs.append("\n".join(str(v) for v in verse_numbers))

    return songs, empty_number_songs

# Parse English and Telugu
eng_songs, eng_empty = parse_songs(eng_file)
tel_songs, tel_empty = parse_songs(tel_file)

# Compare verse counts
all_song_numbers = sorted(set(eng_songs.keys()) | set(tel_songs.keys()), key=int)
mismatch_verses = []

for snum in all_song_numbers:
    eng_count = len(eng_songs.get(snum, []))
    tel_count = len(tel_songs.get(snum, []))
    if eng_count != tel_count:
        mismatch_verses.append((snum, eng_count, tel_count))

# Report
report_file = src_dir / "verse_check_report.txt"
with report_file.open("w", encoding="utf-8") as f:
    f.write("Songs with mismatched verse counts (English vs Telugu):\n")
    for snum, eng_count, tel_count in mismatch_verses:
        f.write(f"Song {snum}: English verses={eng_count}, Telugu verses={tel_count}\n")

    f.write("\nSongs with empty or invalid song numbers in English:\n")
    for v in eng_empty:
        f.write(v + "\n")

    f.write("\nSongs with empty or invalid song numbers in Telugu:\n")
    for v in tel_empty:
        f.write(v + "\n")

print(f"✔ Verse check complete. Report written to {report_file}")
