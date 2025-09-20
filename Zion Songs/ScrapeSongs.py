from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import re

# --- Setup Selenium ---
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")  # Run in background
driver = webdriver.Chrome(options=chrome_options)

base_url = "https://songsofzion.org"
book_url = f"{base_url}/book/1"

driver.get(book_url)
time.sleep(2)  # Wait for page to load

# Get all song links
song_divs = driver.find_elements(By.CSS_SELECTOR, "div.book-song-div-a a")
song_links = [a.get_attribute("href") for a in song_divs]

# --- Functions ---
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

def parse_lyrics_repeated(lyrics_text):
    lines = [line.strip() for line in lyrics_text.split("\n") if line.strip()]
    verses = []
    verse_order = []
    
    chorus_map = {}
    v_counter = 1
    c_counter = 1
    
    for line in lines:
        if re.search(r"\|\|.*\|\|", line):
            chorus_text = line.strip()
            if chorus_text not in chorus_map:
                chorus_map[chorus_text] = f"C{c_counter}"
                c_counter += 1
            verse_name = chorus_map[chorus_text]
            verse_order.append(verse_name)
            chorus_lines = [l.strip() for l in re.split(r"\|\|", chorus_text) if l.strip()]
            verses.append((verse_name, chorus_lines))
        else:
            verse_name = f"V{v_counter}"
            v_counter += 1
            verse_order.append(verse_name)
            verses.append((verse_name, [line]))
    
    return verses, " ".join(verse_order)

def add_song_xml(root, song_number, song_title, lyrics_text):
    song_root, properties, lyrics_elem = create_song_root()
    
    titles = properties.find("titles")
    ET.SubElement(titles, "title").text = song_title
    ET.SubElement(titles, "title").text = song_number
    
    verses, verse_order = parse_lyrics_repeated(lyrics_text)
    properties.find("verseOrder").text = verse_order
    
    for verse_name, lines in verses:
        verse_elem = ET.SubElement(lyrics_elem, "verse", name=verse_name)
        for line in lines:
            ET.SubElement(verse_elem, "lines").text = line
    
    root.append(song_root)

# XML roots
english_root = ET.Element("songs")
telugu_root = ET.Element("songs")

# --- Scrape songs ---
for idx, url in enumerate(song_links, start=1):
    driver.get(url)
    
    # Wait for tab content to load
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CLASS_NAME, "tab-content"))
    )
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Song number and title
    h4 = soup.find("h4").get_text(strip=True)
    if ". " in h4:
        song_number, song_title = h4.split(".", 1)
        song_number = song_number.strip()
        song_title = song_title.strip()
    else:
        song_number = ""
        song_title = h4
    
    tab_content = soup.find("div", class_="tab-content")
    
    # English lyrics
    english_div = tab_content.find("div", id=lambda x: x and "English" in x)
    english_lyrics = english_div.get_text(separator="\n", strip=True) if english_div else ""
    
    # Telugu lyrics
    telugu_div = tab_content.find("div", id=lambda x: x and "Translation" in x)
    telugu_lyrics = telugu_div.get_text(separator="\n", strip=True) if telugu_div else ""
    
    add_song_xml(english_root, song_number, song_title, english_lyrics)
    add_song_xml(telugu_root, song_number, song_title, telugu_lyrics)
    
    print(f"{idx}/{len(song_links)}: Scraped '{song_title}'")
    time.sleep(0.5)

# Save XML files
ET.ElementTree(english_root).write("songs_english.xml", encoding="utf-8", xml_declaration=True)
ET.ElementTree(telugu_root).write("songs_telugu.xml", encoding="utf-8", xml_declaration=True)

driver.quit()
print("Scraping completed! Files saved as songs_english.xml and songs_telugu.xml")
