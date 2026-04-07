"""
Co-Chan TUI  –  Téléchargeur anime-sama avec interface Textual
Fusion des options de plage (même saison & multi-saisons) de Co-Flix
"""
# pylint: disable=broad-exception-caught,global-statement,attribute-defined-outside-init
# pylint: disable=too-many-lines,wrong-import-position,multiple-imports
# pylint: disable=too-many-branches,too-many-statements,too-many-locals
# pylint: disable=too-many-return-statements,too-many-instance-attributes
# pylint: disable=too-many-arguments,too-many-positional-arguments
# pylint: disable=too-many-nested-blocks,import-outside-toplevel
# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=multiple-statements,invalid-name
# ── Auto-installation des dépendances ─────────────────────────────────────────
import sys, subprocess, importlib.util

def _pkg_installed(import_name):
    return importlib.util.find_spec(import_name) is not None

def _install(pip_name, import_name=None):
    if import_name is None:
        import_name = pip_name
    if _pkg_installed(import_name):
        return True
    print(f"  📦  Installation de '{pip_name}'…")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", pip_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return _pkg_installed(import_name)
    except Exception:
        return False

# (pip_name, import_name)  – import_name peut différer du nom pip
_REQUIRED = [
    ("requests",  "requests"),
    ("yt-dlp",    "yt_dlp"),
    ("textual",   "textual"),
    ("rich",      "rich"),
]

_missing = []
for _pip, _imp in _REQUIRED:
    if not _install(_pip, _imp):
        _missing.append(_pip)

if _missing:
    print(f"\n  ✖  Impossible d'installer : {', '.join(_missing)}")
    print("     Installe-les manuellement :  pip install " + " ".join(_missing))
    sys.exit(1)

# ── Imports ───────────────────────────────────────────────────────────────────
import os, platform, shutil, re, time, random, json
import tempfile, asyncio, signal

import requests

try:
    import ctypes
except ImportError:
    ctypes = None

try:
    import tty as _tty  # noqa: F401 – réservé usage futur sur Unix
    import termios as _termios  # noqa: F401
except ImportError:
    pass

_Image = None  # pylint: disable=invalid-name
_io = None     # pylint: disable=invalid-name
pil_available = importlib.util.find_spec("PIL") is not None
if pil_available:
    from PIL import Image as _Image  # type: ignore[assignment]  # pylint: disable=import-error
    import io as _io  # type: ignore[assignment]

from yt_dlp import YoutubeDL  # pylint: disable=import-error

from textual.app import App, ComposeResult  # pylint: disable=import-error
from textual.screen import ModalScreen  # pylint: disable=import-error
from textual.widgets import Static, ListView, ListItem, Label, Input, ProgressBar, RichLog  # pylint: disable=import-error
from textual.containers import Vertical, ScrollableContainer, Center  # pylint: disable=import-error
from textual.binding import Binding  # pylint: disable=import-error
from rich.text import Text  # pylint: disable=import-error

VERSION = "2.0"

# ── safe dismiss ──────────────────────────────────────────────────────────────
def _safe_dismiss(screen, result=None):
    try:
        screen.dismiss(result)
    except Exception:
        try:
            asyncio.get_event_loop().call_soon(screen.dismiss, result)
        except Exception:
            pass

# ── Helpers env ───────────────────────────────────────────────────────────────
def _is_termux():
    return (os.name != "nt" and (
        "ANDROID_STORAGE" in os.environ or "com.termux" in os.environ.get("PREFIX", "")))

def is_ios_device():
    s = platform.system()
    if s == "Darwin":
        if (os.path.exists("/var/mobile")
                or "iPad" in platform.machine()
                or "iPhone" in platform.machine()):
            return True
        if os.environ.get("HOME", "").startswith("/var/mobile"):
            return True
    return False

# ── Config persistante ────────────────────────────────────────────────────────
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cochan_config.json")

def _load_config():
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_config(updates: dict):
    cfg = _load_config()
    cfg.update(updates)
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ── Utilitaires ───────────────────────────────────────────────────────────────
def set_process_priority():
    s = platform.system()
    if s == "Windows":
        if ctypes:
            try:
                handle = ctypes.windll.kernel32.GetCurrentProcess()
                ctypes.windll.kernel32.SetPriorityClass(handle, 0x00000080)
            except Exception:
                pass
    else:
        try:
            current = os.nice(0)
            os.nice(max(-10, -current))
        except (PermissionError, AttributeError, OSError):
            pass

def _strip_ansi(s): return re.sub(r'\033\[[0-9;]*m', '', s)

# ── Chemins ───────────────────────────────────────────────────────────────────
def get_download_path():
    # Sur Termux : config en priorité (stockage choisi), sinon stockage interne par défaut
    if _is_termux():
        cfg = _load_config()
        path = cfg.get("download_dir") or "/storage/emulated/0/Download/anime"
        os.makedirs(path, exist_ok=True)
        return path
    cfg = _load_config()
    if cfg.get("download_dir") and os.path.isdir(cfg["download_dir"]):
        return cfg["download_dir"]
    s = platform.system()
    if s == "Windows":
        return os.getcwd()
    if s == "Darwin" and is_ios_device():
        for path in [os.path.expanduser("~/Documents/anime"),
                     os.path.expanduser("~/Downloads/anime"),
                     os.path.join(os.getcwd(), "anime")]:
            try:
                os.makedirs(path, exist_ok=True)
                if os.access(path, os.W_OK):
                    return path
            except Exception:
                continue
        return os.path.join(os.getcwd(), "anime")
    if s == "Darwin":
        return os.path.join(os.path.expanduser("~"), "Downloads", "anime")
    return os.path.join(os.path.expanduser("~"), "Downloads", "anime")

def format_url_name(name):
    return name.lower().replace("'", "").replace(" ", "-")

def format_folder_name(name, language):
    return f"{' '.join(word.capitalize() for word in name.split())} {language.upper()}"

def normalize_anime_name(name):
    return ' '.join(name.strip().split()).lower()

# ── Domaine anime-sama ────────────────────────────────────────────────────────
def _get_active_domain_sync():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp = requests.get("https://anime-sama.pw/", timeout=10, headers=headers)
        if resp.status_code == 200:
            for pattern in [
                r'<a\s+class="btn-primary"\s+href="(https?://anime-sama\.[a-z]+)"',
                r'href="(https?://anime-sama\.(?!pw)[a-z]+)"',
            ]:
                m = re.search(pattern, resp.text)
                if m:
                    base = m.group(1)
                    try:
                        r2 = requests.head(base, timeout=10, headers=headers, allow_redirects=True)
                        final = r2.url
                        if "anime-sama" in final and "anime-sama.pw" not in final:
                            domain = final.split("/catalogue")[0].rstrip("/")
                            return f"{domain}/catalogue/"
                    except Exception:
                        pass
    except Exception:
        pass
    return None

# ── Espace disque ─────────────────────────────────────────────────────────────
def check_disk_space(min_gb=1):
    s = platform.system()
    try:
        if s == "Windows":
            _, _, free = shutil.disk_usage("C:\\")
            if free / (1024**2) < 100:
                return False
            cur = os.path.splitdrive(os.getcwd())[0] + "\\"
            _, _, free = shutil.disk_usage(cur)
        elif s == "Linux" and "ANDROID_STORAGE" in os.environ:
            free = None
            for p in [os.path.expanduser("~/storage/downloads"), os.path.expanduser("~"),
                      "/storage/emulated/0", "/data/data/com.termux/files/home"]:
                try:
                    if os.path.exists(p):
                        _, _, free = shutil.disk_usage(p)
                        break
                except Exception:
                    continue
            if free is None:
                return True
        else:
            _, _, free = shutil.disk_usage(os.path.expanduser("~"))
        return free / (1024**3) >= min_gb
    except Exception:
        return True

# ── Vérification anime ────────────────────────────────────────────────────────
def check_anime_exists(base_url, name):
    for lang in ["vf", "vostfr", "va", "vkr", "vcn", "vqc"]:
        for kind in ["saison1", "film", "oav"]:
            try:
                r = requests.get(f"{base_url}{name}/{kind}/{lang}/episodes.js", timeout=5)
                if r.status_code == 200 and r.text.strip():
                    return True
            except Exception:
                continue
    return False

def check_available_languages(base_url, name, progress_cb=None, status_cb=None):
    langs = ["vf", "va", "vkr", "vcn", "vqc", "vf1", "vf2", "vf3", "vf4", "vf5"]
    available = []
    for i, lang in enumerate(langs):
        if progress_cb: progress_cb(int(i / len(langs) * 95))
        if status_cb: status_cb(f"Langue {lang.upper()}…")
        for kind in ["saison1", "film"]:
            try:
                r = requests.get(f"{base_url}{name}/{kind}/{lang}/episodes.js", timeout=5)
                if r.status_code == 200 and r.text.strip():
                    available.append(lang)
                    if status_cb: status_cb(f"Langue {lang.upper()}  ✔")
                    break
            except Exception:
                continue
    return available

