#!/usr/bin/env python3
"""
compare_anupallavi.py

Compares English and Telugu cleaned song files:
- Lists songs where English has 'Anupallavi' but Telugu does not have 'అనుపల్లవి'
- Outputs the Song Numbers and Titles to a report file
"""

from pathlib import Path
import re

SRC_DIR = Path("SourceFile")
EN_FILE = SRC_DIR / "all_songs_english_cleaned.txt"
TE_FILE = SRC_DIR / "all_songs_telugu_cleaned.txt"
REPORT_FILE = SRC_DIR / "anupallavi_missing_telugu.txt"


def split_songs(file_path):
    """Splits a cleaned song file into a dict keyed by Song Number."""
    songs = {}
    lines = file_path.read_text(encoding="utf-8").splitlines()
    current_number = None
    current_title = None
    current_lines = []

    for line in lines:
        line = line.strip()
        if line.startswith("Song Number:"):
            # save previous song
            if current_number:
                songs[current_number] = {"title": current_title, "lines": current_lines}
            # start new song
            current_number = line.replace("Song Number:", "").strip()
            current_lines = []
            current_title = None
        elif line.startswith("EN Title:") or line.startswith("TE Title:"):
            current_title = line.replace("EN Title:", "").replace("TE Title:", "").strip()
        else:
            current_lines.append(line)

    # save last song
    if current_number:
        songs[current_number] = {"title": current_title, "lines": current_lines}

    return songs


def main():
    en_songs = split_songs(EN_FILE)
    te_songs = split_songs(TE_FILE)

    report_lines = ["Songs where English has Anupallavi but Telugu does NOT:\n"]

    for snum, en_song in en_songs.items():
        te_song = te_songs.get(snum)
        if not te_song:
            continue  # skip if no Telugu song with same number
        en_has = any("Anupallavi" in line for line in en_song["lines"])
        te_has = any("అనుపల్లవి" in line for line in te_song["lines"])

        if en_has and not te_has:
            report_lines.append(f"Song Number: {snum}")
            report_lines.append(f"EN Title: {en_song['title']}")
            report_lines.append(f"TE Title: {te_song['title'] if te_song['title'] else ''}")
            report_lines.append("")  # blank line between songs

    REPORT_FILE.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"✅ Report generated: {REPORT_FILE}")


if __name__ == "__main__":
    main()
