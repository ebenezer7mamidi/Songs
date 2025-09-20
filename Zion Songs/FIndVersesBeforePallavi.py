#!/usr/bin/env python3
"""
find_verse_before_pallavi.py

Find songs where a "1. " verse occurs AFTER the Title line (EN Title / TE Title)
but BEFORE the Pallavi line (Pallavi / పల్లవి).

Outputs two files in SourceFile:
 - all_songs_english_cleaned_verse_before_pallavi.txt
 - all_songs_telugu_cleaned_verse_before_pallavi.txt

Each output line: <SongNumber> | <Title>
"""
import re
from pathlib import Path

SRC_DIR = Path("SourceFile")
if not SRC_DIR.exists():
    SRC_DIR = Path(r"\SourceFile")  # fallback for Windows

FILES = {
    "english": {
        "fname": "all_songs_english_cleaned.txt",
        "title_prefix": "EN Title:",
        "pallavi_check": lambda s: s.lower().startswith("pallavi"),
    },
    "telugu": {
        "fname": "all_songs_telugu_cleaned.txt",
        "title_prefix": "TE Title:",
        "pallavi_check": lambda s: s.startswith("పల్లవి"),
    },
}

VERSE_RE = re.compile(r'^\s*1\.\s')   # matches lines that begin with "1. "

def find_verse_before_pallavi(file_path: Path, title_prefix: str, pallavi_check) -> list:
    """
    Returns list of (song_number, title) where a line starting with '1. '
    appears between the Title line and the Pallavi line.
    """
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return []

    lines = file_path.read_text(encoding="utf-8").splitlines()
    results = []

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        # detect song start
        if line.startswith("Song Number:"):
            song_num = line.split(":", 1)[1].strip()
            # find the title line for this song
            title_text = ""
            title_index = None
            j = i + 1
            while j < n and not lines[j].strip().startswith("Song Number:"):
                l = lines[j].strip()
                if l.startswith(title_prefix):
                    title_text = l.split(":", 1)[1].strip()
                    title_index = j
                    break
                j += 1

            # if no title found, move on
            if title_index is None:
                i += 1
                continue

            # find pallavi line within this same song block
            k = title_index + 1
            pallavi_index = None
            while k < n and not lines[k].strip().startswith("Song Number:"):
                l = lines[k].strip()
                if pallavi_check(l):
                    pallavi_index = k
                    break
                k += 1

            # if no pallavi found, skip (nothing to compare)
            if pallavi_index is None:
                i = k
                continue

            # check for any '1. ' line between title_index and pallavi_index
            found_verse_before_pallavi = False
            for m in range(title_index + 1, pallavi_index):
                if VERSE_RE.match(lines[m]):
                    found_verse_before_pallavi = True
                    break

            if found_verse_before_pallavi:
                results.append((song_num, title_text))

            # continue scanning after the pallavi_index
            i = pallavi_index + 1
            continue

        i += 1

    return results


def main():
    for lang, cfg in FILES.items():
        infile = SRC_DIR / cfg["fname"]
        outname = infile.with_name(infile.stem + "_verse_before_pallavi.txt")
        matches = find_verse_before_pallavi(infile, cfg["title_prefix"], cfg["pallavi_check"])
        if matches:
            # write "SongNumber | Title" lines
            lines_out = [f"{num} | {title}" for num, title in matches]
            outname.write_text("\n".join(lines_out), encoding="utf-8")
            print(f"Found {len(matches)} problematic songs in {cfg['fname']} → wrote {outname.name}")
        else:
            # write empty file (or optionally skip writing)
            outname.write_text("", encoding="utf-8")
            print(f"No problematic songs found in {cfg['fname']}. Wrote empty {outname.name}")

if __name__ == "__main__":
    main()