def check_seasons(base_url, name, language, progress_cb=None, status_cb=None):
    season_info = {}
    season = 1
    not_found = 0
    while not_found < 3:
        has_n = has_hs = False
        n_url = f"{base_url}{name}/saison{season}/{language}/episodes.js"
        hs_url = f"{base_url}{name}/saison{season}hs/{language}/episodes.js"
        if status_cb: status_cb(f"Saison {season}…")
        # Progress estimée : on suppose rarement plus de 20 saisons
        if progress_cb: progress_cb(min(int((season - 1) / max(season + 2, 5) * 90), 90))
        try:
            r = requests.get(n_url, timeout=10)
            has_n = r.status_code == 200 and r.text.strip()
        except Exception:
            pass
        try:
            r = requests.get(hs_url, timeout=10)
            has_hs = r.status_code == 200 and r.text.strip()
        except Exception:
            pass
        if has_n or has_hs:
            not_found = 0
            label = f"Saison {season}" + (" + HS" if has_n and has_hs else "HS" if has_hs else "")
            if status_cb: status_cb(f"{label}  ✔")
            if has_n and has_hs:
                season_info[f"{season}"] = {
                    "type": "both", "normal": n_url,
                    "hs": hs_url, "variants": []
                }
            elif has_n:
                season_info[f"{season}"] = {"type": "normal", "url": n_url, "variants": []}
            else:
                season_info[f"{season}hs"] = {"type": "hs", "url": hs_url, "variants": []}
            # Variantes
            for base_key, base_u in [(f"{season}", n_url if has_n else None),
                                      (f"{season}hs", hs_url if has_hs else None)]:
                if base_u is None:
                    continue
                i = 1
                vfound = 0
                while vfound < 2:
                    v_url = base_u.replace("episodes.js", f"episodes{i}.js")
                    try:
                        r = requests.get(v_url, timeout=5)
                        if r.status_code == 200 and r.text.strip():
                            if base_key in season_info:
                                season_info[base_key].setdefault("variants", []).append((i, v_url))
                                if status_cb: status_cb(f"Saison {season} · variante {i}  ✔")
                            vfound = 0
                        else:
                            vfound += 1
                    except Exception:
                        vfound += 1
                    i += 1
        else:
            not_found += 1
        season += 1
    for special, label in [("film", "Film"), ("oav", "OAV")]:
        if status_cb: status_cb(f"{label}…")
        url = f"{base_url}{name}/{special}/{language}/episodes.js"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200 and r.text.strip():
                season_info[special] = {"type": special, "url": url, "variants": []}
                if status_cb: status_cb(f"{label}  ✔")
        except Exception:
            continue
    return season_info

def custom_sort_key(x):
    if isinstance(x, str) and x.isdigit():
        return (0, int(x))
    if isinstance(x, str) and 'hs' in x:
        return (0, int(x.replace('hs', '')) + 0.5)
    if x == "film":
        return (1, 0)
    if x == "oav":
        return (2, 0)
    return (3, str(x))

def resolve_season_choices(season_info):
    final_seasons = []
    for key, info in sorted(season_info.items(), key=lambda x: custom_sort_key(x[0])):
        if info["type"] == "both":
            urls = [info["normal"]]
            urls.extend([v[1] for v in sorted(info.get("variants", []))])
            final_seasons.append((key, urls))
        elif info["type"] in ["normal", "hs"]:
            urls = [info["url"]]
            urls.extend([v[1] for v in sorted(info.get("variants", []))])
            final_seasons.append((key, urls))
        elif info["type"] in ["film", "oav"]:
            final_seasons.append((key, [info["url"]]))
    return final_seasons

# ── Analyse JS anime-sama ─────────────────────────────────────────────────────
def parse_eps_arrays(js_text):
    eps_blocks = re.findall(r"var\s+eps\d+\s*=\s*\[(.*?)\][\s;]?", js_text, re.DOTALL)
    results = []
    for block in eps_blocks:
        all_urls = re.findall(r"'(https?://[^']+)'", block)
        compatible = [c for u in all_urls if (c := classify_link(u))]
        results.append({"total": len(all_urls), "compatible": len(compatible), "links": compatible})
    results.sort(key=lambda x: (x["compatible"], x["total"]), reverse=True)
    if len(results) > 1:
        best = results[0]
        tied = [
            r for r in results
            if r["compatible"] == best["compatible"] and r["total"] == best["total"]
        ]
        if len(tied) > 1:
            results[0] = random.choice(tied)
    return results

def classify_link(url):
    if "sibnet" in url:
        return ("sibnet", url)
    if "vidmoly" in url:
        m = re.search(r"embed-([\w]+)\.html", url)
        if m:
            return ("vidmoly", m.group(1))
    if "sendvid" in url:
        return ("sendvid", url)
    if "movearnpre" in url:
        return None  # hébergeur non supporté, ignoré
    return None

def extract_video_links(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
    except Exception:
        return []
    eps_list = parse_eps_arrays(r.text)
    return [eps["links"] for eps in eps_list] if eps_list else []

def get_vidmoly_m3u8(video_id):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://vidmoly.biz/",
        "Accept": "text/html,application/xhtml+xml",
    }
    url = f"https://vidmoly.biz/embed-{video_id}.html"
    for attempt in range(5):
        try:
            resp = session.get(url, headers=headers, timeout=15)
            if resp.status_code == 404:
                return None
            m = re.search(
                r'https?://[^\s"\']+\.m3u8[^\s"\']*',
                resp.content.decode("utf-8", errors="ignore")
            )
            if m:
                return m.group(0)
        except Exception:
            pass
        if attempt < 4:
            time.sleep(1)
    return None

