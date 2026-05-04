#!/usr/bin/env python3

# helps to check the song database

import json
import sys
import requests
from collections import Counter
from difflib import SequenceMatcher

VALID_GENRES = {
    "pop", "rock", "jazz", "classical", "r&b", "indie pop", "rockabilly",
    "raï", "house", "techno", "dance", "electronica", "electro house",
    "drum & bass", "big room", "progressive house", "progressive trance",
    "edm", "trap", "trance", "electronic", "melodic house", "big room house",
    "future house",
}

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
    except requests.exceptions.RequestException:
        print("network error")
        sys.exit(1)
    if data.get("total", 0) > 0:
        for result in data["data"]:
            if result["preview"]:
                genre_id = result["album"].get("genre_id", 0)
                genre_name = requests.get(f"https://api.deezer.com/genre/{genre_id}").json().get("name", "Unknown")
                return result["preview"], None, genre_name
    suggestion = find_best_guess(artist, title)
    return None, suggestion, None

def load_songs():
    try:
        with open("songs.json", "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"songs.json is not valid JSON: {e}")
        sys.exit(1)

def cmd_nopreviews(songs):
    if not check_network():
        print("No network connection; exiting")
        sys.exit(1)
    for song in songs:
        artist = song["artist"]
        title  = song["title"]
        genre  = song.get("genre", "")
        preview_url, suggestion, _ = check_preview(artist, title)
        if preview_url is None:
            suffix = (
                f"   Possible match: {suggestion['suggested_artist']} — {suggestion['suggested_title']}"
                if suggestion else ""
            )
            print(f"No preview: {artist} — {title}{suffix}")
        if genre.lower() not in VALID_GENRES:
            print(f"No genre: {artist} — {title} : {genre or 'missing'}")

def cmd_genres(songs):
    counts = Counter()
    for song in songs:
        genre = song.get("genre", "").strip() or "missing"
        counts[genre] += 1

    # Sort by count descending, then genre name ascending
    sorted_genres = sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))

    # Align columns
    max_genre_len = max(len(g) for g, _ in sorted_genres)
    for genre, count in sorted_genres:
        print(f"{genre:<{max_genre_len}}  {count}")

def usage():
    print("Usage: validate_songs.py -nopreviews | -genres")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()

    songs = load_songs()

    match sys.argv[1]:
        case "-nopreviews":
            cmd_nopreviews(songs)
        case "-genres":
            cmd_genres(songs)
        case _:
            usage()
