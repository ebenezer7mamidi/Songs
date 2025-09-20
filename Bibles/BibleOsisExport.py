import xml.etree.ElementTree as ET

# --- Input files ---
english_file = "EnglishBible.xml"
telugu_file = "TeluguBible.xml"
tamil_file = "Tamil2017Bible.xml"
hindi_file = "HindiOVBSIBible.xml"
nepali_file = "Nepali2021Bible.xml"
output_file = "MergedBible.osis.xml"
log_file = "merge_warnings.log"

# --- Telugu book number mapping (Old + New Testament) ---
telugu_book_names = {
    "1": "Genesis", "2": "Exodus", "3": "Leviticus", "4": "Numbers", "5": "Deuteronomy",
    "6": "Joshua", "7": "Judges", "8": "Ruth", "9": "1 Samuel", "10": "2 Samuel",
    "11": "1 Kings", "12": "2 Kings", "13": "1 Chronicles", "14": "2 Chronicles", "15": "Ezra",
    "16": "Nehemiah", "17": "Esther", "18": "Job", "19": "Psalms", "20": "Proverbs",
    "21": "Ecclesiastes", "22": "Song of Solomon", "23": "Isaiah", "24": "Jeremiah", "25": "Lamentations",
    "26": "Ezekiel", "27": "Daniel", "28": "Hosea", "29": "Joel", "30": "Amos",
    "31": "Obadiah", "32": "Jonah", "33": "Micah", "34": "Nahum", "35": "Habakkuk",
    "36": "Zephaniah", "37": "Haggai", "38": "Zechariah", "39": "Malachi",
    "40": "Matthew", "41": "Mark", "42": "Luke", "43": "John", "44": "Acts",
    "45": "Romans", "46": "1 Corinthians", "47": "2 Corinthians", "48": "Galatians", "49": "Ephesians",
    "50": "Philippians", "51": "Colossians", "52": "1 Thessalonians", "53": "2 Thessalonians", "54": "1 Timothy",
    "55": "2 Timothy", "56": "Titus", "57": "Philemon", "58": "Hebrews", "59": "James",
    "60": "1 Peter", "61": "2 Peter", "62": "1 John", "63": "2 John", "64": "3 John",
    "65": "Jude", "66": "Revelation"
}

# --- Book name corrections ---
book_name_corrections = {
    "Psalm": "Psalms",
    "Song Of Solomon": "Song of Solomon"
}

# --- Parse XML roots ---
eng_root = ET.parse(english_file).getroot()
tel_root = ET.parse(telugu_file).getroot()
tam_root = ET.parse(tamil_file).getroot()
hin_root = ET.parse(hindi_file).getroot()
nep_root = ET.parse(nepali_file).getroot()

# --- Create OSIS root ---
osis = ET.Element("osis", {
    "xmlns": "http://www.bibletechnologies.net/2003/OSIS/namespace",
    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "xsi:schemaLocation": "http://www.bibletechnologies.net/2003/OSIS/namespace http://www.bibletechnologies.net/osisCore.2.1.1.xsd"
})

# --- Header ---
header = ET.SubElement(osis, "header")
ET.SubElement(header, "work").text = "Merged English-Telugu-Tamil-Hindi-Nepali Bible"
ET.SubElement(header, "title").text = "Merged English-Telugu-Tamil-Hindi-Nepali Bible"
ET.SubElement(header, "language").text = "ENG-TEL-TAM-HIN-NEP"

# --- osisText ---
osis_text = ET.SubElement(osis, "osisText", {"osisIDWork": "MergedBible", "language": "ENG-TEL-TAM-HIN-NEP"})

# --- Helper functions ---
def normalize_book_name(name):
    n = name.title()
    return book_name_corrections.get(n, n)

