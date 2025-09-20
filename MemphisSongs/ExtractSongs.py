import requests
from bs4 import BeautifulSoup

BASE_URL = "https://songbooks.memphissaints.org/"
OUTPUT_FILE = "all_songs.txt"

def fetch_song_links():
    response = requests.get(BASE_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    container = soup.find('div', class_='otw-row otw_blog_manager-blog-item-holder')
    if not container:
        print("No song container found!")
        return []

    links = container.find_all('a', href=True)
    song_links = []
    for link in links:
        href = link['href']
        if href.startswith("https://songbooks.memphissaints.org/?p="):
            song_links.append(href)
    return list(set(song_links))  # remove duplicates

def extract_text_from_p(p):
    """Extract text from a <p> preserving <br> as newlines."""
    lines = []
    for elem in p.contents:
        if elem.name == "br":
            lines.append("\n")
        else:
            text = elem.strip() if isinstance(elem, str) else elem.get_text(strip=True)
            lines.append(text)
    return ''.join(lines).strip()

def fetch_song_lyrics(song_url):
    response = requests.get(song_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Song Title
    title_tag = soup.find('h1', class_='entry-title')
    title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

    # Content
    content_div = soup.find('div', class_='entry-content')
    if not content_div:
        print(f"No lyrics found for {title}")
        return None

    lyrics = []
    verse_order = []
    verse_count = 0
    chorus_count = 0
    verse_lines = []

    paragraphs = content_div.find_all('p')
    for p in paragraphs:
        text = extract_text_from_p(p)
        if not text or text in ['&nbsp;', '']:
            # Empty paragraph signals end of current verse
            if verse_lines:
                verse_count += 1
                lyrics.append(f"{verse_count}. " + '\n'.join(verse_lines))
                verse_order.append(f"v{verse_count}")
                verse_lines = []
            continue

        # Heuristic: check for chorus (starts with "Chorus" or common chorus text)
        if "Chorus" in text or text.lower().startswith(("close to", "draw me")):
            chorus_count += 1
            lyrics.append(f"Chorus{chorus_count} : {text}")
            verse_order.append(f"c{chorus_count}")
        else:
            verse_lines.append(text)

    # Add last verse if any
    if verse_lines:
        verse_count += 1
        lyrics.append(f"{verse_count}. " + '\n'.join(verse_lines))
        verse_order.append(f"v{verse_count}")

    song_number = song_url.split('=')[-1]
    verse_order_str = ' '.join(verse_order)
    lyrics_str = '\n'.join(lyrics)

    song_data = f"""SongNumber: {song_number}
SongTitle: {title}
VerseOrder: {verse_order_str}
{lyrics_str}
"""
    return song_data

def main():
    print("Fetching song links from homepage...")
    song_links = fetch_song_links()
    print(f"Found {len(song_links)} songs.")

    all_songs = []
    for song_link in song_links:
        print(f"Processing song {song_link}...")
        song_data = fetch_song_lyrics(song_link)
        if song_data:
            all_songs.append(song_data)
            print(f"Processed song: {song_data.splitlines()[1].split(': ')[1]}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_songs))

    print(f"All songs saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
