import io
import json
import os
import pygame
import random
import requests
import pickle
import time

PREVIEW_DURATION = 10   # seconds

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

def play_song(preview_url, duration, button_rects, song_name):
    response = requests.get(preview_url)
    audio_data = io.BytesIO(response.content)
    pygame.mixer.music.load(audio_data)
    pygame.mixer.music.set_volume(0.2)
    pygame.mixer.music.play()

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
    button_width = 200
    button_height = 50
    button_gap_x = 20
    button_gap_y = 20
    button_x = (screen_width - (2 * button_width + button_gap_x)) // 2
    button_rects = {}  

    for i, option in enumerate(buttons):
        button_row = i // 2
        button_col = i % 2
        button_y = 200 + button_row * (button_height + button_gap_y)
        button_rect = pygame.Rect(button_x + button_col * (button_width + button_gap_x), button_y, button_width, button_height)
        pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
        text_surface = button_font.render(option, True, (0, 0, 0))

        if text_surface.get_width() > button_width - 20:
            text_surface = pygame.transform.scale(text_surface, (button_width - 20, text_surface.get_height()))
        text_rect = text_surface.get_rect(center=button_rect.center)
        screen.blit(text_surface, text_rect)
        button_rects[option] = button_rect
    return button_rects

def music_quiz():
    running = True
    lives = 3
    score = 0
    # add high score loading later

    #while running:
    with open('songs.json', 'r') as file:
        songs = json.load(file)

    # Pick 4 unique songs
    round_songs = random.sample(songs, 4)

    # Pick one to be played
    song = random.choice(round_songs)

    # Fetch preview for it
    song["preview_url"] = get_deezer_preview(song["artist"], song["title"])

    # Create the label that matches the button text
    song_name = f"{song['artist']} — {song['title']}"

    if song is None:
        print("Failed to load a song, exiting.")
        pygame.quit()
        exit()

    screen.fill((255, 255, 255))
    display_text("Mystery song is playing...", None, 40, (0, 0, 255), screen_width // 2, 100)

    buttons = [f"{s['artist']} — {s['title']}" for s in round_songs]
    button_rects = display_buttons(buttons)

    pygame.display.update()
    
    guessed_option = play_song(song["preview_url"], PREVIEW_DURATION, button_rects, song_name)
    
    if guessed_option is None:
        print("No guess made")
    elif guessed_option == song_name:
        print("Correct")
    else:
        print(f"Incorrect; you picked: {guessed_option}")


    screen.fill((255, 255, 255))
    buttons = [f"{s['artist']} — {s['title']}" for s in round_songs]
    button_rects = display_buttons(buttons)
    pygame.display.update()

    # check answer
    # if they get it wrong, lives -= 1
    if lives == 0:
        running = False

#Run the quiz
while music_quiz():
   pass

