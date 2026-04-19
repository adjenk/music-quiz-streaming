# check if there are previews available for our songs

import json
import requests
from difflib import SequenceMatcher

VALID_GENRES = {"pop", "rock", "jazz", "classical", "r&b", "indie pop", "rockabilly", "raï", "house", "techno", "dance", "electronica", "electro house", "drum & bass", "big room", "progressive house", "progressive trance", "edm", "trap", "trance", "electronic", "melodic house", "big room house"}  

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def check_network():
    try:
        requests.get("https://api.deezer.com", timeout=5)
        return True
    except requests.exceptions.ConnectionError:
        return False

def find_best_guess(artist, title):
    loose_query = f"{artist} {title}"
    url = f"https://api.deezer.com/search?q={requests.utils.quote(loose_query)}"
    data = requests.get(url).json()
    if data.get("total", 0) == 0:
        return None
    scored = []
    for result in data["data"]:
        da = result["artist"]["name"]
        dt = result["title"]
        preview = result["preview"]
        score = similar(artist, da) + similar(title, dt)
        scored.append((score, da, dt, preview))
    scored.sort(reverse=True)
    best = scored[0]
    if best[0] < 1.6:
        return {
            "suggested_artist": best[1],
            "suggested_title":  best[2],
            "preview_url":      best[3],
        }
    return None

def check_preview(artist, title):
    query = f'artist:"{artist}" track:"{title}"'
    url = f"https://api.deezer.com/search?q={requests.utils.quote(query)}"
    try:
        data = requests.get(url).json()
    except requests.exceptions.RequestException as e:
        print("network error")
        exit()

    if data.get("total", 0) > 0:
        for result in data["data"]:
            if result["preview"]:
                genre_id = result["album"].get("genre_id", 0)
                genre_name = requests.get(f"https://api.deezer.com/genre/{genre_id}").json().get("name", "Unknown")
                return result["preview"], None, genre_name

    suggestion = find_best_guess(artist, title)
    return None, suggestion, None


if not check_network():
    print("No network connection; exiting")
    exit()

try:
    with open("songs.json", "r") as f:
        songs = json.load(f)
except json.JSONDecodeError as e:
    print(f"songs.json is not valid JSON: {e}")
    exit()

for song in songs:
    artist = song["artist"]
    title  = song["title"]

    preview_url, suggestion, genre = check_preview(artist, title)

    if preview_url is None:
        suffix = f"   Possible match: {suggestion['suggested_artist']} — {suggestion['suggested_title']}" if suggestion else ""
        print(f"No preview: {artist} — {title}{suffix}")

    if song.get("genre", "").lower() not in VALID_GENRES:
        print(f"No genre: {song['artist']} — {song['title']} : {song.get('genre', 'missing')}")
