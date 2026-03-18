import io
import json
import os
import pygame
import random
import requests
import pickle
import time

# Initialize Pygame
pygame.init()

# Screen Setup
screen_width = 800
screen_height = 600

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Song Quiz")

def get_deezer_preview(artist, title):
    query = f'artist:"{artist}" track:"{title}"'
    url = f"https://api.deezer.com/search?q={requests.utils.quote(query)}"

    response = requests.get(url)

    data = response.json()

    if data["total"] > 0:
        for result in data["data"]:
            artist_match = result["artist"]["name"].lower() == artist.lower()
            title_match = result["title"].lower() == title.lower()
            if artist_match and title_match and result["preview"]:
                return result["preview"]
        print("No exact match found.")
    else:
        print("No results found.")
    return None

def load_random_song():
    try:
        with open('songs.json', 'r') as file:
            songs = json.load(file)
        print(f"{len(songs)} songs; you've got a {100 / len(songs):.1f}% chance of being right!")
    except FileNotFoundError:
        print("Error: The file 'songs.json' was not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return None
    
    song = random.choice(songs)
    preview_url = get_deezer_preview(song["artist"], song["title"])
    
    if preview_url:
        return {**song, "preview_url": preview_url}

def play_song(preview_url, duration):
    response = requests.get(preview_url)
    audio_data = io.BytesIO(response.content)
    pygame.mixer.music.load(audio_data)
    pygame.mixer.music.set_volume(0.2)
    pygame.mixer.music.play()

    start_time = time.time()
    while time.time() - start_time < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()
        time.sleep(0.1)             # small sleep to avoid hammering the CPU

    pygame.mixer.music.stop()

def display_text(text, font=None, size=36, color=(0, 0, 255), x=0, y=0, align="center"):
    if font is None:
        font = pygame.font.match_font("freesans")

    font = pygame.font.Font(font, size)
    text_surface = font.render(text, True, color)
    if align == "center":
        text_rect = text_surface.get_rect(center=(x, y))
    elif align == "topright":
        text_rect = text_surface.get_rect(topright=(x, y))
    screen.blit(text_surface, text_rect)

# main program starts here

song = load_random_song()
if song is None:
    print("Failed to load a song, exiting.")
    pygame.quit()
    exit()

#print (song["title"])

screen.fill((255, 255, 255))

display_text("Mystery song is playing...", None, 40, (0, 0, 255), screen_width // 2, screen_height // 2)
pygame.display.update()
play_song(song["preview_url"], 30)  # play first 30 secs