def build_verse_dict(root, version):
    verses = {}
    for testament in root.findall("testament"):
        for book in testament.findall("book"):
            bnum = book.attrib["number"]
            bname = normalize_book_name(telugu_book_names.get(bnum, f"Book{bnum}"))
            verses[bname] = {}
            for chapter in book.findall("chapter"):
                cnum = chapter.attrib["number"]
                verses[bname][cnum] = {}
                for verse in chapter.findall("verse"):
                    vnum = verse.attrib["number"]
                    verses[bname][cnum][vnum] = verse.text or ""
    # English Zefania special format
    if version == "Zefania":
        verses_eng = {}
        for book in root.findall("BIBLEBOOK"):
            bname = normalize_book_name(book.attrib["bname"])
            verses_eng[bname] = {}
            for chapter in book.findall("CHAPTER"):
                cnum = chapter.attrib["cnumber"]
                verses_eng[bname][cnum] = {}
                for verse in chapter.findall("VERS"):
                    vnum = verse.attrib["vnumber"]
                    verses_eng[bname][cnum][vnum] = verse.text or ""
        return verses_eng
    return verses

# --- Build verse dictionaries ---
eng_verses = build_verse_dict(eng_root, "Zefania")
tel_verses = build_verse_dict(tel_root, "Telugu")
tam_verses = build_verse_dict(tam_root, "Tamil")
hin_verses = build_verse_dict(hin_root, "Hindi")
nep_verses = build_verse_dict(nep_root, "Nepali")

warnings = []

# --- Merge all verses ---
for bname, chapters in tel_verses.items():
    book_div = ET.SubElement(osis_text, "div", {"type": "book", "osisID": bname})
    for cnum, verses in chapters.items():
        chapter_elem = ET.SubElement(book_div, "chapter", {"osisID": f"{bname}.{cnum}"})
        for vnum, tel_text in verses.items():
            eng_text = eng_verses.get(bname, {}).get(cnum, {}).get(vnum, "")
            tam_text = tam_verses.get(bname, {}).get(cnum, {}).get(vnum, "")
            hin_text = hin_verses.get(bname, {}).get(cnum, {}).get(vnum, "")
            nep_text = nep_verses.get(bname, {}).get(cnum, {}).get(vnum, "")

            # Record missing verses
            if not eng_text:
                warnings.append(f"WARNING: Missing English verse for {bname} {cnum}:{vnum}")
            if not tel_text:
                warnings.append(f"WARNING: Missing Telugu verse for {bname} {cnum}:{vnum}")
            if not tam_text:
                warnings.append(f"WARNING: Missing Tamil verse for {bname} {cnum}:{vnum}")
            if not hin_text:
                warnings.append(f"WARNING: Missing Hindi verse for {bname} {cnum}:{vnum}")
            if not nep_text:
                warnings.append(f"WARNING: Missing Nepali verse for {bname} {cnum}:{vnum}")

            verse_elem = ET.SubElement(chapter_elem, "verse", {"osisID": f"{bname}.{cnum}.{vnum}"})
            verse_elem.text = (
                f"{{lang-eng}}<sup>{cnum}:{vnum}</sup>{eng_text}{{/lang-eng}} "
                f"{{lang-tel}}<sup>{cnum}:{vnum}</sup>{tel_text}{{/lang-tel}} "
                f"{{lang-tam}}<sup>{cnum}:{vnum}</sup>{tam_text}{{/lang-tam}} "
                f"{{lang-hin}}<sup>{cnum}:{vnum}</sup>{hin_text}{{/lang-hin}} "
                f"{{lang-nep}}<sup>{cnum}:{vnum}</sup>{nep_text}{{/lang-nep}}"
            )

# --- Write output ---
ET.ElementTree(osis).write(output_file, encoding="utf-8", xml_declaration=True)

# --- Write warnings ---
with open(log_file, "w", encoding="utf-8") as f:
    for w in warnings:
        f.write(w + "\n")

print(f"Merged OSIS Bible saved to {output_file}")
print(f"Warnings saved to {log_file}")
