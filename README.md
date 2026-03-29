# music-quiz-streaming
A music‑guessing game that streams preview clips from Deezer’s public API.
Built with Python and Pygame, it presents four possible answers for each round and lets the player guess which song is playing.

## Requirements
- Python 3.10+
- Pygame
- Requests

## Song List
The game loads songs from a local `songs.json` file.
You need at least 5 songs in the file.
The game will automatically skip any song that has no Deezer preview available.

Inspired by [Music-Quiz-Python](https://github.com/SadWillman/Music-Quiz-Python) by SadWillman
