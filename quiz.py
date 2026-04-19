import io
import json
import os
import pygame
import random
import requests
import time
from difflib import SequenceMatcher

from concurrent.futures import ThreadPoolExecutor, as_completed

DEBUG=1
PREVIEW_DURATION = 30   # seconds; up to 30

COLOURS = {
    "bg":         (15,  15,  20),   # near-black
    "button_bg":  (30,  30,  40),   # dark card
    "button_border": (80, 80, 110), # muted purple-grey
    "button_hover":  (50, 50, 70),  # slightly lighter on hover
    "accent":     (220, 60, 120),   # hot pink accent
    "text_main":  (240, 240, 255),  # off-white
    "text_dim":   (140, 140, 160),  # muted
    "correct":    (40,  200, 120),
    "incorrect":  (220, 60,  60),
}

FONT_PATH_REGULAR = "fonts/Outfit-Regular.ttf"
FONT_PATH_BOLD    = "fonts/Outfit-Bold.ttf"

def display_buttons_result(buttons, correct, guessed):
    button_width  = screen_width - 80
    button_height = 80
    button_gap    = 14
    total_height  = len(buttons) * (button_height + button_gap) - button_gap
    start_y       = 80

    for i, option in enumerate(buttons):
        x = 40
        y = start_y + i * (button_height + button_gap)
        rect = pygame.Rect(x, y, button_width, button_height)

        if option == correct:
            bg_color     = (20, 80, 50)
            border_color = COLOURS["correct"]
            bar_color    = COLOURS["correct"]
        elif option == guessed:
            bg_color     = (80, 20, 20)
            border_color = COLOURS["incorrect"]
            bar_color    = COLOURS["incorrect"]
        else:
            bg_color     = COLOURS["button_bg"]
            border_color = COLOURS["button_border"]
            bar_color    = COLOURS["accent"]

        pygame.draw.rect(screen, bg_color, rect, border_radius=12)
        pygame.draw.rect(screen, border_color, rect, width=2, border_radius=12)
        bar_rect = pygame.Rect(x, y + 16, 4, button_height - 32)
        pygame.draw.rect(screen, bar_color, bar_rect, border_radius=2)

        if " — " in option:
            artist, title = option.split(" — ", 1)
        else:
            artist, title = option, ""

        artist_font = pygame.font.SysFont("freesans", 20)
        artist_surf = artist_font.render(artist, True, COLOURS["text_dim"])
        screen.blit(artist_surf, (x + 22, y + 16))

        title_font = pygame.font.SysFont("freesans", 26)
        title_surf = title_font.render(title, True, COLOURS["text_main"])
        screen.blit(title_surf, (x + 22, y + 38))

# Initialize Pygame
pygame.init()

# Screen Setup
screen_width = 800
screen_height = 600

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Song Quiz")

def fetch_preview_for_song(song):
    time.sleep(random.uniform(0.1, 0.3))    # to try not to hammer deezer too hard
    song["preview"] = get_deezer_preview(song["artist"], song["title"])
    return song

