from pathlib import Path
import re

# Source cleaned files
FILES = {
    "telugu": Path(r"SourceFile/all_songs_telugu_cleaned.txt"),
    "english": Path(r"SourceFile/all_songs_english_cleaned.txt"),
}

# Regex
song_number_re = re.compile(r"^Song Number: (\d+)")
pallavi_re = {
    "telugu": re.compile(r"^పల్లవి\s*:"),
    "english": re.compile(r"^Pallavi\s*:", re.IGNORECASE),
}
anupallavi_re = {
    "telugu": re.compile(r"^అనుపల్లవి\s*:"),
    "english": re.compile(r"^Anupallavi\s*:", re.IGNORECASE),
}


def validate_file(lang: str, filepath: Path):
    try:
        with filepath.open(encoding="utf-8") as f:
            lines = [l.rstrip() for l in f]
    except FileNotFoundError:
        print(f"⚠ File {filepath} not found. Skipping {lang}.")
        return []

    songs_with_issue = []

    song_num = None
    has_pallavi = False
    has_anupallavi = False

    def check_and_reset():
        nonlocal song_num, has_pallavi, has_anupallavi
        if song_num:
            if has_anupallavi and not has_pallavi:
                songs_with_issue.append(song_num)
        song_num = None
        has_pallavi = False
        has_anupallavi = False

    for line in lines + [""]:  # extra "" to flush last song
        if not line.strip():
            check_and_reset()
            continue

        if line.startswith("Song Number:"):
            check_and_reset()
            m = song_number_re.match(line)
            if m:
                song_num = m.group(1)
        elif pallavi_re[lang].match(line):
            has_pallavi = True
        elif anupallavi_re[lang].match(line):
            has_anupallavi = True

    return songs_with_issue


if __name__ == "__main__":
    for lang, filepath in FILES.items():
        issues = validate_file(lang, filepath)
        if issues:
            print(f"⚠ {lang.title()} songs with Anupallavi but no Pallavi:")
            for s in issues:
                print(" ", s)
        else:
            print(f"✔ No issues found in {lang.title()} songs.")
