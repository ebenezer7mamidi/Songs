from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re

# --- Setup Selenium ---
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)

base_url = "https://songsofzion.org"
book_url = f"{base_url}/book/1"

# --- Collect all song URLs ---
driver.get(book_url)
time.sleep(2)

song_divs = driver.find_elements(By.CSS_SELECTOR, "div.book-song-div-a a")
song_links = [a.get_attribute("href") for a in song_divs]

# Prepare aggregated song texts
english_all = []
telugu_all = []
interleaved_all = []

# --- Function to split into blocks (chorus/verse) ---
def split_blocks(lines):
    blocks = []
    current_block = []
    is_chorus = False
    for line in lines:
        if "||" in line:
            if current_block:
                blocks.append((is_chorus, current_block))
            current_block = [line.replace("||", "").strip()]
            is_chorus = True
            blocks.append((is_chorus, current_block))
            current_block = []
            is_chorus = False
        else:
            current_block.append(line)
    if current_block:
        blocks.append((is_chorus, current_block))
    return blocks

# --- Scrape each song ---
for idx, url in enumerate(song_links, start=1):
    driver.get(url)
    
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
    english_lines = [line.strip() for line in english_lyrics.split("\n") if line.strip()]
    
    # Telugu lyrics
    telugu_div = tab_content.find("div", id=lambda x: x and "Translation" in x)
    telugu_lyrics = telugu_div.get_text(separator="\n", strip=True) if telugu_div else ""
    telugu_lines = [line.strip() for line in telugu_lyrics.split("\n") if line.strip()]
    
    # --- Save English and Telugu separately ---
    english_all.append(f"{song_number}. {song_title}\n" + "\n".join(english_lines) + "\n\n")
    telugu_all.append(f"{song_number}. {song_title}\n" + "\n".join(telugu_lines) + "\n\n")
    
    # --- Interleaved with chorus first ---
    interleaved = [f"{song_number}. {song_title}"]
    
    en_blocks = split_blocks(english_lines)
    te_blocks = split_blocks(telugu_lines)
    
    # Make sure blocks match in count
    max_blocks = max(len(en_blocks), len(te_blocks))
    
    for i in range(max_blocks):
        # English block
        if i < len(en_blocks):
            is_chorus, lines_en = en_blocks[i]
            for line in lines_en:
                prefix = "CHORUS EN:" if is_chorus else "EN:"
                interleaved.append(f"{prefix} {line}")
        # Telugu block
        if i < len(te_blocks):
            is_chorus, lines_te = te_blocks[i]
            for line in lines_te:
                prefix = "CHORUS TE:" if is_chorus else "TE:"
                interleaved.append(f"{prefix} {line}")
        interleaved.append("")  # blank line between blocks
    
    interleaved_all.append("\n".join(interleaved))
    
    print(f"{idx}/{len(song_links)}: Processed '{song_title}'")
    time.sleep(0.5)

driver.quit()

# --- Save files ---
with open("all_songs_english.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(english_all))

with open("all_songs_telugu.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(telugu_all))

with open("all_songs_interleaved.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(interleaved_all))

print("All files saved with structured interleaved format:\n- all_songs_english.txt\n- all_songs_telugu.txt\n- all_songs_interleaved.txt")
