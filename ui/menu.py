"""Menu definitions, command parsing, and user instructions for Terminal UI (NFR-05)."""


def format_menu_bar() -> str:
    """Return the compact command bar shown in the terminal player."""
    return (
        "Perintah: [l]ist | [1..N] pilih lagu | [p]ause | [r]esume | "
        "[n]ext | [b]ack | [s]top | sort | search | filter | pl | reset | [h]elp | [q]uit"
    )


def format_help_menu() -> str:
    """Return detailed usage instructions for the terminal player."""
    lines = [
        "=" * 60,
        "  DAFTAR PERINTAH TERMINAL MUSIC & LYRIC PLAYER",
        "=" * 60,
        "  l / list                    : Menampilkan daftar lagu aktif",
        "  <nomor>                     : Memilih dan memutar lagu (contoh: 1)",
        "  p / pause                   : Menjeda pemutaran lagu saat ini",
        "  r / resume                  : Melanjutkan pemutaran lagu yang dijeda",
        "  n / next                    : Berpindah ke lagu berikutnya",
        "  b / back / prev             : Berpindah ke lagu sebelumnya",
        "  s / stop                    : Menghentikan pemutaran lagu",
        "  sort <field> [asc|desc]     : Urutkan (title/artist/duration/date)",
        "  search <kata kunci>         : Cari lagu berdasarkan judul/artis",
        "  filter lrc <yes|no>         : Filter lagu dengan/tanpa file LRC",
        "  filter artist <nama artis>  : Filter lagu berdasarkan artis",
        "  reset                       : Kembalikan tampilan ke seluruh library",
        "  pl create <nama>            : Membuat playlist baru",
        "  pl list                     : Melihat daftar playlist",
        "  pl show <nama>              : Melihat isi playlist",
        "  pl add <nama> <nomor>       : Menambah lagu aktif ke playlist",
        "  pl remove <nama> <nomor>    : Menghapus lagu dari playlist",
        "  pl play <nama> [nomor]      : Memutar lagu dari playlist",
        "  h / help                    : Menampilkan panduan perintah ini",
        "  q / quit                    : Menghentikan musik dan keluar",
        "=" * 60,
    ]
    return "\n".join(lines)


def render_menu() -> str:
    """Print the compact menu bar to the terminal."""
    text = format_menu_bar()
    print(text)
    return text


def render_help() -> str:
    """Print the full help menu to the terminal."""
    text = format_help_menu()
    print(text)
    return text


def parse_menu_command(raw_input: str) -> tuple[str, int | None]:
    """Parse raw user command string into a normalized (action, track_number) tuple."""
    cleaned = raw_input.strip().lower()
    if not cleaned:
        return ("empty", None)

    if cleaned.isdigit():
        return ("select_track", int(cleaned))

    parts = cleaned.split()
    cmd = parts[0]

    if cmd == "play" and len(parts) == 2 and parts[1].isdigit():
        return ("select_track", int(parts[1]))

    command_map = {
        "l": "list",
        "list": "list",
        "p": "pause",
        "pause": "pause",
        "r": "resume",
        "resume": "resume",
        "play": "play",
        "n": "next",
        "next": "next",
        "b": "previous",
        "back": "previous",
        "prev": "previous",
        "previous": "previous",
        "s": "stop",
        "stop": "stop",
        "h": "help",
        "help": "help",
        "q": "quit",
        "quit": "quit",
        "exit": "quit",
    }

    action = command_map.get(cmd)
    if action is not None and len(parts) == 1:
        return (action, None)

    return ("unknown", None)


def parse_extended_command(raw_input: str) -> tuple[str, list[str]]:
    """Parse Stage 2 library & playlist commands into (action, args)."""
    cleaned = raw_input.strip()
    if not cleaned:
        return ("unknown", [])

    parts = cleaned.split()
    cmd = parts[0].lower()

    if cmd == "sort" and len(parts) in (2, 3):
        field = parts[1].lower()
        order = parts[2].lower() if len(parts) == 3 else "asc"
        return ("sort", [field, order])

    if cmd == "search" and len(parts) >= 2:
        keyword = cleaned[len(parts[0]) :].strip()
        if keyword:
            return ("search", [keyword])

    if cmd == "filter" and len(parts) >= 3:
        sub = parts[1].lower()
        if sub == "lrc" and len(parts) == 3:
            return ("filter_lrc", [parts[2].lower()])
        if sub == "artist":
            artist_name = cleaned.split(None, 2)[2].strip()
            if artist_name:
                return ("filter_artist", [artist_name])

    if cmd == "reset" and len(parts) == 1:
        return ("reset", [])

    if cmd in {"pl", "playlist"} and len(parts) >= 2:
        subcmd = parts[1].lower()
        return ("playlist", [subcmd, *parts[2:]])

    return ("unknown", [])
