from pathlib import Path

# Source directory
src_dir = Path("SourceFile")
if not src_dir.exists():
    src_dir = Path(r"\SourceFile")  # fallback for Windows

# Files
english_file = src_dir / "all_songs_english_cleaned.txt"
telugu_file = src_dir / "all_songs_telugu_cleaned.txt"

def list_songs_without_keyword(file_path, keyword):
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return []

    lines = file_path.read_text(encoding="utf-8").splitlines()
    songs_missing_keyword = []
    song_number = ""
    song_title = ""
    inside_song = False

    for line in lines:
        line = line.strip()
        if line.startswith("Song Number:"):
            song_number = line.split(":", 1)[1].strip()
            song_title = ""
            inside_song = True
            song_has_keyword = False
            continue
        if inside_song and (line.startswith("EN Title:") or line.startswith("TE Title:")):
            song_title = line.split(":", 1)[1].strip()
            if keyword.lower() in song_title.lower():
                song_has_keyword = True
            continue
        if inside_song and line and not (line.startswith("Song Number:") or line.startswith("EN Title:") or line.startswith("TE Title:")):
            if keyword.lower() in line.lower():
                song_has_keyword = True
        if inside_song and line == "":
            # End of song
            if not song_has_keyword:
                songs_missing_keyword.append(f"{song_number}. {song_title}")
            inside_song = False

    return songs_missing_keyword

def write_missing_songs(file_path, keyword, out_file_name):
    missing_songs = list_songs_without_keyword(file_path, keyword)
    if missing_songs:
        out_file = file_path.parent / out_file_name
        out_file.write_text("\n".join(missing_songs), encoding="utf-8")
        print(f"✔ Written {len(missing_songs)} songs missing '{keyword}' → {out_file.name}")
    else:
        print(f"No songs missing '{keyword}' found in {file_path.name}")

# Process English
write_missing_songs(english_file, "Pallavi", "all_songs_english_missing_pallavi.txt")

# Process Telugu
write_missing_songs(telugu_file, "పల్లవి", "all_songs_telugu_missing_pallavi.txt")
