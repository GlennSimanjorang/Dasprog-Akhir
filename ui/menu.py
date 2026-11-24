"""Terminal menu text and user command parser."""

_ALIASES = {
    "p": "pause",
    "pause": "pause",
    "r": "resume",
    "resume": "resume",
    "s": "stop",
    "stop": "stop",
    "n": "next",
    "next": "next",
    "b": "prev",
    "prev": "prev",
    "back": "prev",
    "list": "list",
    "sort": "sort",
    "search": "search",
    "filter": "filter",
    "playlist": "playlist",
    "pl": "playlist",
    "help": "help",
    "h": "help",
    "?": "help",
    "q": "quit",
    "quit": "quit",
    "exit": "quit",
}


def format_menu() -> str:
    """Return the CLI command reference string."""
    return "\n".join([
        "Perintah:",
        "  <no>                         Putar lagu sesuai nomor daftar",
        "  p | r | s | n | b            Pause, resume, stop, next, prev",
        "  list                         Tampilkan semua lagu",
        "  sort <kolom> [asc|desc]      Urutkan (title, artist, duration, date_added)",
        "  search <kata>                Cari berdasarkan judul atau artis",
        "  filter lrc <ya|tidak>        Filter ketersediaan lirik LRC",
        "  filter artist <nama>         Filter berdasarkan nama artis",
        "  playlist list                Lihat daftar playlist",
        "  playlist new <nama>          Buat playlist baru",
        "  playlist add <nama> <no>     Tambah lagu dari daftar aktif ke playlist",
        "  playlist remove <nama> <no>  Hapus lagu nomor urut dari playlist",
        "  playlist show <nama>         Lihat isi playlist",
        "  playlist play <nama>         Putar lagu dari playlist",
        "  help | q                     Tampilkan menu ini atau keluar",
    ])


def render_menu() -> None:
    """Print the CLI command menu to the terminal."""
    print(format_menu())


def parse_command(raw: str) -> tuple[str, list[str]]:
    """Parse a raw command string into an action name and argument list."""
    text = raw.strip()
    if not text:
        return "empty", []

    parts = text.split()
    if len(parts) == 1 and parts[0].isascii() and parts[0].isdigit():
        return "play_index", [parts[0]]

    action = _ALIASES.get(parts[0].lower())
    if action is None:
        return "unknown", [text]
    return action, parts[1:]