# ── Couverture anime ──────────────────────────────────────────────────────────
def get_anime_image(anime_name, folder_name, formatted_url_name):
    try:
        img_data = None
        base_img_url = (
            "https://raw.githubusercontent.com/Anime-Sama/IMG"
            f"/img/contenu/{formatted_url_name}.jpg"
        )
        r = requests.get(base_img_url, timeout=10)
        if r.status_code == 200:
            img_data = r.content
        else:
            url_name = anime_name.replace(" ", "+")
            r2 = requests.get(f"https://api.jikan.moe/v4/anime?q={url_name}&limit=1", timeout=10)
            r2.raise_for_status()
            data = r2.json()
            if data["data"]:
                r3 = requests.get(data["data"][0]["images"]["jpg"]["large_image_url"], timeout=10)
                r3.raise_for_status()
                img_data = r3.content
        if not img_data:
            return
        jpg_path = os.path.join(folder_name, "cover.jpg")
        with open(jpg_path, 'wb') as f:
            f.write(img_data)
        if pil_available and platform.system() == "Windows":
            ico_path = os.path.join(folder_name, "folder.ico")
            image = _Image.open(_io.BytesIO(img_data))
            size = 256
            sq = _Image.new('RGBA', (size, size), (0, 0, 0, 0))
            w, h = image.size
            if w > h:
                nh = int(h * size / w)
                ri = image.resize((size, nh))
                sq.paste(ri, (0, (size - nh) // 2))
            else:
                nw = int(w * size / h)
                ri = image.resize((nw, size))
                sq.paste(ri, ((size - nw) // 2, 0))
            sq.save(ico_path, format='ICO', sizes=[(size, size)])
            ini = (
                "[.ShellClassInfo]\r\nIconResource=folder.ico,0\r\n"
                "[ViewState]\r\nMode=\r\nVid=\r\nFolderType=Generic\r\n"
            )
            with open(os.path.join(folder_name, "desktop.ini"), "w", encoding="utf-16-le") as f:
                f.write("\ufeff" + ini)
            if os.name == 'nt':
                os.system(f'attrib +s "{folder_name}"')
                os.system(f'attrib +h +s "{os.path.join(folder_name, "desktop.ini")}"')
                os.system(f'attrib +h "{ico_path}"')
    except Exception:
        pass

# ── Détection dernier épisode ─────────────────────────────────────────────────
def find_last_downloaded_episode(folder_path):
    if not os.path.exists(folder_path):
        return None, None
    pattern = re.compile(r's(\w+)_e(\d+)\.mp4')
    episodes = []
    for file in os.listdir(folder_path):
        m = pattern.match(file)
        if m:
            episodes.append((m.group(1), int(m.group(2))))
    if not episodes:
        return None, None
    def sk(x):
        season, ep = x
        sn = season.replace('hs', '')
        if sn.isdigit():
            return (0, int(sn), 'hs' in season, ep)
        if season == "film":
            return (1, 0, False, ep)
        if season == "oav":
            return (2, 0, False, ep)
        return (3, str(season), False, ep)
    episodes.sort(key=sk, reverse=True)
    return episodes[0]

# ═══════════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════════
_APP_CSS = """
Screen { background: #0a0a0a; color: #d0d0d0; }

.banner {
    color: #d0d0d0;
    text-align: center;
    padding: 0 2;
    height: 1;
    text-style: bold;
    background: #0a0a0a;
}

MenuScreen { align: center middle; }

#menu-wrap {
    width: 1fr;
    max-width: 72;
    height: auto;
    max-height: 95vh;
    border: heavy #3a3a3a;
    background: #0f0f0f;
    padding: 0 0 1 0;
}

#menu-title {
    background: #0c0c0c;
    color: #ffffff;
    text-align: center;
    padding: 0 2;
    text-style: bold;
    border-bottom: solid #252525;
    height: 1;
}

#menu-subtitle {
    color: #909090;
    text-align: center;
    padding: 0 1;
    text-style: italic;
    height: 1;
    border-bottom: solid #1a1a1a;
}

#menu-list {
    height: auto;
    max-height: 36;
    border: none;
    background: transparent;
    margin: 1 2;
    overflow-y: auto;
}

#menu-list ListItem {
    padding: 1 2;
    color: #606060;
    background: transparent;
    height: 3;
}

#menu-list ListItem.--highlight {
    background: #181818;
    color: #ffffff;
    text-style: bold;
    border-left: heavy #d0d0d0;
}

#menu-hint {
    color: #454545;
    text-align: center;
    padding: 0 2;
    border-top: solid #252525;
    height: 1;
    margin-top: 1;
}

InputScreen { align: center middle; }
#input-wrap {
    width: 1fr; max-width: 70; height: auto;
    border: heavy #3a3a3a; background: #0f0f0f; padding: 1 3;
}
#input-title { color: #ffffff; text-style: bold; text-align: center; padding-bottom: 1; border-bottom: solid #252525; }
#input-subtitle { color: #909090; text-align: center; text-style: italic; padding-bottom: 1; height: 1; }
#input-field { border: solid #252525; background: #080808; color: #e8e8e8; width: 100%; margin-top: 1; }
#input-field:focus { border: solid #d0d0d0; }
#input-hint { color: #454545; text-align: center; padding-top: 1; height: 1; }

ResultScreen { align: center middle; }
#result-wrap { width: 1fr; max-width: 72; height: auto; max-height: 95vh; border: heavy #3a3a3a; background: #0f0f0f; padding: 0 0 1 0; }
#result-title { background: #0c0c0c; color: #ffffff; text-align: center; padding: 0 2; text-style: bold; border-bottom: solid #252525; height: 1; }
#result-subtitle { color: #909090; text-align: center; padding: 0 1; text-style: italic; height: 1; border-bottom: solid #1a1a1a; }
#result-body { height: auto; max-height: 28; overflow-y: auto; padding: 1 3; padding-bottom: 1; }
#result-hint { color: #454545; text-align: center; border-top: solid #252525; padding-top: 1; height: 1; margin-top: 1; }

SplashScreen { align: center middle; background: #0a0a0a; }
#splash-wrap { width: 1fr; max-width: 74; height: auto; border: heavy #3a3a3a; background: #0f0f0f; padding: 2 4; align: center middle; }
#splash-ascii { color: #d0d0d0; text-align: center; text-style: bold; padding: 1 0; height: auto; }
#splash-step { color: #ffffff; text-style: bold; text-align: center; padding: 1 0; height: 1; }
#splash-sub { color: #909090; text-align: center; text-style: italic; height: 1; padding-bottom: 1; }
#splash-spinner { color: #d0d0d0; text-align: center; text-style: bold; height: 1; margin-top: 1; }

LoadingScreen, WorkingScreen { align: center middle; }
#loading-wrap { width: 1fr; max-width: 68; height: auto; border: heavy #3a3a3a; background: #0f0f0f; padding: 2 4; align: center middle; }
#loading-title { color: #ffffff; text-style: bold; text-align: center; padding-bottom: 1; }
#loading-status { color: #606060; text-align: center; text-style: italic; height: 1; padding-bottom: 1; }
#loading-spinner { color: #d0d0d0; text-align: center; text-style: bold; height: 1; margin-top: 1; }

ProgressBar { width: 70%; margin: 1 0; }
ProgressBar > .bar--bar  { color: #909090; }
ProgressBar > .bar--complete { color: #d0d0d0; }

DownloadScreen { align: center middle; }
#dl-wrap { width: 1fr; max-width: 82; height: auto; max-height: 95vh; border: heavy #3a3a3a; background: #0f0f0f; padding: 1 3; }
#dl-title { color: #ffffff; text-style: bold; text-align: center; padding: 0 1; height: 1; }
#dl-subtitle { color: #909090; text-align: center; text-style: italic; padding: 0 1; height: 1; }
#dl-info { color: #606060; text-align: center; padding: 0 1; height: 1; }
#dl-progress { width: 70%; margin: 1 0; }
#dl-log { height: 14; background: #060606; border: solid #1a1a1a; padding: 0 1; margin: 0 0 1 0; }
#dl-hint { color: #454545; text-align: center; border-top: solid #252525; padding-top: 1; height: 1; }
Center { align: center middle; width: 100%; height: auto; }
"""

_BANNER = (
    f"[bold #d0d0d0]🌸  CO-CHAN[/]  [#909090]·[/]"
    f"  [bold white]ANIME DOWNLOADER[/]  [#909090]·[/]"
    f"  [dim #909090]v{VERSION}[/]"
)

_SPLASH_ART = (
    "  ════════════════════════════════════\n"
    "\n"
    "   ██████╗ ██████╗        ██████╗██╗  ██╗ █████╗ ███╗  ██╗\n"
    "  ██╔════╝██╔═══██╗      ██╔════╝██║  ██║██╔══██╗████╗ ██║\n"
    "  ██║     ██║   ██║      ██║     ███████║███████║██╔██╗██║\n"
    "  ██║     ██║   ██║      ██║     ██╔══██║██╔══██║██║╚████║\n"
    "  ╚██████╗╚██████╔╝      ╚██████╗██║  ██║██║  ██║██║ ╚███║\n"
    "   ╚═════╝ ╚═════╝        ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚══╝\n"
    "\n"
    "  ════════════════════════════════════"
)

# ═══════════════════════════════════════════════════════════════════════════════
# App Textual
# ═══════════════════════════════════════════════════════════════════════════════
_APP: "CoChanApp | None" = None

class CoChanApp(App):
    CSS = _APP_CSS
    BINDINGS = [Binding("ctrl+c", "quit_app", show=False)]
    def __init__(self, main_fn):
        super().__init__()
        self._main_fn = main_fn
    async def on_mount(self):
        global _APP
        _APP = self
        self.run_worker(self._main_fn(), exclusive=True)
    def action_quit_app(self):
        _goodbye()

async def _push_and_wait(screen):
    loop = asyncio.get_running_loop()
    fut: asyncio.Future = loop.create_future()
    def _cb(result):
        if not fut.done():
            loop.call_soon_threadsafe(fut.set_result, result)
    _APP.push_screen(screen, _cb)
    return await fut

# ── ConsoleUI ─────────────────────────────────────────────────────────────────
class ConsoleUI:
    @staticmethod
    def enable_ansi():
        if os.name == 'nt' and ctypes:
            try:
                ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
            except Exception:
                pass
    @staticmethod
    def display_len(s):
        count = 0
        for ch in s:
            cp = ord(ch)
            if cp in (0xFE0E, 0xFE0F, 0x200D, 0x20E3): continue
            if 0x0300 <= cp <= 0x036F: continue
            is_wide = (0x1F000 <= cp <= 0x1FFFF or 0x2600 <= cp <= 0x27BF or
                       0x2B00 <= cp <= 0x2BFF or 0xFE30 <= cp <= 0xFE4F or
                       0x3000 <= cp <= 0x9FFF or 0xAC00 <= cp <= 0xD7AF)
            count += 2 if is_wide else 1
        return count
    @staticmethod
    async def navigate(options, title="MENU", subtitle="") -> int:
        if not options or _APP is None: return -1
        r = await _push_and_wait(MenuScreen(options, title, subtitle))
        return r if r is not None else -1
    @staticmethod
    async def input_screen(title, prompt_text, subtitle="") -> str:
        if _APP is None: return ""
        r = await _push_and_wait(InputScreen(title, prompt_text, subtitle))
        return r or ""
    @staticmethod
    async def result_screen(lines, pause=True, title="", subtitle=""):
        if _APP: await _push_and_wait(ResultScreen(lines, pause, title=title, subtitle=subtitle))
    @staticmethod
    async def loading_screen(title, duration=1.5):
        if _APP: await _push_and_wait(LoadingScreen(title, duration))
    @staticmethod
    async def working(title, fn, *args, **kwargs):
        """Affiche un loading screen PENDANT que fn(*args) tourne
        en thread, retourne son résultat.
        """
        if _APP is None: return fn(*args, **kwargs)
        return await _push_and_wait(WorkingScreen(title, fn, *args, **kwargs))
    @staticmethod
    def info(m):
        if _APP: _APP.notify(_strip_ansi(m), severity="information", timeout=4)
    @staticmethod
    def warn(m):
        if _APP: _APP.notify(_strip_ansi(m), severity="warning", timeout=5)

# ── Écrans ────────────────────────────────────────────────────────────────────
class MenuScreen(ModalScreen):
    BINDINGS = [Binding("enter", "select", show=False), Binding("escape", "cancel", show=False)]
    def __init__(self, options, title="MENU", subtitle=""):
        super().__init__(); self._options = options; self._title = title; self._subtitle = subtitle
    def compose(self) -> ComposeResult:
        with Vertical(id="menu-wrap"):
            yield Static(_BANNER, markup=True, classes="banner")
            yield Static(self._title, id="menu-title")
            yield Static(self._subtitle or " ", id="menu-subtitle")
            with ListView(id="menu-list"):
                for opt in self._options: yield ListItem(Label(_strip_ansi(opt)))
            yield Static("↑↓ Naviguer  ·  ↵ Valider  ·  Échap Retour", id="menu-hint")
    def on_mount(self): self.query_one("#menu-list", ListView).focus()
    def on_list_view_selected(self, event): _safe_dismiss(self, event.list_view.index)
    def action_select(self): _safe_dismiss(self, self.query_one("#menu-list", ListView).index)
    def action_cancel(self): _safe_dismiss(self, -1)


class InputScreen(ModalScreen):
    BINDINGS = [Binding("escape", "cancel", show=False)]

    def __init__(self, title, prompt, subtitle=""):
        super().__init__()
        self._title    = title
        self._prompt   = prompt
        self._subtitle = subtitle
        self._buffer   = ""

    # ── Termux : saisie manuelle touche par touche ────────────────────────────
    def _render_buffer(self):
        txt = self._buffer or ""
        try:
            self.query_one("#input-field", Static).update(
                f"[bold #e8e8e8]{txt}[/][dim #d0d0d0]\u258c[/]" if txt
                else f"[dim #606060]{self._prompt}[/][dim #d0d0d0]\u258c[/]"
            )
        except Exception:
            pass

    def _show_keyboard(self):
        """Demande à Android d'afficher le clavier virtuel."""
        for cmd in [
            ["termux-show-keyboard"],
            ["am", "broadcast", "-a", "termux.app.SHOW_KEYBOARD"],
        ]:
            try:
                subprocess.Popen(  # pylint: disable=consider-using-with
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                continue

    def on_key(self, event) -> None:
        if not _is_termux():
            return
        key = event.key
        char = event.character  # vrai caractère unicode tapé (None pour les touches spéciales)

        # Touches spéciales
        if key == "enter":
            _safe_dismiss(self, self._buffer.strip())
            return
        if key in ("backspace", "ctrl+h"):
            self._buffer = self._buffer[:-1]
            self._render_buffer()
            return
        if key == "escape":
            _safe_dismiss(self, "")
            return
        if key == "ctrl+w":
            parts = self._buffer.rstrip().rsplit(" ", 1)
            self._buffer = parts[0] + " " if len(parts) > 1 else ""
            self._render_buffer()
            return

        # Tout caractère imprimable (espace, accents, chiffres, ponctuation…)
        # event.character contient le vrai caractère unicode, quelle que soit la touche
        if char and char.isprintable():
            self._buffer += char
            self._render_buffer()

    # ── Composition ──────────────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        with Vertical(id="input-wrap"):
            yield Static(_BANNER, markup=True, classes="banner")
            yield Static(self._title, id="input-title")
            yield Static(self._subtitle or " ", id="input-subtitle")
            if _is_termux():
                yield Static(
                    f"[dim #606060]{self._prompt}[/][dim #d0d0d0]\u258c[/]",
                    id="input-field", markup=True
                )
                yield Static("Tape · ↵ Valider · Échap Annuler", id="input-hint")
            else:
                yield Input(placeholder=self._prompt, id="input-field")
                yield Static("↵ Valider  ·  Échap Annuler", id="input-hint")

    def on_mount(self):
        if _is_termux():
            self.focus()
            self.set_timer(0.3, self._show_keyboard)
        else:
            self.query_one("#input-field", Input).focus()

    def on_input_submitted(self, event):
        _safe_dismiss(self, event.value.strip())

    def action_cancel(self):
        _safe_dismiss(self, "")


class ResultScreen(ModalScreen):
    can_focus = True
    BINDINGS = [Binding("enter","close",show=False), Binding("escape","close",show=False),
                Binding("space","close",show=False)]
    def __init__(self, lines, pause=True, timeout=None, title="", subtitle=""):
        super().__init__()
        self._lines = lines; self._pause = pause; self._timeout = timeout
        self._title = title; self._subtitle = subtitle
    def compose(self) -> ComposeResult:
        with Vertical(id="result-wrap"):
            yield Static(_BANNER, markup=True, classes="banner")
            if self._title:
                yield Static(self._title, id="result-title")
            if self._subtitle:
                yield Static(self._subtitle, id="result-subtitle")
            with ScrollableContainer(id="result-body"):
                for line in self._lines: yield Static(_strip_ansi(line))
            yield Static("↵ / Espace  ·  Continuer" if self._pause else " ", id="result-hint")
    def on_mount(self):
        self.focus()
        delay = self._timeout if self._timeout is not None else 1.5
        if not self._pause: self.set_timer(delay, self._auto_close)
    def _auto_close(self): _safe_dismiss(self, None)
    def action_close(self): _safe_dismiss(self, None)


class SplashScreen(ModalScreen):
    _SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    def __init__(self):
        super().__init__()
        self._spin_i = 0; self._done = False; self._result = None
    def _ui(self, fn, *a):
        if _APP:
            try: _APP.call_from_thread(fn, *a)
            except Exception: pass
    def _set_step(self, msg, pct):
        try:
            self.query_one("#splash-step", Static).update(msg)
            self.query_one("#splash-bar", ProgressBar).update(progress=pct)
        except Exception: pass
    def _set_sub(self, msg):
        try: self.query_one("#splash-sub", Static).update(msg)
        except Exception: pass
    def compose(self) -> ComposeResult:
        with Vertical(id="splash-wrap"):
            yield Static(_SPLASH_ART, id="splash-ascii")
            yield Static("🔍  Recherche du serveur actif…", id="splash-step")
            yield Static("Initialisation…", id="splash-sub")
            with Center():
                yield ProgressBar(total=100, show_eta=False, id="splash-bar")
            yield Static(self._SPIN[0], id="splash-spinner")
    def on_mount(self):
        self._spin_int = self.set_interval(0.08, self._tick)
        self.run_worker(self._run_sync, thread=True, exclusive=True)
    def _tick(self):
        if self._done: return
        self._spin_i = (self._spin_i + 1) % len(self._SPIN)
        try: self.query_one("#splash-spinner", Static).update(f"  {self._SPIN[self._spin_i]}")
        except Exception: pass
    def _run_sync(self):
        self._ui(self._set_step, "🔍  Recherche du serveur actif…", 20)
        self._ui(self._set_sub, "Connexion à anime-sama…")
        domain = _get_active_domain_sync()
        if domain:
            self._ui(self._set_step, "✅  Serveur trouvé !", 80)
            self._ui(self._set_sub, domain)
        else:
            self._ui(self._set_step, "⚠️  Domaine introuvable – saisie requise", 50)
        self._result = {"domain": domain or ""}
        if _APP:
            try: _APP.call_from_thread(self._finish)
            except Exception: _safe_dismiss(self, self._result)
    def _finish(self):
        self._done = True
        try:
            self._spin_int.stop()
            self.query_one("#splash-step", Static).update("✔   Prêt !")
            self.query_one("#splash-spinner", Static).update("")
            self.query_one("#splash-bar", ProgressBar).update(progress=100)
        except Exception: pass
        self.set_timer(0.4, lambda: _safe_dismiss(self, self._result))


class LoadingScreen(ModalScreen):
    _SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    def __init__(self, title, duration=1.5):
        super().__init__(); self._title = title; self._duration = duration
        self._dismissed = False; self._spin_i = 0
    def compose(self) -> ComposeResult:
        with Vertical(id="loading-wrap"):
            yield Static(_BANNER, markup=True, classes="banner")
            yield Static(self._title, id="loading-title")
            with Center():
                yield ProgressBar(total=100, show_eta=False, id="loading-bar")
            yield Static(f"  {self._SPIN[0]}", id="loading-spinner")
    def on_mount(self):
        self._step = 0; self._steps = 30
        self._interval = self.set_interval(self._duration / self._steps, self._tick)
        self._spin_int = self.set_interval(0.08, self._spin_tick)
    def _tick(self):
        if self._dismissed: return
        self._step += 1; pct = int(self._step * 100 / self._steps)
        try: self.query_one("#loading-bar", ProgressBar).update(progress=pct)
        except Exception: pass
        if self._step >= self._steps:
            self._dismissed = True
            try: self._interval.stop(); self._spin_int.stop()
            except Exception: pass
            _safe_dismiss(self, None)
    def _spin_tick(self):
        if self._dismissed: return
        self._spin_i = (self._spin_i + 1) % len(self._SPIN)
        try: self.query_one("#loading-spinner", Static).update(f"  {self._SPIN[self._spin_i]}")
        except Exception: pass


class WorkingScreen(ModalScreen):
    """Loading screen qui reste affiche PENDANT que fn(*args) tourne en thread.
    Injecte automatiquement progress_cb(pct) et status_cb(msg) si la fonction les accepte.
    """
    _SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, title, fn, *args, **kwargs):
        super().__init__()
        self._title = title; self._fn = fn; self._args = args; self._kwargs = kwargs
        self._spin_i = 0; self._pct = 0; self._real_progress = False

    def _ui(self, fn, *a):
        if _APP:
            try: _APP.call_from_thread(fn, *a)
            except Exception: pass

    def _progress_cb(self, pct):
        self._real_progress = True
        def _do():
            try: self.query_one("#loading-bar", ProgressBar).update(progress=min(int(pct), 100))
            except Exception: pass
        self._ui(_do)

    def _status_cb(self, msg):
        def _do():
            try: self.query_one("#loading-status", Static).update(msg)
            except Exception: pass
        self._ui(_do)

    def compose(self) -> ComposeResult:
        with Vertical(id="loading-wrap"):
            yield Static(_BANNER, markup=True, classes="banner")
            yield Static(self._title, id="loading-title")
            yield Static(" ", id="loading-status")
            with Center():
                yield ProgressBar(total=100, show_eta=False, id="loading-bar")
            yield Static(f"  {self._SPIN[0]}", id="loading-spinner")

    def on_mount(self):
        self._spin_int = self.set_interval(0.08, self._spin_tick)
        self._pulse_int = self.set_interval(0.15, self._pulse_tick)
        self.run_worker(self._run, thread=True, exclusive=True)

    def _spin_tick(self):
        self._spin_i = (self._spin_i + 1) % len(self._SPIN)
        try: self.query_one("#loading-spinner", Static).update(f"  {self._SPIN[self._spin_i]}")
        except Exception: pass

    def _pulse_tick(self):
        if self._real_progress: return
        self._pct = (self._pct + 3) % 101
        try: self.query_one("#loading-bar", ProgressBar).update(progress=self._pct)
        except Exception: pass

    def _run(self):
        import inspect
        sig = inspect.signature(self._fn)
        kw = dict(self._kwargs)
        if "progress_cb" in sig.parameters: kw["progress_cb"] = self._progress_cb
        if "status_cb"   in sig.parameters: kw["status_cb"]   = self._status_cb
        result = self._fn(*self._args, **kw)
        def _finish():
            try:
                self._spin_int.stop(); self._pulse_int.stop()
                self.query_one("#loading-bar", ProgressBar).update(progress=100)
                self.query_one("#loading-spinner", Static).update("  ✔")
            except Exception: pass
            self.set_timer(0.25, lambda: _safe_dismiss(self, result))
        self._ui(_finish)

# ═══════════════════════════════════════════════════════════════════════════════
# DownloadScreen – yt-dlp Python API
# ═══════════════════════════════════════════════════════════════════════════════
class _CancelError(Exception): pass

class DownloadScreen(ModalScreen):
    can_focus = True
    BINDINGS = [
        Binding("escape", "cancel_dl", show=False),
        Binding("enter",  "confirm",   show=False),
        Binding("space",  "confirm",   show=False),
    ]

    def __init__(self, candidates, filename, display_season, episode_num,
                 total_episodes, pause=True):
        """
        candidates : list of (link_type, link_value) – primary first, then fallbacks
        filename   : full path for the output .mp4
        """
        super().__init__()
        self._candidates   = candidates
        self._filename     = filename
        self._season       = display_season
        self._episode      = episode_num
        self._total        = total_episodes
        self._pause        = pause
        self._cancelled    = False
        self._result       = None   # True/False when done

    def _ui(self, fn, *a):
        if _APP:
            try: _APP.call_from_thread(fn, *a)
            except Exception: pass

    def _do_log(self, line, style="white"):
        try: self.query_one("#dl-log", RichLog).write(Text(line, style=style))
        except Exception: pass

    def _do_info(self, msg):
        try: self.query_one("#dl-info", Static).update(msg)
        except Exception: pass

    def _do_progress(self, pct):
        try: self.query_one("#dl-progress", ProgressBar).update(progress=min(pct, 100))
        except Exception: pass

    def _do_hint(self, msg):
        try: self.query_one("#dl-hint", Static).update(msg)
        except Exception: pass

    def _do_done(self, success):
        self._result = success
        if success:
            self._ui(self._do_progress, 100)
            if self._pause:
                hint = f"✔  S{self._season} E{self._episode}  ·  ↵ Continuer"
            else:
                hint = "✔  Épisode téléchargé — passage au suivant…"
        else:
            hint = "✖  Échec  ·  ↵ Fermer" if self._pause else "✖  Échec — passage au suivant…"
        self._ui(self._do_hint, hint)
        if not self._pause:
            self.set_timer(1.5, lambda: _safe_dismiss(self, self._result))

    def compose(self) -> ComposeResult:
        ep_lbl = f"S{self._season} · E{self._episode}/{self._total}"
        with Vertical(id="dl-wrap"):
            yield Static(_BANNER, markup=True, classes="banner")
            yield Static(f"⬇️   Téléchargement  –  {ep_lbl}", id="dl-title")
            yield Static(f"Fichier : {os.path.basename(self._filename)}", id="dl-subtitle")
            yield Static("Initialisation…", id="dl-info")
            with Center():
                yield ProgressBar(total=100, show_eta=False, id="dl-progress")
            yield RichLog(id="dl-log", highlight=False, markup=False)
            yield Static("⏬  Téléchargement en cours…  ·  Échap : Annuler", id="dl-hint")

    def on_mount(self):
        self.focus()
        self.run_worker(self._run, thread=True, exclusive=True)

    def action_cancel_dl(self):
        if self._result is not None:
            _safe_dismiss(self, self._result); return
        self._cancelled = True
        _safe_dismiss(self, False)

    def action_confirm(self):
        if self._result is not None:
            _safe_dismiss(self, self._result)

    @staticmethod
    def _source_label(link_type, link_value):
        """Retourne un label court : type + domaine si dispo."""
        try:
            import urllib.parse
            domain = urllib.parse.urlparse(
                link_value if link_value.startswith("http") else f"https://{link_value}"
            ).netloc or link_value
            # retire le sous-domaine www.
            domain = re.sub(r"^www\.", "", domain)
            if domain and domain != link_type:
                return f"{link_type} ({domain})"
        except Exception:
            pass
        return link_type

    def _run(self):
        success = False
        total = len(self._candidates)
        for idx, (link_type, link_value) in enumerate(self._candidates):
            if self._cancelled:
                break
            label = self._source_label(link_type, link_value)
            prefix = f"[{idx+1}/{total}] "
            self._ui(self._do_log, f"{prefix}Lecteur : {label}")
            success = self._try_download(link_type, link_value, idx)
            if success:
                break
            if self._cancelled:
                break
            if idx < len(self._candidates) - 1:
                next_label = self._source_label(*self._candidates[idx + 1])
                self._ui(self._do_log,
                    f"⚠  Échec [{idx+1}/{total}], passage à : {next_label}…", "dim white")
        self._ui(self._do_done, success)

    def _try_download(self, link_type, link_value, _attempt_idx):
        if self._cancelled:
            return False
        final_url = None
        if link_type == "vidmoly":
            self._ui(self._do_info, "Extraction m3u8 Vidmoly…")
            m3u8 = get_vidmoly_m3u8(link_value)
            if not m3u8:
                self._ui(self._do_log, "✖  m3u8 introuvable", "red")
                return False
            final_url = m3u8
        else:
            final_url = link_value

        # Format
        if link_type == "vidmoly":
            fmt = (
                "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
                "/bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
            )
        else:
            fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"

        # ── Dossier temp : même nom que l'épisode + .tmp (comme Co-flix) ──────
        ep_base  = os.path.splitext(os.path.basename(self._filename))[0]   # ex: s1_e3
        dl_dir   = os.path.dirname(self._filename)
        if _is_termux():
            # Sur Termux : temp dans le dossier de destination pour éviter
            # les problèmes de permission inter-partition
            temp_dir = os.path.join(dl_dir, ep_base + ".tmp")
        else:
            temp_dir = os.path.join(tempfile.gettempdir(), "anime-dl", ep_base + ".tmp")
        os.makedirs(temp_dir, exist_ok=True)

        # Fragments parallèles : adapté à la puissance de l'appareil
        concurrent = 3 if _is_termux() else 4

        cancelled_ref = [False]
        _season, _episode, _total = self._season, self._episode, self._total

        def _hook(d):
            if self._cancelled or cancelled_ref[0]:
                raise _CancelError("Annulé")
            if d["status"] == "downloading":
                pct_str = _strip_ansi(d.get("_percent_str", "0%")).strip().rstrip("%")
                try:
                    pct = float(pct_str)
                    self._ui(self._do_progress, int(pct))
                except ValueError:
                    pass
                speed  = _strip_ansi(d.get("_speed_str", "")).strip()
                eta    = _strip_ansi(d.get("_eta_str", "")).strip()
                total_s = _strip_ansi(d.get(
                    "_total_bytes_str",
                    d.get("_total_bytes_estimate_str", "")
                )).strip()
                down_s  = _strip_ansi(d.get("_downloaded_bytes_str", "")).strip()
                parts = []
                if pct_str: parts.append(f"⬇ {pct_str}%")
                if down_s and total_s: parts.append(f"{down_s}/{total_s}")
                if speed: parts.append(speed)
                if eta: parts.append(f"ETA {eta}")
                info = "  ·  ".join(p for p in parts if p)
                self._ui(self._do_info, info[:72])
            elif d["status"] == "finished":
                self._ui(self._do_progress, 99)
                self._ui(self._do_info, "✔  Fusion des flux…")
                self._ui(self._do_log, "✔  Fusion en cours…", "dim white")

        ydl_opts = {
            "outtmpl":                  self._filename,
            "quiet":                    True,
            "ignoreerrors":             True,
            "progress_hooks":           [_hook],
            "no_warnings":              True,
            "noprogress":               False,
            "format":                   fmt,
            "merge_output_format":      "mp4",
            "socket_timeout":           60,
            "retries":                  15,
            "fragment_retries":         15,
            "concurrent_fragment_downloads": concurrent,
            "retry_sleep_functions":    {"fragment": lambda n: 2},
            "skip_unavailable_fragments": True,
            "paths":                    {"temp": temp_dir},
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ret = ydl.download([final_url])
            if self._cancelled:
                return False
            if ret != 0:
                self._ui(self._do_log, f"✖  yt-dlp code {ret}", "red")
                return False
            mp4 = self._filename if self._filename.endswith(".mp4") else self._filename + ".mp4"
            if not os.path.isfile(mp4) or os.path.getsize(mp4) == 0:
                self._ui(self._do_log, "✖  Fichier vide ou absent", "red")
                return False
            # Nettoyage du dossier temp
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            self._ui(self._do_log, f"✔  Sauvegardé : {os.path.basename(mp4)}", "bold white")
            return True
        except _CancelError:
            cancelled_ref[0] = True
            return False
        except Exception as e:
            self._ui(self._do_log, f"✖  Erreur : {e}", "red")
            return False

# ─── Sentinel et menu post-épisode (comme Co-flix) ───────────────────────────
_NEXT_SEASON = object()

async def _post_episode_menu(n_total, current_ep, season_key, seasons):
    """
    Menu affiché après le téléchargement d'un épisode précis.
    Retourne : episode_num | _NEXT_SEASON | None
    """
    is_last = current_ep >= n_total
    season_keys = [sk for sk, _ in seasons]
    cur_idx     = season_keys.index(season_key) if season_key in season_keys else -1
    has_next_s  = cur_idx >= 0 and cur_idx + 1 < len(seasons)

    if is_last and has_next_s:
        next_sk  = season_keys[cur_idx + 1]
        title    = f"🏁  FIN SAISON {season_key}  →  SAISON {next_sk} ?"
        subtitle = f"Dernier épisode de la saison {season_key}"
    elif is_last:
        title    = f"🏁  FIN DE SAISON {season_key}"
        subtitle = "Dernier épisode téléchargé"
    else:
        title    = f"✔  ÉPISODE {current_ep:02d}  TÉLÉCHARGÉ"
        subtitle = f"Saison {season_key}  ·  {current_ep}/{n_total} épisodes"

    opts = []
    if not is_last:
        opts.append(f"▶   Épisode suivant  (E{current_ep+1:02d})")
    if is_last and has_next_s:
        opts.append(f"⏭️   Passer à la saison {next_sk}")
    opts += ["📋  Choisir un autre épisode", "📙  Retour"]

    idx = await ConsoleUI.navigate(opts, title, subtitle)
    if idx == -1: return None
    label = opts[idx]
    if label.startswith("▶"):   return current_ep + 1
    if label.startswith("⏭️"):  return _NEXT_SEASON
    if label.startswith("📋"):
        return await _choose_episode_number(n_total, f"ÉPISODE  –  Saison {season_key}",
                                             f"{n_total} épisode{'s' if n_total > 1 else ''}")
    return None   # Retour


# ═══════════════════════════════════════════════════════════════════════════════
# Sélecteurs TUI
# ═══════════════════════════════════════════════════════════════════════════════
async def choose_season_mode(seasons, subtitle=""):
    """
    Retourne (mode, season_key) où mode est :
      'all'         → tout télécharger
      'season'      → une saison complète
      'n_eps'       → N premiers épisodes depuis le début
      'ep_range'    → plage A→B même saison
      'multi_range' → plage multi-saisons
      'from_ep'     → depuis un épisode précis
      'one_ep'      → un seul épisode (+ boucle post-épisode)
      None          → retour
    """
    has_multi = len(seasons) > 1
    opts = [
        "⬇️   Tout télécharger  (toutes les saisons)",
        "📅  Saison complète",
        "🔢  N épisodes  (depuis le début)",
        "📎  Plage  –  épisode A à B  (même saison)",
    ]
    if has_multi:
        opts.append("🌐  Plage multi-saisons  (ex: S1E5 → S3E2)")
    opts += [
        "▸   Point de départ précis",
        "🎯  Un seul épisode  (+ menu après)",
        "📙  Retour",
    ]

    idx = await ConsoleUI.navigate(opts, "MODE DE TÉLÉCHARGEMENT", subtitle)
    last = len(opts) - 1
    if idx in (-1, last): return None, None

    IDX_ALL        = 0
    IDX_SEASON     = 1
    IDX_N_EPS      = 2
    IDX_EP_RANGE   = 3
    IDX_MULTI      = 4 if has_multi else None
    IDX_FROM_EP    = 5 if has_multi else 4
    IDX_ONE_EP     = 6 if has_multi else 5

    if idx == IDX_ALL: return "all", None
    if has_multi and idx == IDX_MULTI: return "multi_range", None

    # Choisir une saison pour les modes restants
    s_opts = [f"📅  Saison {s_key}" for s_key, _ in seasons]
    s_idx = await ConsoleUI.navigate(
        s_opts, "CHOISIR LA SAISON",
        f"{len(seasons)} saison(s) disponible(s)"
    )
    if s_idx == -1: return None, None
    season_key = seasons[s_idx][0]

    if idx == IDX_SEASON:   return "season",    season_key
    if idx == IDX_N_EPS:    return "n_eps",     season_key
    if idx == IDX_EP_RANGE: return "ep_range",  season_key
    if idx == IDX_FROM_EP:  return "from_ep",   season_key
    if idx == IDX_ONE_EP:   return "one_ep",    season_key
    return None, None


async def _choose_episode_number(n_total, title_prefix, subtitle=""):
    """Sélecteur d'épisode (numéros seulement, sans titre)."""
    opts = [
        f"▸  E{str(i).zfill(2)}" + ("  🏁" if i == n_total else "")
        for i in range(1, n_total + 1)
    ]
    sub = subtitle or f"{n_total} épisode{'s' if n_total > 1 else ''}"
    idx = await ConsoleUI.navigate(opts, title_prefix, sub)
    return None if idx == -1 else idx + 1   # 1-based episode number


async def _choose_episode_flat(flat_list, title_prefix, subtitle=""):
    """
    Sélecteur multi-saisons.
    flat_list : [(season_key, episode_num), ...]
    Retourne le tuple choisi ou None.
    """
    n = len(flat_list)
    opts = []
    for i, (sk, ep) in enumerate(flat_list):
        marker = "  🏁" if i == n - 1 else ""
        opts.append(f"▸  S{sk.upper()}·E{str(ep).zfill(2)}{marker}")
    sub = subtitle or f"{n} épisode{'s' if n > 1 else ''} (toutes saisons)"
    idx = await ConsoleUI.navigate(opts, title_prefix, sub)
    return None if idx == -1 else flat_list[idx]

# ─── Helpers chargement saison ────────────────────────────────────────────────
def _load_season_data(_season_key, url_list, progress_cb=None, status_cb=None):
    """
    Charge les eps_arrays pour une saison.
    Retourne (all_eps_arrays, n_total) ou n_total est le vrai nombre
    d episodes dans le JS (total URLs, pas seulement les liens compatibles).
    """
    all_eps_arrays = []
    n_total = 0
    total = max(len(url_list), 1)
    for idx, url in enumerate(url_list):
        if progress_cb: progress_cb(int(idx / total * 95))
        if status_cb: status_cb(f"Fichier {idx + 1}/{total}…")
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue
        except Exception:
            continue
        eps_list = parse_eps_arrays(r.text)
        if not eps_list:
            continue
        n_total = max(n_total, max(e["total"] for e in eps_list))
        all_eps_arrays.extend([e["links"] for e in eps_list])
        if status_cb: status_cb(f"Fichier {idx + 1}/{total}  ✔  ({n_total} épisodes)")
    return all_eps_arrays, n_total


def _best_candidates(all_eps_arrays, episode_num):
    """Retourne la liste de (link_type, link_value) pour un épisode (primary+fallbacks)."""
    ep_idx = episode_num - 1
    candidates = []
    for arr in all_eps_arrays:
        if ep_idx < len(arr):
            candidates.append(arr[ep_idx])
    return candidates

# ═══════════════════════════════════════════════════════════════════════════════
# Fonctions de téléchargement TUI
# ═══════════════════════════════════════════════════════════════════════════════
async def _run_download(candidates, filename, season_key, ep_num, n_total, pause=True):
    """Lance le DownloadScreen et retourne True/False."""
    if not candidates:
        await ConsoleUI.result_screen([f"  ✖  Aucun lien disponible pour S{season_key} E{ep_num}."])
        return False
    result = await _push_and_wait(
        DownloadScreen(candidates, filename, season_key, ep_num, n_total, pause=pause))
    return bool(result)


async def download_season_all(anime_name, folder_name, season_key, url_list, _base_url_path,
                               start_ep=1, only_one=False):
    """Télécharge tous les épisodes d'une saison (ou depuis start_ep)."""
    result = await ConsoleUI.working(f"Chargement saison {season_key}…",
                                      _load_season_data, season_key, url_list)
    all_eps_arrays, n_total = result
    if not all_eps_arrays or n_total == 0:
        await ConsoleUI.result_screen([f"  ✖  Saison {season_key} inaccessible."])
        return

    dl_dir = os.path.join(get_download_path(), folder_name)
    os.makedirs(dl_dir, exist_ok=True)

    if start_ep == 1:
        get_anime_image(anime_name, dl_dir, format_url_name(anime_name))

    ok, err = 0, 0
    eps_to_dl = [start_ep] if only_one else range(start_ep, n_total + 1)
    for ep_num in eps_to_dl:
        if ep_num < 1 or ep_num > n_total:
            await ConsoleUI.result_screen([f"  ✖  Épisode {ep_num} hors plage (1–{n_total})."])
            break
        candidates = _best_candidates(all_eps_arrays, ep_num)
        filename = os.path.join(dl_dir, f"s{season_key}_e{ep_num}.mp4")
        if not check_disk_space():
            await ConsoleUI.result_screen(["  ⚠   Espace disque insuffisant — arrêt."])
            break
        success = await _run_download(
            candidates, filename, season_key, ep_num, n_total, pause=True
        )
        if success: ok += 1
        else: err += 1

    await ConsoleUI.result_screen([
        f"  ✔  Saison {season_key} terminée",
        f"  ✔  Réussis : {ok}",
        f"  ⚠   Erreurs : {err}",
        f"  📂  {dl_dir}"])


async def download_n_episodes(anime_name, folder_name, season_key, url_list, n):
    """Télécharge les N premiers épisodes d'une saison depuis le début."""
    result = await ConsoleUI.working(f"Chargement saison {season_key}…",
                                      _load_season_data, season_key, url_list)
    all_eps_arrays, n_total = result
    if not all_eps_arrays or n_total == 0:
        await ConsoleUI.result_screen([f"  ✖  Saison {season_key} inaccessible."])
        return
    n = min(n, n_total)
    dl_dir = os.path.join(get_download_path(), folder_name)
    os.makedirs(dl_dir, exist_ok=True)
    get_anime_image(anime_name, dl_dir, format_url_name(anime_name))

    ok, err = 0, 0
    for ep_num in range(1, n + 1):
        if not check_disk_space():
            await ConsoleUI.result_screen(["  ⚠   Espace disque insuffisant — arrêt."])
            break
        candidates = _best_candidates(all_eps_arrays, ep_num)
        filename = os.path.join(dl_dir, f"s{season_key}_e{ep_num}.mp4")
        success = await _run_download(
            candidates, filename, season_key, ep_num, n_total, pause=True
        )
        if success: ok += 1
        else: err += 1

    await ConsoleUI.result_screen([
        f"  ✔  {n} premiers épisodes  –  Saison {season_key}",
        f"  ✔  Réussis : {ok}/{n}",
        f"  ⚠   Erreurs : {err}",
        f"  📂  {dl_dir}"])


async def download_ep_range(anime_name, folder_name, season_key, url_list, _base_url_path):
    """Plage épisode A → B, même saison, avec sélecteur visuel."""
    result = await ConsoleUI.working(f"Chargement saison {season_key}…",
                                      _load_season_data, season_key, url_list)
    all_eps_arrays, n_total = result
    if not all_eps_arrays or n_total == 0:
        await ConsoleUI.result_screen([f"  ✖  Saison {season_key} inaccessible."])
        return

    ep_sub = f"Saison {season_key}  –  {n_total} épisode{'s' if n_total > 1 else ''}"
    start = await _choose_episode_number(
        n_total, f"DÉPART  –  Saison {season_key}", ep_sub + "  ·  Début"
    )
    if start is None: return

    end = await _choose_episode_number(n_total, f"FIN  –  Saison {season_key}",
                                        ep_sub + f"  ·  Depuis E{start:02d}, choisissez la fin")
    if end is None: return
    if end < start:
        start, end = end, start   # swap silencieux

    n_sel = end - start + 1
    dl_dir = os.path.join(get_download_path(), folder_name)
    os.makedirs(dl_dir, exist_ok=True)
    get_anime_image(anime_name, dl_dir, format_url_name(anime_name))

    ok, err = 0, 0
    for ep_num in range(start, end + 1):
        if not check_disk_space():
            await ConsoleUI.result_screen(["  ⚠   Espace disque insuffisant — arrêt."])
            break
        candidates = _best_candidates(all_eps_arrays, ep_num)
        filename = os.path.join(dl_dir, f"s{season_key}_e{ep_num}.mp4")
        success = await _run_download(
            candidates, filename, season_key, ep_num, n_total, pause=True
        )
        if success: ok += 1
        else: err += 1

    await ConsoleUI.result_screen([
        f"  ✔  PLAGE TERMINÉE  E{start:02d} → E{end:02d}",
        f"  ✔  Réussis : {ok}/{n_sel}",
        f"  ⚠   Erreurs : {err}",
        f"  📂  {dl_dir}"])


async def download_multi_range(anime_name, folder_name, seasons, _base_url_path):
    """Plage multi-saisons S1E5 → S3E2, sélection visuelle."""
    # Charger toutes les saisons en parallèle (via working screen)
    flat_all = []
    season_data = {}
    for sk, url_list in seasons:
        arrs, n = await ConsoleUI.working(f"Chargement saison {sk}…",
                                           _load_season_data, sk, url_list)
        if arrs and n > 0:
            season_data[sk] = (arrs, n)
            for ep in range(1, n + 1):
                flat_all.append((sk, ep))

    if not flat_all:
        await ConsoleUI.result_screen(["  ⚠   Aucun épisode chargé."])
        return

    n_all = len(flat_all)
    sub_all = f"{n_all} épisodes  ·  {len(season_data)} saison(s)"

    start_item = await _choose_episode_flat(flat_all, "DÉPART  –  Choisissez où commencer", sub_all)
    if start_item is None: return
    start_i = flat_all.index(start_item)

    flat_from = flat_all[start_i:]
    s_lbl = f"S{start_item[0].upper()}·E{start_item[1]:02d}"

    end_item = await _choose_episode_flat(flat_from, "FIN  –  Choisissez où arrêter",
                                           f"Depuis {s_lbl}  ·  Épisode final inclus")
    if end_item is None: return
    end_i = flat_all.index(end_item)

    selected = flat_all[start_i:end_i + 1]
    n_sel = len(selected)
    s_from = f"S{start_item[0].upper()}·E{start_item[1]:02d}"
    s_to   = f"S{end_item[0].upper()}·E{end_item[1]:02d}"

    dl_dir = os.path.join(get_download_path(), folder_name)
    os.makedirs(dl_dir, exist_ok=True)
    get_anime_image(anime_name, dl_dir, format_url_name(anime_name))

    ok, err = 0, 0
    for _ep_i, (sk, ep_num) in enumerate(selected, start=1):
        if not check_disk_space():
            await ConsoleUI.result_screen(["  ⚠   Espace disque insuffisant — arrêt.",
                                            f"  ✔  Épisodes complétés : {ok}/{n_sel}"])
            return
        arrs, n_total = season_data.get(sk, ([], 0))
        candidates = _best_candidates(arrs, ep_num)
        filename = os.path.join(dl_dir, f"s{sk}_e{ep_num}.mp4")
        success = await _run_download(candidates, filename, sk, ep_num, n_total, pause=True)
        if success: ok += 1
        else: err += 1

    await ConsoleUI.result_screen([
        "  ✔  PLAGE MULTI-SAISONS TERMINÉE",
        f"  📎  {s_from}  →  {s_to}",
        f"  ✔  Réussis : {ok}/{n_sel}",
        f"  ⚠   Erreurs : {err}",
        f"  📂  {dl_dir}"])


# ═══════════════════════════════════════════════════════════════════════════════
# ── Sélecteur de stockage Termux ─────────────────────────────────────────────
def _detect_android_storages():
    """Retourne une liste de (label, chemin_anime) pour chaque stockage accessible."""
    storages = []

    # Stockage interne toujours présent
    internal = "/storage/emulated/0/Download/anime"
    storages.append(("📱  Interne  —  /storage/emulated/0/Download", internal))

    # Stockage(s) externe(s) : cartes SD, clés USB…
    try:
        for entry in os.listdir("/storage"):
            if entry in ("emulated", "self"):
                continue
            base = f"/storage/{entry}"
            if not os.path.isdir(base):
                continue
            # Vérifie qu'on peut y accéder
            try:
                os.listdir(base)
            except PermissionError:
                continue
            # Cherche un sous-dossier Download ou utilise la racine
            for sub in ["Download", "Downloads", ""]:
                candidate = os.path.join(base, sub) if sub else base
                if os.path.isdir(candidate) or sub == "":
                    dest = os.path.join(candidate, "anime")
                    label = f"💾  Externe  —  {candidate}"
                    storages.append((label, dest))
                    break
    except Exception:
        pass

    return storages

async def _termux_pick_storage(dl_path: list):
    """Affiche un menu de choix de stockage et met à jour dl_path[0]."""
    storages = _detect_android_storages()

    if len(storages) == 1:
        # Pas de stockage externe détecté
        await ConsoleUI.result_screen([
            "  ⚠   Aucun stockage externe détecté.",
            "  📱  Stockage interne conservé :",
            f"  {storages[0][1]}",
        ])
        return

    opts = [label for label, _ in storages] + ["📙  Annuler"]
    idx = await ConsoleUI.navigate(opts, "STOCKAGE", "Choisir où télécharger les animes")
    if idx < 0 or idx >= len(storages):
        return

    _, chosen_path = storages[idx]
    try:
        os.makedirs(chosen_path, exist_ok=True)
        dl_path[0] = chosen_path
        _save_config({"download_dir": chosen_path})
        await ConsoleUI.result_screen([
            "  ✔  Stockage enregistré !",
            f"  📂  {chosen_path}",
        ])
    except Exception as e:
        await ConsoleUI.result_screen([f"  ✖  Impossible d'accéder à ce stockage : {e}"])


# Menu paramètres
# ═══════════════════════════════════════════════════════════════════════════════
async def menu_settings():
    dl_path = [get_download_path()]
    while True:
        if _is_termux():
            base_opts = ["📲  Choisir le device de stockage", "📂  Ouvrir le dossier actuel"]
        else:
            base_opts = ["📁  Changer le dossier de téléchargement", "📂  Ouvrir le dossier actuel"]
        options = base_opts + ["📙  Retour"]
        choice = await ConsoleUI.navigate(options, "PARAMÈTRES", f"Dossier : {dl_path[0]}")
        if choice in (-1, len(options) - 1): return
        if choice == 0:
            if _is_termux():
                await _termux_pick_storage(dl_path)
            else:
                new = await ConsoleUI.input_screen("DOSSIER", "Nouveau chemin complet")
                if new:
                    try:
                        os.makedirs(new, exist_ok=True)
                        dl_path[0] = os.path.abspath(new)
                        _save_config({"download_dir": dl_path[0]})
                        await ConsoleUI.result_screen(
                            ["  ✔  Dossier changé !", f"  📂  {dl_path[0]}"]
                        )
                    except Exception as e:
                        await ConsoleUI.result_screen([f"  ✖  Erreur : {e}"])
        elif choice == 1:
            if _is_termux():
                # Sur Termux : affiche le chemin pendant 15 secondes
                await _push_and_wait(ResultScreen(
                    ["  📂  Dossier de téléchargement :", "", f"  {dl_path[0]}"],
                    pause=False,
                    timeout=15,
                ))
            else:
                try:
                    if os.name == 'nt':
                        os.startfile(dl_path[0])  # pylint: disable=no-member
                    else:
                        subprocess.run(['xdg-open', dl_path[0]], check=False)
                    time.sleep(1)
                except Exception as e:
                    await ConsoleUI.result_screen([f"  ✖  {e}"])


# ═══════════════════════════════════════════════════════════════════════════════
# Menu principal téléchargement
# ═══════════════════════════════════════════════════════════════════════════════
async def menu_download(base_url):
    while True:
        # ── Saisie du nom ──────────────────────────────────────────────────
        anime_raw = await ConsoleUI.input_screen("ANIME", "Nom de l'anime",
                                                  subtitle="Ex: one piece, naruto, demon slayer…")
        if not anime_raw: return
        anime_name = normalize_anime_name(anime_raw)
        anime_cap  = anime_name.title()

        fmt_name = format_url_name(anime_name)
        exists = await ConsoleUI.working(f"Vérification de « {anime_cap} »…",
                                         check_anime_exists, base_url, fmt_name)
        if not exists:
            await ConsoleUI.result_screen([
                f"  ✖  « {anime_cap} » introuvable.",
                "  Essayez le nom japonais ou vérifiez l'orthographe."])
            continue

        # ── Langue ────────────────────────────────────────────────────────
        langs = await ConsoleUI.working("Détection des langues disponibles…",
                                        check_available_languages, base_url, fmt_name)
        if langs:
            l_opts = [f"[FR]  {l.upper()}" for l in langs] + ["🎌  VOSTFR"]
            l_idx = await ConsoleUI.navigate(l_opts, "VERSION", f"« {anime_cap} »")
            if l_idx == -1: continue
            selected_lang = langs[l_idx] if l_idx < len(langs) else "vostfr"
        else:
            selected_lang = "vostfr"
            ConsoleUI.info("Aucune VF — VOSTFR sélectionné automatiquement.")

        folder_name = format_folder_name(anime_cap, selected_lang)

        # ── Saisons ────────────────────────────────────────────────────────
        raw_season_info = await ConsoleUI.working("Détection des saisons…",
                                                   check_seasons, base_url, fmt_name, selected_lang)
        seasons = resolve_season_choices(raw_season_info)

        if not seasons:
            await ConsoleUI.result_screen([f"  ✖  Aucune saison disponible pour « {anime_cap} »."])
            continue

        # ── Vérification reprise ───────────────────────────────────────────
        dl_dir = os.path.join(get_download_path(), folder_name)
        last_s, last_e = find_last_downloaded_episode(dl_dir)
        if last_s is not None:
            resume_opts = [
                f"▶   Reprendre depuis S{last_s} E{last_e}",
                "📋  Choisir un autre mode",
                "📙  Retour",
            ]
            r_idx = await ConsoleUI.navigate(resume_opts, "REPRISE DÉTECTÉE",
                                              f"{anime_cap} ({selected_lang.upper()})"
                                              f"  ·  Dernier : S{last_s} E{last_e}")
            if r_idx in (2, -1): continue
            if r_idx == 0:
                url_list = dict(seasons).get(last_s)
                if url_list:
                    await download_season_all(anime_name, folder_name, last_s, url_list,
                                               base_url, start_ep=last_e)
                continue

        # ── Mode de téléchargement ─────────────────────────────────────────
        mode, season_key = await choose_season_mode(
            seasons,
            subtitle=f"{anime_cap}  ({selected_lang.upper()})  ·  {len(seasons)} saison(s)")
        if mode is None: continue

        if mode == "all":
            for sk, url_list in seasons:
                await download_season_all(anime_name, folder_name, sk, url_list, base_url)
            continue

        if mode == "multi_range":
            await download_multi_range(anime_name, folder_name, seasons, base_url)
            continue

        url_list = dict(seasons)[season_key]

        if mode == "season":
            await download_season_all(anime_name, folder_name, season_key, url_list, base_url)

        elif mode == "n_eps":
            n_str = await ConsoleUI.input_screen(
                "NOMBRE D'ÉPISODES", "Combien d'épisodes ?",
                subtitle="À partir du 1er épisode de la saison")
            try:
                n = int(n_str)
                if n <= 0: raise ValueError
            except (ValueError, TypeError):
                await ConsoleUI.result_screen(["  ✖  Nombre invalide."])
                continue
            await download_n_episodes(anime_name, folder_name, season_key, url_list, n)

        elif mode == "ep_range":
            await download_ep_range(anime_name, folder_name, season_key, url_list, base_url)

        elif mode == "from_ep":
            result = await ConsoleUI.working(f"Chargement saison {season_key}…",
                                              _load_season_data, season_key, url_list)
            _, n_total = result
            if n_total == 0:
                await ConsoleUI.result_screen([f"  ✖  Saison {season_key} inaccessible."])
                continue
            ep_sub = f"Saison {season_key}  –  {n_total} épisodes"
            start = await _choose_episode_number(
                n_total, f"POINT DE DÉPART  –  S{season_key}", ep_sub
            )
            if start is None: continue
            await download_season_all(
                anime_name, folder_name, season_key,
                url_list, base_url, start_ep=start
            )

        elif mode == "one_ep":
            # Charge la saison initiale
            result = await ConsoleUI.working(f"Chargement saison {season_key}…",
                                              _load_season_data, season_key, url_list)
            arrs, n_total = result
            if n_total == 0:
                await ConsoleUI.result_screen([f"  ✖  Saison {season_key} inaccessible."])
                continue

            # Choisir le 1er épisode
            ep_num = await _choose_episode_number(
                n_total, f"CHOISIR L'ÉPISODE  –  S{season_key}",
                f"Saison {season_key}  –  {n_total} épisodes")
            if ep_num is None: continue

            # Variables de saison courante (peuvent changer via _NEXT_SEASON)
            cur_season_key  = season_key
            cur_arrs        = arrs
            cur_n_total     = n_total

            while ep_num is not None and ep_num is not _NEXT_SEASON:
                candidates = _best_candidates(cur_arrs, ep_num)
                filename   = os.path.join(dl_dir, f"s{cur_season_key}_e{ep_num}.mp4")
                os.makedirs(dl_dir, exist_ok=True)
                if not check_disk_space():
                    await ConsoleUI.result_screen(["  ⚠   Espace disque insuffisant."])
                    break
                success = await _run_download(
                    candidates, filename, cur_season_key,
                    ep_num, cur_n_total, pause=True
                )
                if not success:
                    await ConsoleUI.result_screen(["  ✖  Téléchargement échoué ou annulé."])
                ep_num = await _post_episode_menu(cur_n_total, ep_num, cur_season_key, seasons)

            # Passage à la saison suivante demandé
            if ep_num is _NEXT_SEASON:
                s_keys = [sk for sk, _ in seasons]
                cur_idx = s_keys.index(cur_season_key) if cur_season_key in s_keys else -1
                if cur_idx >= 0 and cur_idx + 1 < len(seasons):
                    next_sk, next_urls = seasons[cur_idx + 1]
                    result = await ConsoleUI.working(f"Chargement saison {next_sk}…",
                                                      _load_season_data, next_sk, next_urls)
                    _, next_n = result
                    if next_n > 0:
                        await download_season_all(anime_name, folder_name, next_sk,
                                                   next_urls, base_url)


# ═══════════════════════════════════════════════════════════════════════════════
# Main async
# ═══════════════════════════════════════════════════════════════════════════════
async def _app_main():
    setup = await _push_and_wait(SplashScreen())
    if not setup:
        setup = {"domain": ""}

    base_url = setup.get("domain") or ""
    if not base_url:
        # Saisie manuelle
        while True:
            domain_in = await ConsoleUI.input_screen(
                "SERVEUR INACCESSIBLE",
                "Ex: https://anime-sama.fr/catalogue/",
                subtitle="Impossible de détecter le domaine automatiquement")
            domain_in = domain_in.strip().rstrip("/")
            if domain_in:
                base_url = domain_in if domain_in.endswith("/") else domain_in + "/"
                break
            await ConsoleUI.result_screen(["  ✖  Le domaine ne peut pas être vide."])

    while True:
        choice = await ConsoleUI.navigate(
            ["🌸  Télécharger un anime", "⚙️   Paramètres", "✖   Quitter"],
            "  ◈  CO-CHAN  ◈", f"v{VERSION}  ·  anime-sama")
        if choice == 0:
            await menu_download(base_url)
        elif choice == 1:
            await menu_settings()
        elif choice in (2, -1):
            await ConsoleUI.result_screen(["  🌸  Merci d'avoir utilisé CO-CHAN !  🌸"], pause=False)
            _goodbye()


def _goodbye():
    if _APP:
        _APP.exit()
    else:
        os._exit(0)


def main():
    if os.name == "nt":
        os.system("title 🌸 CO-CHAN DOWNLOADER 🌸")
    ConsoleUI.enable_ansi()
    set_process_priority()
    CoChanApp(_app_main).run()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: _goodbye())
    signal.signal(signal.SIGTERM, lambda s, f: _goodbye())
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, lambda s, f: _goodbye())
    try:
        main()
    except KeyboardInterrupt:
        _goodbye()
    except Exception as e:
        import traceback
        print(f"\n  💥  ERREUR CRITIQUE : {e}\n")
        traceback.print_exc()
        try:
            input("\n  Appuyez sur Entrée pour quitter…")
        except (EOFError, OSError):
            pass
        _goodbye()
