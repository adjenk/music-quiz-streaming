import io
import json
import os
import pygame
import random
import requests
import time
from difflib import SequenceMatcher

DEBUG=0
PREVIEW_DURATION = 30   # seconds; up to 30

# Initialize Pygame
pygame.init()

# Screen Setup
screen_width = 800
screen_height = 600

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Song Quiz")

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def get_deezer_preview(artist, title):
    if DEBUG:
        print(f"Searching Deezer for: {artist} — {title}")

    query = f'artist:"{artist}" track:"{title}"'
    url = f"https://api.deezer.com/search?q={requests.utils.quote(query)}"

    response = requests.get(url)
    data = response.json()

    if DEBUG:
        print(f"Deezer returned total={data.get('total')} results")

    if data["total"] > 0:
        for result in data["data"]:
            deezer_artist = result["artist"]["name"]
            deezer_title = result["title"]
            has_preview = bool(result["preview"])

            if DEBUG:
                print(f"Checking: '{deezer_artist}' — '{deezer_title}' (preview={has_preview})")

            artist_match = similar(artist, deezer_artist) > 0.6
            title_match = similar(title, deezer_title) > 0.6

            if DEBUG:
                print(f"  artist_match={artist_match}, title_match={title_match}")

            if artist_match and title_match and has_preview:
                return result["preview"]

        if DEBUG:
            print("No matching result with preview")
    else:
        if DEBUG:
            print("No results found at all")

    return None

def play_song(preview_url, duration, button_rects, song_name):
    response = requests.get(preview_url)
    audio_data = io.BytesIO(response.content)
    pygame.mixer.music.load(audio_data)
    pygame.mixer.music.set_volume(0.2)

    offset = random.uniform(5.0, 30.0)
    if DEBUG:
        print(f"Using offset {offset}")
    pygame.mixer.music.play(start=offset)   # start at a random point. this should make it easier, for songs with long intros etc

    # Update UI
    message_rect = pygame.Rect(0, 140, screen_width, 60)
    pygame.draw.rect(screen, (255, 255, 255), message_rect)
    display_text("Mystery song is playing...", None, 32, (0, 0, 255), screen_width // 2, 170)
    pygame.display.update(message_rect)

    start_time = time.time()
   
    guessed_option = None

    while True:
        elapsed = time.time() - start_time
        remaining = int(duration - elapsed)

        if remaining < 0:
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                for option, rect in button_rects.items():
                    if rect.collidepoint(event.pos):
                        guessed_option = option
                        pygame.mixer.music.stop()
                        return guessed_option 

        # Clear only the countdown area
        countdown_rect = pygame.Rect(screen_width // 2 - 50, 470, 100, 60)
        pygame.draw.rect(screen, (255, 255, 255), countdown_rect)

        # Draw countdown number
        display_text(f"{remaining}", None, 60, (255, 0, 0), screen_width // 2, 500)

        pygame.display.update()
        time.sleep(0.1)

    pygame.mixer.music.stop()
    return guessed_option

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

def display_buttons(buttons):
    button_font = pygame.font.SysFont(None, 30)
    button_width =  260
    button_height = 70
    button_gap_x =  30
    button_gap_y =  25
    button_x = (screen_width - (2 * button_width + button_gap_x)) // 2
    button_rects = {}  

    for i, option in enumerate(buttons):
        button_row = i // 2
        button_col = i % 2
        button_y = 200 + button_row * (button_height + button_gap_y)
        button_rect = pygame.Rect(button_x + button_col * (button_width + button_gap_x), button_y, button_width, button_height)
        pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
        
        text = option
        font_size = 30
        font = pygame.font.SysFont(None, font_size)

        # shrink font until it fits inside the button
        while font.size(text)[0] > button_width - 20 and font_size > 14:
            font_size -= 1
            font = pygame.font.SysFont(None, font_size)

        text_surface = font.render(text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=button_rect.center)
        screen.blit(text_surface, text_rect)

        button_rects[option] = button_rect
    return button_rects

def music_quiz():
    score = 0
    total_questions = 3

    with open('songs.json', 'r') as file:
        songs = json.load(file)
        if len(songs) < 5:
            print("Not enough songs in songs.json (need at least 5)")
            pygame.quit()
            exit()

    question = 0
    while question < total_questions:
        # Pick 4 unique songs
        round_songs = random.sample(songs, 4)

        # Pick one to be played
        song = random.choice(round_songs)
        song_name = f"{song['artist']} — {song['title']}"

        # Get preview
        song["preview_url"] = get_deezer_preview(song["artist"], song["title"])
        if song["preview_url"] is None:
            if DEBUG:
                print(f"Skipping: No preview for {song_name}")
            continue
        screen.fill((255, 255, 255))
        display_text(f"Question {question + 1} of {total_questions}", None, 40, (0, 0, 255), screen_width // 2, 60)

        buttons = [f"{s['artist']} — {s['title']}" for s in round_songs]
        button_rects = display_buttons(buttons)
        pygame.display.update()
   
        question += 1
        guessed = play_song(song["preview_url"], PREVIEW_DURATION, button_rects, song_name)
    
        if guessed == song_name:
            score += 1
            screen.fill((255, 255, 255))
            display_text("Correct!", None, 50, (0, 180, 0), screen_width // 2, 250)
        else:
            screen.fill((255, 255, 255))
            display_text("Incorrect!", None, 50, (200, 0, 0), screen_width // 2, 220)
            display_text(f"It was:", None, 32, (0, 0, 0), screen_width // 2, 400)
            display_text(song_name, None, 28, (0, 0, 0), screen_width // 2, 440)

        time.sleep(1)
        pygame.display.update()

    question += 1

    # Final screen
    screen.fill((255, 255, 255))
    display_text(f"Final Score: {score} / {total_questions}", None, 50, (0, 128, 0), screen_width // 2, 250)
    pygame.display.update()
    time.sleep(3)

    pygame.quit()
    exit()

music_quiz()