def prefetch_previews(songs, screen):
    # Loading screen
    screen.fill(COLOURS["bg"])
    display_text("Loading songs...", None, 40, COLOURS["text_main"], screen_width // 2, 250)
    pygame.display.update()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(fetch_preview_for_song, song): song for song in songs}
        completed = 0
        for future in as_completed(futures):
            future.result()
            completed += 1
            pygame.event.pump()   # keep OS happy
            screen.fill(COLOURS["bg"])
            display_text("Loading songs...", None, 40, COLOURS["text_main"], screen_width // 2, 220)
            display_text(f"{completed} / {len(songs)}", None, 32, COLOURS["text_dim"], screen_width // 2, 280)
            pygame.display.update()

def check_network():
    try:
        requests.get("https://api.deezer.com", timeout=5)
        return True
    except requests.exceptions.ConnectionError:
        return False

def get_deezer_preview(artist, title):
    """
    Look up a Deezer preview URL for the given artist and title.
    Returns the preview URL string, or None if nothing usable was found.
    """
    try:
        query = f'artist:"{artist}" track:"{title}"'
        url = f"https://api.deezer.com/search?q={requests.utils.quote(query)}"
        data = requests.get(url, timeout=10).json()
        if "data" not in data:
            print(f"Unexpected response for {artist} - {title}: {data}")
            return None

        for result in data["data"]:
            if result["preview"]:
                return result["preview"]

    except requests.exceptions.ConnectionError:
        print(f"Network error looking up: {artist} - {title}")
        exit()
    except requests.exceptions.Timeout:
        print(f"Timed out looking up: {artist} - {title}")
        exit()
    return None


def play_song(preview_url, duration, button_rects, song_name, question, total_questions):
    response = requests.get(preview_url)
    audio_data = io.BytesIO(response.content)
    pygame.mixer.music.load(audio_data)
    pygame.mixer.music.set_volume(0.2)

    offset = random.uniform(5.0, 30.0)
    if DEBUG:
        print(f"Using offset {offset}")
    pygame.mixer.music.play(start=offset)

    start_time = time.time()
    guessed_option = None
    buttons = list(button_rects.keys())

    while True:
        elapsed = time.time() - start_time
        remaining = int(duration - elapsed)
        if remaining < 0:
            break

        mouse_pos = pygame.mouse.get_pos()
        hovered = next((opt for opt, r in button_rects.items() if r.collidepoint(mouse_pos)), None)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for option, rect in button_rects.items():
                    if rect.collidepoint(event.pos):
                        pygame.mixer.music.stop()
                        return option

        # Redraw
        screen.fill(COLOURS["bg"])
        display_text(f"Question {question} of {total_questions}", None, 28, COLOURS["text_dim"], screen_width // 2, 40)
        button_rects = display_buttons(buttons, hovered=hovered)

        button_height = 80
        button_gap    = 14
        total_height  = 4 * (button_height + button_gap) - button_gap
        last_button_bottom = 80 + total_height
        countdown_y = last_button_bottom + (screen_height - last_button_bottom) // 2

        # Countdown at the bottom, cleared each frame by the fill above
        display_text(f"{remaining}", None, 52, COLOURS["accent"], screen_width // 2, countdown_y)

        pygame.display.update()
        time.sleep(0.05)

    pygame.mixer.music.stop()
    return None

def display_text(text, font=None, size=36, color=COLOURS["text_main"], x=0, y=0, align="center"):
    if font is None:
        font = FONT_PATH_BOLD
    font = pygame.font.Font(font, size)
    text_surface = font.render(text, True, color)
    if align == "center":
        text_rect = text_surface.get_rect(center=(x, y))
    elif align == "topright":
        text_rect = text_surface.get_rect(topright=(x, y))
    screen.blit(text_surface, text_rect)

def display_buttons(buttons, hovered=None):
    button_width  = screen_width - 80          # nearly full width
    button_height = 80
    button_gap    = 14
    total_height  = len(buttons) * (button_height + button_gap) - button_gap
    start_y       = 80

    button_rects = {}

    for i, option in enumerate(buttons):
        x = 40
        y = start_y + i * (button_height + button_gap)
        rect = pygame.Rect(x, y, button_width, button_height)

        is_hovered = (option == hovered)

        # Background + border
        bg_color = COLOURS["button_hover"] if is_hovered else COLOURS["button_bg"]
        pygame.draw.rect(screen, bg_color, rect, border_radius=12)
        border_color = COLOURS["accent"] if is_hovered else COLOURS["button_border"]
        pygame.draw.rect(screen, border_color, rect, width=2, border_radius=12)

        # Accent bar on the left
        bar_rect = pygame.Rect(x, y + 16, 4, button_height - 32)
        pygame.draw.rect(screen, COLOURS["accent"], bar_rect, border_radius=2)

        # Split "Artist — Title" onto two lines
        if " — " in option:
            artist, title = option.split(" — ", 1)
        else:
            artist, title = option, ""

        # Artist name (smaller, dimmed)
        artist_font_size = 20
        artist_font = pygame.font.SysFont("freesans", artist_font_size)
        while artist_font.size(artist)[0] > button_width - 60 and artist_font_size > 13:
            artist_font_size -= 1
            artist_font = pygame.font.SysFont("freesans", artist_font_size)
        artist_surf = artist_font.render(artist, True, COLOURS["text_dim"])
        screen.blit(artist_surf, (x + 22, y + 16))

        # Track title (larger, bright)
        title_font_size = 26
        title_font = pygame.font.SysFont("freesans", title_font_size)
        while title_font.size(title)[0] > button_width - 60 and title_font_size > 14:
            title_font_size -= 1
            title_font = pygame.font.SysFont("freesans", title_font_size)
        title_surf = title_font.render(title, True, COLOURS["text_main"])
        screen.blit(title_surf, (x + 22, y + 38))

        button_rects[option] = rect

    return button_rects

def music_quiz():
    score = 0
    total_questions = 3

    with open('songs.json', 'r') as file:
        songs = json.load(file)

    if not check_network():
        print("No network connection; exiting")
        pygame.quit()
        exit()

    fetch_start = time.time()

    # Pre-fetch all preview URLs before the quiz starts
    #for song in songs:
    #    song["preview"] = get_deezer_preview(song["artist"], song["title"])
    prefetch_previews(songs, screen)

    print(f"Preview fetch took {time.time() - fetch_start:.1f}s for {len(songs)} songs")

    if len(songs) < 5:
        print("Not enough songs in songs.json (need at least 5)")
        exit()

    question = 0
    while question < total_questions:
        # Pick 4 unique songs
        round_songs = random.sample(songs, 4)

        # Pick one to be played
        song = random.choice(round_songs)
        song_name = f"{song['artist']} — {song['title']}"

        # Get preview
        preview_url = song.get("preview")

        if not preview_url:
            if DEBUG:
                print(f"Skipping: No preview for {song_name}")
            continue

#        display_text(f"Question {question + 1} of {total_questions}", None, 40, (0, 0, 255), screen_width // 2, 60)

        buttons = [f"{s['artist']} — {s['title']}" for s in round_songs]
        button_rects = display_buttons(buttons)
        pygame.display.update()
   
        question += 1
        guessed = play_song(preview_url, PREVIEW_DURATION, button_rects, song_name, question, total_questions)

        correct_name = song_name
        result_text  = "Correct!" if guessed == correct_name else "Incorrect!"
        result_color = COLOURS["correct"] if guessed == correct_name else COLOURS["incorrect"]
        if guessed == correct_name:
            score += 1

        screen.fill(COLOURS["bg"])
        display_text(result_text, None, 40, result_color, screen_width // 2, 30)
        display_text(f"{score} / {total_questions}", None, 24, COLOURS["text_dim"], screen_width // 2, 68)
        display_buttons_result(list(button_rects.keys()), correct_name, guessed)
        pygame.display.update()
        time.sleep(2)

    # Final screen
    screen.fill((255, 255, 255))
    display_text(f"Final Score: {score} / {total_questions}", None, 50, (0, 128, 0), screen_width // 2, 250)
    pygame.display.update()
    time.sleep(3)

    pygame.quit()
    exit()

music_quiz()
