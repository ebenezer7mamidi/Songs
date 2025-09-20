from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# --- Setup Selenium ---
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)

base_url = "https://songsofzion.org"
book_url = f"{base_url}/book/1"

driver.get(book_url)
time.sleep(2)

# Get all song links
song_divs = driver.find_elements(By.CSS_SELECTOR, "div.book-song-div-a a")
song_links = [a.get_attribute("href") for a in song_divs]

# --- XML helper functions ---
def create_song_root():
    root = ET.Element("song", xmlns="http://openlyrics.info/namespace/2009/song",
                      version="0.8",
                      createdIn="OpenLP 2.9.5",
                      modifiedIn="OpenLP 2.9.5",
                      modifiedDate=datetime.now().isoformat())
    properties = ET.SubElement(root, "properties")
    titles = ET.SubElement(properties, "titles")
    ET.SubElement(properties, "verseOrder")
    ET.SubElement(properties, "authors")
    ET.SubElement(properties, "songbooks")
    lyrics = ET.SubElement(root, "lyrics")
    return root, properties, lyrics

def capitalize_english_line(line):
    return line[:1].upper() + line[1:] if line else line

def parse_lyrics_en_only(lyrics_text):
    lines = [line.strip() for line in lyrics_text.split("\n") if line.strip()]
    verses = []
    verse_order = []
    
    chorus_map = {}
    v_counter = 1
    c_counter = 1
    
    for line in lines:
        is_chorus = False
        if "||" in line:
            is_chorus = True
            line_clean = line.replace("||", "").strip()
            if line_clean not in chorus_map:
                chorus_map[line_clean] = f"C{c_counter}"
                c_counter += 1
            verse_name = chorus_map[line_clean]
        else:
            line_clean = line.strip()
            verse_name = f"V{v_counter}"
            v_counter += 1
        
        verse_order.append(verse_name)
        verses.append((verse_name, [capitalize_english_line(line_clean)]))
    
    return verses, " ".join(verse_order)

def parse_lyrics_interleaved(en_text, te_text):
    en_lines = [line.strip() for line in en_text.split("\n") if line.strip()]
    te_lines = [line.strip() for line in te_text.split("\n") if line.strip()]
    
    max_len = max(len(en_lines), len(te_lines))
    verses = []
    verse_order = []
    
    c_counter = 1
    v_counter = 1
    
    for i in range(max_len):
        en_line = en_lines[i] if i < len(en_lines) else ""
        te_line = te_lines[i] if i < len(te_lines) else ""
        
        is_chorus = False
        if "||" in en_line or "||" in te_line:
            is_chorus = True
            en_line = en_line.replace("||", "").strip()
            te_line = te_line.replace("||", "").strip()
        
        # Capitalize English
        if en_line:
            en_line = en_line[:1].upper() + en_line[1:]
        
        combined_line = f"{en_line} | {te_line}" if en_line else te_line
        
        verse_name = f"C{c_counter}" if is_chorus else f"V{v_counter}"
        if is_chorus:
            c_counter += 1
        else:
            v_counter += 1
        
        verse_order.append(verse_name)
        verses.append((verse_name, [combined_line]))
    
    return verses, " ".join(verse_order)

def add_song_xml(root, song_number, song_title, verses, verse_order):
    song_root, properties, lyrics_elem = create_song_root()
    
    titles = properties.find("titles")
    ET.SubElement(titles, "title").text = song_title
    ET.SubElement(titles, "title").text = song_number
    properties.find("verseOrder").text = verse_order
    
    for verse_name, lines in verses:
        verse_elem = ET.SubElement(lyrics_elem, "verse", name=verse_name)
        for line in lines:
            ET.SubElement(verse_elem, "lines").text = line
    
    root.append(song_root)

# --- Create XML roots ---
english_root = ET.Element("songs")
telugu_root = ET.Element("songs")
interleaved_root = ET.Element("songs")

# --- Scrape each song ---
for idx, url in enumerate(song_links, start=1):
    driver.get(url)
    
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CLASS_NAME, "tab-content"))
    )
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    h4 = soup.find("h4").get_text(strip=True)
    if ". " in h4:
        song_number, song_title = h4.split(".", 1)
        song_number = song_number.strip()
        song_title = song_title.strip()
    else:
        song_number = ""
        song_title = h4
    
    tab_content = soup.find("div", class_="tab-content")
    
    english_div = tab_content.find("div", id=lambda x: x and "English" in x)
    english_lyrics = english_div.get_text(separator="\n", strip=True) if english_div else ""
    
    telugu_div = tab_content.find("div", id=lambda x: x and "Translation" in x)
    telugu_lyrics = telugu_div.get_text(separator="\n", strip=True) if telugu_div else ""
    
    # English XML
    en_verses, en_order = parse_lyrics_en_only(english_lyrics)
    add_song_xml(english_root, song_number, song_title, en_verses, en_order)
    
    # Telugu XML
    te_verses, te_order = parse_lyrics_interleaved("", telugu_lyrics)
    add_song_xml(telugu_root, song_number, song_title, te_verses, te_order)
    
    # Interleaved XML
    inter_verses, inter_order = parse_lyrics_interleaved(english_lyrics, telugu_lyrics)
    add_song_xml(interleaved_root, song_number, song_title, inter_verses, inter_order)
    
    print(f"{idx}/{len(song_links)}: Processed '{song_title}'")
    time.sleep(0.5)

driver.quit()

# --- Save XML files ---
ET.ElementTree(english_root).write("songs_english.xml", encoding="utf-8", xml_declaration=True)
ET.ElementTree(telugu_root).write("songs_telugu.xml", encoding="utf-8", xml_declaration=True)
ET.ElementTree(interleaved_root).write("songs_interleaved.xml", encoding="utf-8", xml_declaration=True)

print("All three XML files saved with proper capitalization and interleaving.")
