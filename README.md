# Terminal Music & Lyric Player

Aplikasi CLI Python untuk memutar musik MP3 lokal dan menampilkan lirik LRC
secara tersinkronisasi.

## Struktur proyek

- `core/` - controller, lifecycle aplikasi, dan integrasi modul
- `audio/` - playback menggunakan `pygame.mixer`
- `lyrics/` - parser LRC dan sinkronisasi lirik
- `library/` - scanner, listing, sorting, search, dan playlist
- `ui/` - menu serta tampilan terminal
- `tests/` - unit test dan integration test
- `data/music/` - file MP3 lokal
- `data/lyrics/` - file LRC lokal

## Instalasi dependency

```powershell
python -m pip install -r requirements.txt
```

Dependency eksternal awal: `pygame-ce`. Package ini menyediakan modul import
`pygame` dan dipakai karena mendukung Python 3.14 pada Windows. Modul lain
menggunakan standard library Python sesuai SRS.
