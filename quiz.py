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

def draw_menu_button(text, y):
    button_width = 400
    button_height = 60
    x = (screen_width - button_width) // 2
    rect = pygame.Rect(x, y, button_width, button_height)

    pygame.draw.rect(screen, COLOURS["button_bg"], rect, border_radius=12)
    pygame.draw.rect(screen, COLOURS["button_border"], rect, width=2, border_radius=12)

    label = pygame.font.Font(FONT_PATH_BOLD, 28).render(text, True, COLOURS["text_main"])
    label_rect = label.get_rect(center=rect.center)
    screen.blit(label, label_rect)

    return rect

def cycle_questions(current, total_songs):
    max_q = max(3, min(20, total_songs // 2))
    options = [3, 5, 10, 15, 20]
    options = [o for o in options if o <= max_q]
    if current not in options:
        return options[0]
    idx = options.index(current)
    return options[(idx + 1) % len(options)]

def cycle_genre(current, available_genres):
    idx = available_genres.index(current)
    return available_genres[(idx + 1) % len(available_genres)]

def main_menu(settings, songs, available_genres):
    while True:
        screen.fill(COLOURS["bg"])

        display_text("Song Quiz", None, 60, COLOURS["accent"], screen_width // 2, 100)

        start_rect     = draw_menu_button("Start Quiz", 220)
        questions_rect = draw_menu_button(f"Questions: {settings['num_questions']}", 300)
        genre_rect     = draw_menu_button(f"Genre: {settings['genre']}", 380)
        quit_rect      = draw_menu_button("Quit", 460)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_rect.collidepoint(event.pos):
                    return "start"
                if quit_rect.collidepoint(event.pos):
                    return "quit"
                if questions_rect.collidepoint(event.pos):
                    if settings["genre"] == "Any":
                        available = songs
                    else:
                        available = [s for s in songs if s.get("genre") == settings["genre"]]
                    settings["num_questions"] = cycle_questions(settings["num_questions"], len(available))
                if genre_rect.collidepoint(event.pos):
                    settings["genre"] = cycle_genre(settings["genre"], available_genres)

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

def music_quiz(settings, songs):
    score = 0
    total_questions = settings["num_questions"]
    selected_genre = settings["genre"]

    # Apply genre filter
    filtered_songs = songs
    if selected_genre != "Any":
        filtered_songs = [s for s in songs if s.get("genre") == selected_genre]

    if len(filtered_songs) < 4:
        screen.fill(COLOURS["bg"])
        display_text("Not enough songs", None, 36, COLOURS["incorrect"], screen_width // 2, 250)
        display_text("for this genre.", None, 36, COLOURS["incorrect"], screen_width // 2, 295)
        pygame.display.update()
        time.sleep(2)
        if DEBUG:
            print(f"Not enough songs in songs.json (need at least 4 for {selected_genre}")
        return

    if not check_network():
        print("No network connection; exiting")
        pygame.quit()
        exit()

    button_height = 80
    button_gap    = 14
    total_height  = 4 * (button_height + button_gap) - button_gap
    last_button_bottom = 80 + total_height
    countdown_y = last_button_bottom + (screen_height - last_button_bottom) // 2

    question = 0

    while question < total_questions:
        sample_size = min(4, len(filtered_songs))
        round_songs = random.sample(filtered_songs, sample_size)

        song = random.choice(round_songs)
        song_name = f"{song['artist']} — {song['title']}"

        preview_url = song.get("preview")

        if not preview_url:
            if DEBUG:
                print(f"Skipping: No preview for {song_name}")
            continue

        buttons = [f"{s['artist']} — {s['title']}" for s in round_songs]
        screen.fill(COLOURS["bg"])
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
        display_buttons_result(list(button_rects.keys()), correct_name, guessed)
#        display_text(f"{score} / {total_questions}", None, 24, COLOURS["text_dim"], screen_width // 2, countdown_y)
        pygame.display.update()
        time.sleep(2)

    # Final screen
    screen.fill(COLOURS["bg"])
    display_text(f"Final Score: {score} / {total_questions}", None, 50, COLOURS["correct"], screen_width // 2, 250)
    pygame.display.update()
    time.sleep(3)

def main():
    from collections import Counter

    # Load all songs once before showing the menu
    with open('songs.json', 'r') as file:
        songs = json.load(file)

    if not check_network():
        print("No network connection; exiting")
        pygame.quit()
        exit()

    fetch_start = time.time()

    # Pre-fetch all preview URLs before the quiz starts
    prefetch_previews(songs, screen)

    print(f"Preview fetch took {time.time() - fetch_start:.1f}s for {len(songs)} songs")

    if len(songs) < 5:
        print("Not enough songs in songs.json (need at least 5)")
        exit()

    # Build list of genres with enough songs
    MIN_SONGS_PER_GENRE = 10
    genre_counts = Counter(s.get("genre", "") for s in songs)
    available_genres = ["Any"] + sorted(g for g, count in genre_counts.items() if count >= MIN_SONGS_PER_GENRE and g)

    settings = {
        "num_questions": 10,
        "genre": "Any"
    }

    while True:
        choice = main_menu(settings, songs, available_genres)
        if choice == "start":
            music_quiz(settings, songs)
        elif choice == "quit":
            pygame.quit()
            exit()

main()
