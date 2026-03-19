import importlib.util
import io
import os
import platform
import random
import re
import shutil
import sys
import tempfile
import time

import requests
from yt_dlp import YoutubeDL

try:
    import ctypes
except ImportError:
    ctypes = None

try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    import tty
    import termios
    import select as _select
except ImportError:
    tty = termios = _select = None


# ── Détection plateforme ──────────────────────────────────────────────────────
def _is_termux():
    return (os.name != "nt" and (
        "ANDROID_STORAGE" in os.environ
        or "com.termux" in os.environ.get("PREFIX", "")
    ))

IS_ANDROID = _is_termux()


# ══════════════════════════════════════════════════════════════════════════════
#  INTERFACE PC — ConsoleUI (menus interactifs, logo ASCII, flèches)
# ══════════════════════════════════════════════════════════════════════════════
class ConsoleUI:
    RESET  = '\033[0m'
    BOLD   = '\033[1m'
    DIM    = '\033[2m'
    RED    = '\033[31m'
    GREEN  = '\033[32m'
    YELLOW = '\033[33m'
    CYAN   = '\033[36m'

    ASCII_LOGO = r"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ██████╗ ██████╗        ██████╗██╗  ██╗ █████╗ ███╗  ██╗  ║
║    ██╔════╝██╔═══██╗      ██╔════╝██║  ██║██╔══██╗████╗ ██║  ║
║    ██║     ██║   ██║█████╗██║     ███████║███████║██╔██╗██║  ║
║    ██║     ██║   ██║╚════╝██║     ██╔══██║██╔══██║██║╚████║  ║
║    ╚██████╗╚██████╔╝      ╚██████╗██║  ██║██║  ██║██║ ╚███║  ║
║     ╚═════╝ ╚═════╝        ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚══╝  ║
║                                                              ║
║           🌸  CO-CHAN  DOWNLOADER  🌸                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝"""

    @staticmethod
    def enable_ansi():
        if os.name == 'nt':
            try:
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                pass

    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')

    MAX_VISIBLE = 8

    @staticmethod
    def display_len(s):
        count = 0
        i = 0
        while i < len(s):
            cp = ord(s[i])
            # Saut des modificateurs qui ne prennent pas de place visuelle
            if cp in (0xFE0E, 0xFE0F, 0x200D, 0x20E3):
                i += 1
                continue
            if 0x0300 <= cp <= 0x036F:  # diacritiques combinants
                i += 1
                continue
            if 0x1F3FB <= cp <= 0x1F3FF:  # modificateurs de teinte de peau
                i += 1
                continue
            is_emoji = (0x1F000 <= cp <= 0x1FFFF or 0x2600 <= cp <= 0x27BF
                        or 0x2B00 <= cp <= 0x2BFF)
            is_cjk   = (0xFE30 <= cp <= 0xFE4F or 0x2E80 <= cp <= 0x2EFF
                        or 0x3000 <= cp <= 0x9FFF or 0xF900 <= cp <= 0xFAFF)
            is_hangul = 0xAC00 <= cp <= 0xD7AF
            if is_emoji or is_cjk or is_hangul:
                count += 2
                # Consommer les caractères suivants liés par ZWJ (émoji composé)
                # Ex: 👨‍👩‍👧 = 3 emojis + 2 ZWJ → compte comme 2, pas 6
                j = i + 1
                while j < len(s):
                    ncp = ord(s[j])
                    if ncp == 0x200D:  # ZWJ : lier au prochain emoji
                        j += 1
                        continue
                    if ncp in (0xFE0E, 0xFE0F, 0x20E3):  # variation/keycap
                        j += 1
                        continue
                    if 0x1F3FB <= ncp <= 0x1F3FF:  # teinte de peau
                        j += 1
                        continue
                    if (0x1F000 <= ncp <= 0x1FFFF or 0x2600 <= ncp <= 0x27BF
                            or 0x2B00 <= ncp <= 0x2BFF):
                        # Emoji suivant dans la séquence ZWJ : skip sans compter
                        j += 1
                        continue
                    break
                i = j
            else:
                count += 1
                i += 1
        return count

    @staticmethod
    def print_logo():
        print(ConsoleUI.CYAN + ConsoleUI.ASCII_LOGO + ConsoleUI.RESET)

    @staticmethod
    def show_menu(options, title="MENU", selected_index=0, subtitle=""):
        box_w = 62
        ConsoleUI.clear()
        ConsoleUI.print_logo()

        if subtitle:
            print(f"\n  {ConsoleUI.DIM}{subtitle}{ConsoleUI.RESET}")
        else:
            print()

        visible = min(len(options), ConsoleUI.MAX_VISIBLE)
        half    = visible // 2
        top     = selected_index - half
        top     = max(0, min(top, len(options) - visible))

        h_line      = "═" * box_w
        title_vlen  = ConsoleUI.display_len(title)
        title_pad_l = max(0, (box_w - title_vlen) // 2)
        title_pad_r = max(0, box_w - title_vlen - title_pad_l)
        print(f"  ╔{h_line}╗")
        print(f"  ║{' ' * title_pad_l}{ConsoleUI.BOLD}{ConsoleUI.CYAN}{title}{ConsoleUI.RESET}{' ' * title_pad_r}║")
        print(f"  ╠{h_line}╣")

        if top > 0:
            arrow_up = f"▲  {top} élément(s) plus haut"
            pad_r = " " * max(0, box_w - 2 - ConsoleUI.display_len(arrow_up))
            print(f"  ║  {ConsoleUI.CYAN}{arrow_up}{ConsoleUI.RESET}{pad_r}║")
        else:
            print(f"  ║{' ' * box_w}║")

        inner    = box_w - 4
        max_text = inner - 3

        for i in range(top, top + visible):
            raw = options[i]
            if ConsoleUI.display_len(raw) > max_text:
                accum, width = [], 0
                for ch in raw:
                    cw = 2 if ConsoleUI.display_len(ch) == 2 else 1
                    if width + cw > max_text - 1:
                        break
                    accum.append(ch)
                    width += cw
                raw = "".join(accum) + "…"

            prefix       = "▶  " if i == selected_index else "   "
            visible_text = prefix + raw
            pad_r        = " " * max(0, inner - ConsoleUI.display_len(visible_text))

            if i == selected_index:
                print(f"  ║  {ConsoleUI.CYAN}{ConsoleUI.BOLD}{visible_text}{ConsoleUI.RESET}{pad_r}  ║")
            else:
                print(f"  ║  {visible_text}{pad_r}  ║")

        remaining = len(options) - top - visible
        if remaining > 0:
            arrow_dn = f"▼  {remaining} élément(s) plus bas"
            pad_r = " " * max(0, box_w - 2 - ConsoleUI.display_len(arrow_dn))
            print(f"  ║  {ConsoleUI.CYAN}{arrow_dn}{ConsoleUI.RESET}{pad_r}║")
        else:
            print(f"  ║{' ' * box_w}║")

        print(f"  ╠{h_line}╣")
        nav     = "↑ ↓  Naviguer   ↵  Valider   Échap  Retour"
        nav_pad = " " * max(0, box_w - 2 - ConsoleUI.display_len(nav))
        print(f"  ║  {ConsoleUI.YELLOW}{nav}{ConsoleUI.RESET}{nav_pad}║")
        print(f"  ╚{h_line}╝")

    @staticmethod
    def get_key():
        if os.name == 'nt' and msvcrt:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\xe0':
                    key = msvcrt.getch()
                    if key == b'H':
                        return 'UP'
                    if key == b'P':
                        return 'DOWN'
                elif key == b'\r':
                    return 'ENTER'
                elif key == b'\x1b':
                    return 'ESC'
        elif tty and termios and _select:
            fd = sys.stdin.fileno()
            try:
                old_attr = termios.tcgetattr(fd)
            except Exception:
                return None
            try:
                tty.setraw(fd)
                if _select.select([sys.stdin], [], [], 0.05)[0]:
                    ch = sys.stdin.read(1)
                    if ch == '\x1b':
                        if _select.select([sys.stdin], [], [], 0.05)[0]:
                            more = sys.stdin.read(2)
                            if more == '[A':
                                return 'UP'
                            if more == '[B':
                                return 'DOWN'
                        return 'ESC'
                    if ch in ('\r', '\n'):
                        return 'ENTER'
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)
        return None

    @staticmethod
    def flush_keys():
        if os.name == 'nt' and msvcrt:
            while msvcrt.kbhit():
                msvcrt.getch()
        elif termios:
            try:
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
            except Exception:
                pass

    @staticmethod
    def navigate(options, title="MENU", subtitle=""):
        if not options:
            return -1
        selected = 0
        while True:
            ConsoleUI.show_menu(options, title, selected, subtitle)
            while True:
                key = ConsoleUI.get_key()
                if key:
                    break
                time.sleep(0.03)
            if key == 'UP':
                selected = (selected - 1) % len(options)
            elif key == 'DOWN':
                selected = (selected + 1) % len(options)
            elif key == 'ENTER':
                return selected
            elif key == 'ESC':
                return -1

    @staticmethod
    def input_screen(title, prompt_text, subtitle=""):
        ConsoleUI.clear()
        ConsoleUI.print_logo()
        print(f"\n  {ConsoleUI.CYAN}{ConsoleUI.BOLD}{'─'*58}{ConsoleUI.RESET}")
        print(f"  {ConsoleUI.BOLD}{title}{ConsoleUI.RESET}")
        if subtitle:
            print(f"  {ConsoleUI.DIM}{subtitle}{ConsoleUI.RESET}")
        print(f"  {ConsoleUI.CYAN}{'─'*58}{ConsoleUI.RESET}\n")
        try:
            return input(f"  {ConsoleUI.YELLOW}▶  {ConsoleUI.RESET}{prompt_text} : ").strip()
        except (EOFError, OSError):
            return ""

    @staticmethod
    def result_screen(lines, pause=True):
        ConsoleUI.clear()
        print(ConsoleUI.CYAN + "\n  " + "═"*58 + ConsoleUI.RESET)
        for line in lines:
            print(line)
        print(ConsoleUI.CYAN + "\n  " + "═"*58 + ConsoleUI.RESET)
        if pause:
            try:
                input(f"\n  {ConsoleUI.DIM}Appuyez sur Entrée pour continuer...{ConsoleUI.RESET}")
            except (EOFError, OSError):
                pass

    @staticmethod
    def info(m):
        print(f"  {ConsoleUI.CYAN}ℹ  {ConsoleUI.RESET}{m}")

    @staticmethod
    def success(m):
        print(f"  {ConsoleUI.GREEN}✔  {ConsoleUI.RESET}{m}")

    @staticmethod
    def warn(m):
        print(f"  {ConsoleUI.YELLOW}⚠  {ConsoleUI.RESET}{m}")

    @staticmethod
    def error(m):
        print(f"  {ConsoleUI.RED}✖  {ConsoleUI.RESET}{m}")

    @staticmethod
    def sep():
        print(f"\n  {ConsoleUI.DIM}{'─'*54}{ConsoleUI.RESET}\n")


# ══════════════════════════════════════════════════════════════════════════════
#  INTERFACE ANDROID — SimpleUI (print/input classiques, style old.py)
# ══════════════════════════════════════════════════════════════════════════════
class SimpleUI:
    """Interface texte simple pour Android/Termux."""

    @staticmethod
    def clear():
        os.system('clear')

    @staticmethod
    def print_logo():
        print("🌸  CO-CHAN  DOWNLOADER  🌸")
        print("=" * 40)

    @staticmethod
    def navigate(options, title="MENU", subtitle=""):
        """Affiche un menu numéroté et retourne l'index choisi (0-based), -1 = retour."""
        while True:
            SimpleUI.clear()
            SimpleUI.print_logo()
            print(f"\n  {title}")
            if subtitle:
                print(f"  {subtitle}")
            print()
            for i, opt in enumerate(options, 1):
                print(f"  [{i}]  {opt}")
            print("  [0]  Retour")
            print()
            try:
                raw = input("  Choix : ").strip()
            except (EOFError, OSError):
                return -1
            if raw in ("0", ""):
                return -1
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(options):
                    return idx
            print("Choix invalide.")
            time.sleep(0.6)

    @staticmethod
    def input_screen(title, prompt_text, subtitle=""):
        SimpleUI.clear()
        SimpleUI.print_logo()
        print(f"\n  {title}")
        if subtitle:
            print(f"  {subtitle}")
        print()
        try:
            return input(f"  {prompt_text} : ").strip()
        except (EOFError, OSError):
            return ""

    @staticmethod
    def result_screen(lines, pause=True):
        SimpleUI.clear()
        print("=" * 40)
        for line in lines:
            print(line)
        print("=" * 40)
        if pause:
            try:
                input("\n  Appuyez sur Entrée pour continuer...")
            except (EOFError, OSError):
                pass

    @staticmethod
    def info(m):
        print(f"ℹ️  {m}")

    @staticmethod
    def success(m):
        print(f"✅ {m}")

    @staticmethod
    def warn(m):
        print(f"⚠️  {m}")

    @staticmethod
    def error(m):
        print(f"❌ {m}")

    @staticmethod
    def sep():
        print("─" * 40)


# ── Façade UI : sélectionne automatiquement la bonne interface ────────────────
UI = SimpleUI if IS_ANDROID else ConsoleUI


# ── Dépendances optionnelles ──────────────────────────────────────────────────
pil_available = importlib.util.find_spec("PIL") is not None
Image = None  # will be replaced by actual class if PIL is available
if pil_available:
    from PIL import Image  # noqa: F811


# ── Loggers yt-dlp ────────────────────────────────────────────────────────────
class _SilentLogger:
    """Absorbe tous les messages de yt-dlp (PC)."""
    def debug(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        pass


class _AndroidLogger:
    """Affiche les erreurs yt-dlp sur Android."""
    def debug(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        print(msg)


# ── Utilitaires plateforme ────────────────────────────────────────────────────
def is_ios_device():
    s = platform.system()
    if s == "Darwin":
        if os.path.exists("/var/mobile") or "iPad" in platform.machine() or "iPhone" in platform.machine():
            return True
        if os.environ.get("HOME", "").startswith("/var/mobile"):
            return True
    return False


def set_title(title_text):
    s = platform.system()
    is_termux = s == "Linux" and "ANDROID_STORAGE" in os.environ
    is_ios = is_ios_device()
    if s == "Windows":
        os.system(f"title {title_text}")
    elif s == "Linux" and not is_termux:
        os.system(f'echo -e "\\033]0;{title_text}\\007"')
    elif s == "Darwin" and not is_ios:
        os.system(f'echo -e "\\033]0;{title_text}\\007"')


set_title("Co-Chan")


# ── Domaine actif ─────────────────────────────────────────────────────────────
def verify_domain_redirect(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.head(url, timeout=10, headers=headers, allow_redirects=True)
        final_url = response.url
        if "anime-sama" in final_url and "anime-sama.pw" not in final_url:
            return True, final_url
        return False, final_url
    except Exception:
        return False, None


def get_active_domain():
    try:
        UI.info("Recherche du serveur actif...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get("https://anime-sama.pw/", timeout=10, headers=headers)

        if response.status_code == 200:
            pattern = r'<a\s+class="btn-primary"\s+href="(https?://anime-sama\.[a-z]+)"'
            match = re.search(pattern, response.text)

            if match:
                base_domain = match.group(1)
                is_valid, redirected_url = verify_domain_redirect(base_domain)
                if is_valid:
                    redirected_domain = redirected_url.split("/catalogue")[0] if "/catalogue" in redirected_url else redirected_url.rstrip("/")
                    UI.success("Serveur actif trouvé.")
                    return f"{redirected_domain}/catalogue/"

            pattern_fallback = r'href="(https?://anime-sama\.(?!pw)[a-z]+)"'
            match_fallback = re.search(pattern_fallback, response.text)
            if match_fallback:
                base_domain = match_fallback.group(1)
                is_valid, redirected_url = verify_domain_redirect(base_domain)
                if is_valid:
                    redirected_domain = redirected_url.split("/catalogue")[0] if "/catalogue" in redirected_url else redirected_url.rstrip("/")
                    UI.success(f"Serveur actif trouvé : {redirected_domain}")
                    return f"{redirected_domain}/catalogue/"

        UI.error("Impossible de trouver le serveur actif.")
        UI.warn("Fermeture automatique dans 10 secondes...")
        time.sleep(10)
        sys.exit(1)

    except Exception as e:
        UI.error(f"Erreur lors de la récupération du serveur : {e}")
        UI.warn("Fermeture automatique dans 10 secondes...")
        time.sleep(10)
        sys.exit(1)


def check_domain_availability():
    return get_active_domain()


# ── Espace disque ─────────────────────────────────────────────────────────────
def check_disk_space(min_gb=1):
    s = platform.system()
    if s == "Windows":
        _, _, free_c = shutil.disk_usage("C:\\")
        if free_c / (1024**2) < 100:
            print(f"⚠️ Espace insuffisant sur C: ({free_c / (1024**2):.0f} Mo disponibles)")
            return False
        current_drive = os.path.splitdrive(os.getcwd())[0] + "\\"
        _, _, free = shutil.disk_usage(current_drive)
        free_space_gb = free / (1024**3)
    elif s == "Linux" and "ANDROID_STORAGE" in os.environ:
        try:
            output = os.popen("df -h /storage/emulated/0").read()
            lines = output.split("\n")
            if len(lines) > 1:
                free_space = lines[1].split()[3]
                if "G" in free_space:
                    free_space_gb = float(free_space.replace("G", ""))
                elif "M" in free_space:
                    free_space_gb = float(free_space.replace("M", "")) / 1024
                else:
                    free_space_gb = 0
            else:
                free_space_gb = 0
        except Exception:
            free_space_gb = 0
    elif s == "Darwin" and is_ios_device():
        try:
            home_path = os.path.expanduser("~")
            if os.path.exists(home_path):
                _, _, free = shutil.disk_usage(home_path)
                free_space_gb = free / (1024**3)
            else:
                free_space_gb = 0
        except Exception:
            free_space_gb = 0
    else:
        statvfs = os.statvfs("/")
        free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)

    return free_space_gb >= min_gb


# ── Progression ───────────────────────────────────────────────────────────────
def progress_hook(d, season, episode, max_episode):
    if d["status"] == "downloading":
        percent = d["_percent_str"].strip()
        sys.stdout.write(f"\r🔄 [S{season} E{episode}/{max_episode}] {percent} complet")
        sys.stdout.flush()
    elif d["status"] == "finished":
        sys.stdout.write(f"\r✅ [S{season} E{episode}/{max_episode}] Téléchargement terminé !\n")
        sys.stdout.flush()


# ── Chemin de téléchargement ──────────────────────────────────────────────────
def get_download_path():
    s = platform.system()
    if s == "Windows":
        return os.getcwd()
    if s == "Linux" and "ANDROID_STORAGE" in os.environ:
        return "/storage/emulated/0/Download/anime"
    if s == "Darwin" and is_ios_device():
        for path in [
            os.path.expanduser("~/Documents/anime"),
            os.path.expanduser("~/Downloads/anime"),
            os.path.join(os.getcwd(), "anime"),
        ]:
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


# ── Formatage ─────────────────────────────────────────────────────────────────
def format_url_name(name):
    return name.lower().replace("'", "").replace(" ", "-")


def format_folder_name(name, language):
    return f"{' '.join(word.capitalize() for word in name.split())} {language.upper()}"


def normalize_anime_name(name):
    return ' '.join(name.strip().split()).lower()


# ── Existence / langues / saisons ─────────────────────────────────────────────
def check_anime_exists(base_url, formatted_url_name):
    test_languages = ["vf", "vostfr", "va", "vkr", "vcn", "vqc"]
    for lang in test_languages:
        for kind in ["saison1", "film", "oav"]:
            url = f"{base_url}{formatted_url_name}/{kind}/{lang}/episodes.js"
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200 and r.text.strip():
                    return True
            except Exception:
                continue
    return False


def check_available_languages(base_url, name):
    all_languages = ["vf", "va", "vkr", "vcn", "vqc", "vf1", "vf2", "vf3", "vf4", "vf5"]
    available = []
    for lang in all_languages:
        for kind in ["saison1", "film"]:
            try:
                r = requests.get(f"{base_url}{name}/{kind}/{lang}/episodes.js", timeout=5)
                if r.status_code == 200 and r.text.strip():
                    available.append(lang)
                    break
            except Exception:
                continue
    return available


def check_seasons(base_url, name, language):
    season_info = {}
    season = 1
    consecutive_not_found = 0

    while consecutive_not_found < 3:
        normal_url = f"{base_url}{name}/saison{season}/{language}/episodes.js"
        try:
            normal_resp = requests.get(normal_url, timeout=10)
            has_normal = normal_resp.status_code == 200 and normal_resp.text.strip()
        except Exception:
            has_normal = False

        hs_url = f"{base_url}{name}/saison{season}hs/{language}/episodes.js"
        try:
            hs_resp = requests.get(hs_url, timeout=10)
            has_hs = hs_resp.status_code == 200 and hs_resp.text.strip()
        except Exception:
            has_hs = False

        if has_normal or has_hs:
            consecutive_not_found = 0

            if has_normal and has_hs:
                UI.info(f"Saison {season} (Normal + HS) trouvée → choix requis")
                season_info[f"{season}"] = {"type": "both", "normal": normal_url, "hs": hs_url, "variants": []}
            elif has_normal:
                UI.success(f"Saison {season} trouvée.")
                season_info[f"{season}"] = {"type": "normal", "url": normal_url, "variants": []}
            else:
                UI.success(f"Saison {season} HS trouvée.")
                season_info[f"{season}hs"] = {"type": "hs", "url": hs_url, "variants": []}

            for base_key, base_url_var in [
                (f"{season}",   normal_url if has_normal else None),
                (f"{season}hs", hs_url     if has_hs     else None),
            ]:
                if base_url_var is None:
                    continue
                i = 1
                variant_not_found = 0
                while variant_not_found < 3:
                    variant_suffix = 'hs' if 'hs' in base_key else ''
                    variant_url = f"{base_url}{name}/saison{season}{variant_suffix}-{i}/{language}/episodes.js"
                    try:
                        r = requests.get(variant_url, timeout=10)
                        if r.status_code == 200 and r.text.strip():
                            season_info[base_key]["variants"].append((i, variant_url))
                            UI.info(f"   → Variante {season}{variant_suffix}-{i} trouvée")
                            variant_not_found = 0
                        else:
                            variant_not_found += 1
                    except Exception:
                        variant_not_found += 1
                    i += 1
        else:
            consecutive_not_found += 1

        season += 1

    for special, label in [("film", "Film"), ("oav", "OAV")]:
        url = f"{base_url}{name}/{special}/{language}/episodes.js"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200 and r.text.strip():
                UI.success(f"{label} trouvé.")
                season_info[special] = {"type": special, "url": url, "variants": []}
        except Exception:
            continue

    return season_info


# ── Tri des saisons ───────────────────────────────────────────────────────────
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


# ── resolve_season_choices : PC vs Android ────────────────────────────────────
def resolve_season_choices(season_info):
    final_seasons = []
    for key, info in sorted(season_info.items(), key=lambda x: custom_sort_key(x[0])):
        if info["type"] == "both":
            if IS_ANDROID:
                print(f"\nPour la Saison {key}:")
                print("1. Version Normale")
                print("2. Version HS")
                choix = ""
                while choix not in ["1", "2"]:
                    choix = input("Choisissez 1 ou 2 : ").strip()
                if choix == "1":
                    chosen_url = info["normal"]
                    display = key
                else:
                    chosen_url = info["hs"]
                    display = f"{key}hs"
                print(f"→ {display.upper()} sélectionnée\n")
            else:
                idx = ConsoleUI.navigate(
                    ["🎬  Version Normale", "⭐  Version HS (Hors-Série)"],
                    f"SAISON {key} — CHOISIR",
                )
                if idx == -1:
                    chosen_url = info["normal"]
                    display = key
                elif idx == 0:
                    chosen_url = info["normal"]
                    display = key
                else:
                    chosen_url = info["hs"]
                    display = f"{key}hs"
                ConsoleUI.success(f"{display.upper()} sélectionnée\n")

            urls = [chosen_url] + [v[1] for v in sorted(info.get("variants", []))]
            final_seasons.append((display, urls))

        elif info["type"] in ["normal", "hs"]:
            urls = [info["url"]] + [v[1] for v in sorted(info.get("variants", []))]
            final_seasons.append((key, urls))

        elif info["type"] in ["film", "oav"]:
            final_seasons.append((key, [info["url"]]))

    return final_seasons


# ── Détection reprise ─────────────────────────────────────────────────────────
def find_last_downloaded_episode(folder_path):
    if not os.path.exists(folder_path):
        return None, None
    pattern = re.compile(r's(\w+)_e(\d+)\.mp4')
    episodes = []
    for f in os.listdir(folder_path):
        m = pattern.match(f)
        if m:
            episodes.append((m.group(1), int(m.group(2))))
    if not episodes:
        return None, None

    def sort_key(x):
        s, e = x
        n = s.replace('hs', '')
        is_hs = 'hs' in s
        if n.isdigit():
            return (0, int(n), int(is_hs), e)
        if s == "film":
            return (1, 0, 0, e)
        if s == "oav":
            return (2, 0, 0, e)
        return (3, 0, int(is_hs), e)

    episodes.sort(key=sort_key, reverse=True)
    return episodes[0]


def count_downloaded_episodes_for_season(folder_path, target_season):
    if not os.path.exists(folder_path):
        return 0
    pattern = re.compile(r's(\w+)_e(\d+)\.mp4')
    return sum(1 for f in os.listdir(folder_path)
               if (m := pattern.match(f)) and m.group(1) == target_season)


def get_actual_total_episodes_for_season(url_list):
    count = 0
    for url in url_list:
        eps_arrays = extract_video_links(url)
        if eps_arrays:
            count += len(eps_arrays[0])
    return count


# ── ask_for_starting_point : PC vs Android ────────────────────────────────────
def ask_for_starting_point(folder_name, seasons):
    """
    Retourne (start_season, start_episode, only_season, only_episode).
    Android : interface old.py (input/print), retourne only_season/only_episode=False.
    PC      : interface ConsoleUI avec menus interactifs et options avancées.
    """
    download_dir = os.path.join(get_download_path(), folder_name)
    last_season, last_episode = find_last_downloaded_episode(download_dir)

    # ── ANDROID ───────────────────────────────────────────────────────────────
    if IS_ANDROID:
        if last_season is not None and last_episode is not None:
            print(f"📁 Dernier épisode détecté : S{last_season} E{last_episode}")
            downloaded_count = count_downloaded_episodes_for_season(download_dir, last_season)
            season_urls = [url_list for display, url_list in seasons if display == last_season]
            total_in_season = get_actual_total_episodes_for_season(season_urls[0]) if season_urls else 0
            print(f"📊 Épisodes téléchargés pour S{last_season}: {downloaded_count}/{total_in_season}")

            if 0 < total_in_season <= downloaded_count:
                print(f"✅ Tous les épisodes de la saison {last_season} sont déjà téléchargés")
                season_keys = [display for display, _ in seasons]
                if last_season in season_keys:
                    idx_cur = season_keys.index(last_season)
                    if idx_cur + 1 < len(season_keys):
                        next_season = season_keys[idx_cur + 1]
                        choice = input(f"Passer à la saison suivante S{next_season} E1 ? (o/n): ").strip().lower()
                        if choice in ["o", "oui", "y", "yes", ""]:
                            return next_season, 1, False, False
                    else:
                        print("🎉 Tous les épisodes disponibles ont été téléchargés !")
                        choice = input("Recommencer depuis le début ? (o/n): ").strip().lower()
                        if choice in ["o", "oui", "y", "yes", ""]:
                            return 0, 0, False, False
                        sys.exit(0)
            else:
                choice = input(
                    f"Reprendre depuis S{last_season} E{last_episode} ? (o/n): "
                ).strip().lower()
                if choice in ["o", "oui", "y", "yes", ""]:
                    print(f"➡️ Reprise à partir de S{last_season} E{last_episode}")
                    return last_season, last_episode, False, False

        choice = input("Télécharger tous les épisodes ? (o/n): ").strip().lower()
        if choice in ["o", "oui", "y", "yes", ""]:
            print("➡️ Téléchargement de tous les épisodes")
            return 0, 0, False, False

        while True:
            try:
                season_input = input(
                    "Numéro de saison (ou 'film'/'oav', ajoutez 'hs' si HS): "
                ).strip().lower()
                season = season_input
                episode = int(input("Numéro d'épisode: ").strip())
                print(f"➡️ Téléchargement à partir de S{season} E{episode}")
                return season, episode, False, False
            except ValueError:
                print("⚠️ Veuillez entrer des nombres valides")

    # ── PC ────────────────────────────────────────────────────────────────────
    else:
        if last_season is not None and last_episode is not None:
            ConsoleUI.info(f"Dernier épisode détecté : S{last_season} E{last_episode}")
            downloaded_count = count_downloaded_episodes_for_season(download_dir, last_season)
            season_urls = [url_list for display, url_list in seasons if display == last_season]
            total_in_season = get_actual_total_episodes_for_season(season_urls[0]) if season_urls else 0
            ConsoleUI.info(f"Épisodes téléchargés pour S{last_season} : {downloaded_count}/{total_in_season}")

            if 0 < total_in_season <= downloaded_count:
                ConsoleUI.success(f"Tous les épisodes de la saison {last_season} sont déjà téléchargés !")
                season_keys = [d for d, _ in seasons]
                if last_season in season_keys:
                    idx_cur = season_keys.index(last_season)
                    if idx_cur + 1 < len(season_keys):
                        next_season = season_keys[idx_cur + 1]
                        idx = ConsoleUI.navigate(
                            [f"▶  Passer à la saison suivante S{next_season} E1",
                             "⏮  Rester sur la saison actuelle"],
                            "SAISON COMPLÈTE"
                        )
                        if idx == 0:
                            return next_season, 1, False, False
                        # idx == 1 ou ESC (-1) → rester, on continue vers le menu principal
                    else:
                        ConsoleUI.success("🎉 Tous les épisodes disponibles ont été téléchargés !")
                        idx = ConsoleUI.navigate(
                            ["🔄  Recommencer depuis le début", "❌  Quitter"],
                            "TÉLÉCHARGEMENT TERMINÉ"
                        )
                        if idx == 0:
                            return 0, 0, False, False
                        sys.exit(0)
            else:
                idx = ConsoleUI.navigate(
                    [f"▶  Reprendre depuis S{last_season} E{last_episode}",
                     "⏭  Télécharger tous les épisodes depuis le début"],
                    "REPRENDRE LE TÉLÉCHARGEMENT"
                )
                if idx == 0:
                    ConsoleUI.info(f"Reprise à partir de S{last_season} E{last_episode}")
                    return last_season, last_episode, False, False

        idx = ConsoleUI.navigate(
            ["📥  Télécharger tous les épisodes",
             "📺  Télécharger une saison complète",
             "🎯  Choisir un point de départ précis",
             "🎬  Télécharger un seul épisode"],
            "POINT DE DÉPART"
        )

        if idx == -1:
            return None, None, None, None

        if idx == 0:
            ConsoleUI.info("Téléchargement de tous les épisodes")
            return 0, 0, False, False

        if idx == 1:
            s_idx = ConsoleUI.navigate([f"📺  Saison {s}" for s, _ in seasons], "CHOISIR LA SAISON")
            if s_idx == -1:
                return 0, 0, False, False
            chosen_season = seasons[s_idx][0]
            ConsoleUI.info(f"Téléchargement de la saison {chosen_season} complète")
            return chosen_season, 1, True, False

        if idx == 2:
            s_idx = ConsoleUI.navigate([f"📺  Saison {s}" for s, _ in seasons], "CHOISIR LA SAISON DE DÉPART")
            if s_idx == -1:
                return 0, 0, False, False
            chosen_season = seasons[s_idx][0]
            while True:
                try:
                    ep_raw = ConsoleUI.input_screen(f"ÉPISODE DE DÉPART — Saison {chosen_season}", "Numéro d'épisode")
                    episode = int(ep_raw)
                    ConsoleUI.info(f"Téléchargement à partir de S{chosen_season} E{episode}")
                    return chosen_season, episode, False, False
                except ValueError:
                    ConsoleUI.warn("Veuillez entrer un numéro d'épisode valide.")

        if idx == 3:
            s_idx = ConsoleUI.navigate([f"📺  Saison {s}" for s, _ in seasons], "CHOISIR LA SAISON")
            if s_idx == -1:
                return 0, 0, False, False
            chosen_season = seasons[s_idx][0]
            while True:
                try:
                    ep_raw = ConsoleUI.input_screen(
                        f"ÉPISODE UNIQUE — Saison {chosen_season}",
                        "Numéro d'épisode",
                        "Un seul épisode sera téléchargé"
                    )
                    episode = int(ep_raw)
                    ConsoleUI.info(f"Téléchargement de S{chosen_season} E{episode} uniquement")
                    return chosen_season, episode, False, True
                except ValueError:
                    ConsoleUI.warn("Veuillez entrer un numéro d'épisode valide.")

        return 0, 0, False, False


# ── Sibnet 403 ────────────────────────────────────────────────────────────────
def check_http_403(url):
    for attempt in range(5):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 403:
                print(
                    f"⛔ Tentative {attempt+1} échouée : Sibnet a renvoyé un code 403. "
                    "Nouvelle tentative, veuillez patienter."
                )
                time.sleep(10)
            else:
                return False
        except requests.exceptions.RequestException as e:
            print(f"⛔ Erreur réseau tentative {attempt+1} : {e}. Nouvelle tentative...")
            time.sleep(5)
    print("⛔ Sibnet vous a temporairement banni, veuillez réessayer dans un maximum de 2 jours.")
    time.sleep(20)
    return True


# ── Image de couverture ───────────────────────────────────────────────────────
def get_anime_image(anime_name, folder_name, formatted_url_name):
    try:
        image_data = None
        github_url = f"https://raw.githubusercontent.com/Anime-Sama/IMG/img/contenu/{formatted_url_name}.jpg"
        github_response = requests.get(github_url, timeout=10)
        if github_response.status_code == 200:
            image_data = github_response.content
        else:
            url_name = anime_name.replace(" ", "+")
            jikan_url = f"https://api.jikan.moe/v4/anime?q={url_name}&limit=1"
            jikan_response = requests.get(jikan_url, timeout=10)
            jikan_response.raise_for_status()
            data = jikan_response.json()
            if not data["data"]:
                return
            image_url = data["data"][0]["images"]["jpg"]["large_image_url"]
            image_response = requests.get(image_url, timeout=10)
            image_response.raise_for_status()
            image_data = image_response.content

        if not image_data:
            return

        jpg_path = os.path.join(folder_name, "cover.jpg")
        with open(jpg_path, 'wb') as f:
            f.write(image_data)

        if pil_available and platform.system() == "Windows":
            ico_path = os.path.join(folder_name, "folder.ico")
            image = Image.open(io.BytesIO(image_data))
            size = 256
            square_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            width, height = image.size
            if width > height:
                new_height = int(height * size / width)
                resized_img = image.resize((size, new_height))
                square_img.paste(resized_img, (0, (size - new_height) // 2))
            else:
                new_width = int(width * size / height)
                resized_img = image.resize((new_width, size))
                square_img.paste(resized_img, ((size - new_width) // 2, 0))
            square_img.save(ico_path, format='ICO', sizes=[(size, size)])
            if os.name == 'nt':
                os.system(f'attrib +h "{ico_path}"')
            absolute_ico_path = os.path.abspath(ico_path)
            desktop_ini_path = os.path.join(folder_name, "desktop.ini")
            with open(desktop_ini_path, "w", encoding="utf-8") as ini_file:
                ini_file.write(f"""[.ShellClassInfo]
IconResource={absolute_ico_path},0
[ViewState]
Mode=
Vid=
FolderType=Generic
""")
            if os.name == 'nt':
                os.system(f'attrib +s "{folder_name}"')
                os.system(f'attrib +h +s "{desktop_ini_path}"')
    except Exception:
        pass


# ── Extraction m3u8 Vidmoly ───────────────────────────────────────────────────
def get_vidmoly_m3u8(video_id):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Sec-Fetch-Dest": "iframe",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Referer": "https://vidmoly.biz/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Connection": "keep-alive",
        "Accept-Encoding": "identity",
    }
    for attempt in range(5):
        try:
            url  = f"https://vidmoly.biz/embed-{video_id}.html"
            resp = session.get(url, headers=headers, timeout=15)
            text = resp.content.decode("utf-8", errors="ignore")
            m3u8 = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', text)
            if m3u8:
                return m3u8.group(0)
        except Exception:
            pass
        if attempt < 4:
            time.sleep(1)
    return None


# ── Classification des liens ──────────────────────────────────────────────────
def classify_link(url):
    if "sibnet" in url:
        return ("sibnet", url)
    if "vidmoly" in url:
        m = re.search(r"embed-([\w]+)\.html", url)
        if m:
            return ("vidmoly", m.group(1))
    if "sendvid" in url:
        return ("sendvid", url)
    return None


# ── Parsing des eps arrays ────────────────────────────────────────────────────
def parse_eps_arrays(js_text):
    eps_blocks = re.findall(r"var\s+eps\d+\s*=\s*\[(.*?)\]\s*;", js_text, re.DOTALL)
    results = []
    for block in eps_blocks:
        all_urls = re.findall(r"'(https?://[^']+)'", block)
        if not all_urls:
            continue
        compatible = [c for url in all_urls if (c := classify_link(url))]
        results.append({
            "total":      len(all_urls),
            "compatible": len(compatible),
            "links":      compatible,
        })
    results.sort(key=lambda x: (x["compatible"], x["total"]), reverse=True)
    if len(results) > 1:
        best = results[0]
        tied = [r for r in results if r["compatible"] == best["compatible"] and r["total"] == best["total"]]
        if len(tied) > 1:
            results[0] = random.choice(tied)
    return results


def extract_video_links(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []
    except Exception:
        return []
    eps_list = parse_eps_arrays(response.text)
    if not eps_list:
        return []
    return [eps["links"] for eps in eps_list]


# ── Téléchargement ────────────────────────────────────────────────────────────
def download_video(link_type, link_value, filename, season, episode, max_episode):
    if not check_disk_space():
        print(f"⛔ Espace disque insuffisant. Arrêt pour [S{season} E{episode}/{max_episode}].")
        return False

    if link_type == "vidmoly":
        final_url = get_vidmoly_m3u8(link_value)
        if not final_url:
            return False
        video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
    else:
        final_url    = link_value
        video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"

    anime_folder_name = os.path.basename(os.path.dirname(filename))
    is_termux = platform.system() == "Linux" and "ANDROID_STORAGE" in os.environ
    if is_termux:
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "temp", anime_folder_name)
    else:
        temp_dir = os.path.join(tempfile.gettempdir(), "anime-dl", anime_folder_name)
    os.makedirs(temp_dir, exist_ok=True)

    logger = _AndroidLogger() if IS_ANDROID else _SilentLogger()

    ydl_opts = {
        "outtmpl":             filename,
        "quiet":               True,
        "ignoreerrors":        False,
        "no_warnings":         True,
        "noprogress":          False,
        "progress_hooks":      [lambda d: progress_hook(d, season, episode, max_episode)],
        "format":              video_format,
        "merge_output_format": "mp4",
        "logger":              logger,
        "socket_timeout":      60,
        "retries":             3,
        "paths":               {"temp": temp_dir},
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ret = ydl.download([final_url])
        if ret != 0:
            return False
        mp4 = filename if filename.endswith(".mp4") else filename + ".mp4"
        if not os.path.isfile(mp4) or os.path.getsize(mp4) == 0:
            return False
        return True
    except Exception:
        sys.stdout.write("\r")
        sys.stdout.flush()
        return False


# ── Aide CLI ──────────────────────────────────────────────────────────────────
def show_usage():
    print("Usage:")
    print("  python script.py <nom_anime> <langue>")
    print("  python script.py -h|--help|help|/?|-?")
    print()
    print("Exemples:")
    print('  python script.py "one piece" vf')
    print('  python script.py "naruto" vostfr')
    print()
    print("Plateformes supportées: Windows, macOS, Linux, Android (Termux)")
    print("Sources vidéo supportées: Sibnet, Vidmoly, Sendvid")


# ── Point d'entrée ────────────────────────────────────────────────────────────
def main():
    # Initialisation de l'affichage selon la plateforme
    if IS_ANDROID:
        SimpleUI.clear()
        SimpleUI.print_logo()
        print("📱 Plateforme détectée : Android (Termux)")
        print("⏳ Chargement, veuillez patienter...\n")
    else:
        ConsoleUI.enable_ansi()
        ConsoleUI.clear()
        ConsoleUI.print_logo()
        if os.name == 'nt':
            platform_label = "Windows — navigation par flèches"
        else:
            platform_label = "Linux / macOS — navigation par flèches"
        print(f"  {ConsoleUI.DIM}🖥  Plateforme détectée : {platform_label}{ConsoleUI.RESET}")
        print(f"\n  {ConsoleUI.DIM}⏳ Chargement, veuillez patienter...{ConsoleUI.RESET}\n")

    base_url = check_domain_availability()

    # ── Mode arguments CLI ────────────────────────────────────────────────────
    if len(sys.argv) > 1:
        if sys.argv[1].lower() in ["-h", "--help", "help", "/?", "-?"]:
            show_usage()
            return
        if len(sys.argv) == 3:
            anime_name          = normalize_anime_name(sys.argv[1])
            language_input      = sys.argv[2].strip().lower()
            anime_name_capitalized = anime_name.title()
            set_title(f"Co-Chan : {anime_name_capitalized}")
            if language_input not in ["vf", "vostfr", "va", "vkr", "vcn", "vqc"]:
                UI.error(f"Langage '{language_input}' non reconnu.")
                show_usage()
                return
            selected_language = language_input
        else:
            UI.error("Nombre d'arguments incorrect.")
            show_usage()
            return

        formatted_url_name = format_url_name(anime_name)
        UI.info(f"Vérification de '{anime_name_capitalized}'...")
        if not check_anime_exists(base_url, formatted_url_name):
            UI.error(f"L'anime '{anime_name_capitalized}' est introuvable.")
            UI.warn("Vérifiez l'orthographe ou essayez le nom japonais.")
            time.sleep(5)
            sys.exit(1)
        UI.success(f"Anime '{anime_name_capitalized}' trouvé !")

    # ── Mode interactif ───────────────────────────────────────────────────────
    else:
        # ── ANDROID : interface old.py ─────────────────────────────────────
        if IS_ANDROID:
            anime_name_raw = input("Entrez le nom de l'anime : ").strip()
            if not anime_name_raw:
                return

            anime_name             = normalize_anime_name(anime_name_raw)
            anime_name_capitalized = anime_name.title()
            set_title(f"Co-Chan : {anime_name_capitalized}")
            formatted_url_name     = format_url_name(anime_name)

            UI.info(f"Vérification de '{anime_name_capitalized}'...")
            if not check_anime_exists(base_url, formatted_url_name):
                UI.error(f"'{anime_name_capitalized}' introuvable.")
                UI.warn("Vérifiez l'orthographe ou essayez avec le nom japonais.")
                time.sleep(5)
                sys.exit(1)
            UI.success(f"Anime '{anime_name_capitalized}' trouvé !")

            available_vf_versions = check_available_languages(base_url, formatted_url_name)
            if available_vf_versions:
                print("\nVersions disponibles :")
                for i, lang in enumerate(available_vf_versions, start=1):
                    print(f"  {i}. {lang.upper()}")
                print(f"  {len(available_vf_versions)+1}. VOSTFR")
                choice = input("Choisissez la version : ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(available_vf_versions):
                    selected_language = available_vf_versions[int(choice) - 1]
                else:
                    selected_language = "vostfr"
            else:
                UI.warn("Aucune version VF trouvée → VOSTFR sélectionné automatiquement.")
                selected_language = "vostfr"

        # ── PC : interface ConsoleUI ───────────────────────────────────────
        else:
            while True:
                choice = ConsoleUI.navigate(
                    ["🌸  Télécharger un anime", "❓  Aide / Usage", "❌  Quitter"],
                    "MENU PRINCIPAL"
                )

                if choice == 0:
                    anime_name_raw = ConsoleUI.input_screen(
                        "TÉLÉCHARGER UN ANIME", "Nom de l'anime",
                        "Entrez le nom exact ou approximatif"
                    )
                    if not anime_name_raw:
                        continue

                    anime_name             = normalize_anime_name(anime_name_raw)
                    anime_name_capitalized = anime_name.title()
                    set_title(f"Co-Chan : {anime_name_capitalized}")
                    formatted_url_name     = format_url_name(anime_name)

                    ConsoleUI.clear()
                    ConsoleUI.print_logo()
                    ConsoleUI.sep()
                    ConsoleUI.info(f"Vérification de '{anime_name_capitalized}'...")

                    if not check_anime_exists(base_url, formatted_url_name):
                        ConsoleUI.error(f"'{anime_name_capitalized}' introuvable.")
                        ConsoleUI.warn("Vérifiez l'orthographe ou essayez avec le nom japonais.")
                        ConsoleUI.sep()
                        try:
                            input(f"  {ConsoleUI.DIM}Appuyez sur Entrée pour continuer...{ConsoleUI.RESET}")
                        except (EOFError, OSError):
                            pass
                        continue

                    ConsoleUI.success(f"Anime '{anime_name_capitalized}' trouvé !")
                    ConsoleUI.sep()

                    available_vf_versions = check_available_languages(base_url, formatted_url_name)
                    if available_vf_versions:
                        lang_options = [f"🎌  {lang.upper()}" for lang in available_vf_versions] + ["📺  VOSTFR"]
                        lang_idx = ConsoleUI.navigate(lang_options, "CHOISIR LA VERSION", anime_name_capitalized)
                        if lang_idx == -1:
                            continue
                        selected_language = available_vf_versions[lang_idx] if lang_idx < len(available_vf_versions) else "vostfr"
                    else:
                        ConsoleUI.warn("Aucune version VF trouvée → VOSTFR sélectionné automatiquement.")
                        selected_language = "vostfr"
                    break

                if choice == 1:
                    ConsoleUI.clear()
                    ConsoleUI.print_logo()
                    show_usage()
                    try:
                        input(f"\n  {ConsoleUI.DIM}Appuyez sur Entrée pour revenir au menu...{ConsoleUI.RESET}")
                    except (EOFError, OSError):
                        pass
                    continue
                ConsoleUI.result_screen([
                    f"  {ConsoleUI.CYAN}👋  Merci d'avoir utilisé Co-Chan !{ConsoleUI.RESET}",
                    "  🌸  À bientôt !",
                ], pause=False)
                time.sleep(1)
                sys.exit(0)

    folder_name = format_folder_name(anime_name_capitalized, selected_language)

    if not check_disk_space():
        UI.error("Espace disque insuffisant. Libérez de l'espace et réessayez.")
        sys.exit(1)

    if not IS_ANDROID:
        ConsoleUI.clear()
        ConsoleUI.print_logo()
        ConsoleUI.sep()
    UI.info(f"Recherche des saisons pour '{anime_name_capitalized}' [{selected_language.upper()}]...")
    if not IS_ANDROID:
        ConsoleUI.sep()

    raw_season_info = check_seasons(base_url, formatted_url_name, selected_language)
    seasons         = resolve_season_choices(raw_season_info)

    if not IS_ANDROID:
        ConsoleUI.clear()
        ConsoleUI.print_logo()
        ConsoleUI.sep()

    start_season, start_episode, only_season, only_episode = ask_for_starting_point(folder_name, seasons)

    if start_season is None:
        return

    # ── Boucle de téléchargement — logique Co-chan.py (fallback multi-lecteur) ─
    for display_season, url_list in seasons:
        if only_season and start_season != 0 and display_season != start_season:
            continue
        if only_episode and display_season != start_season:
            continue

        all_eps_arrays = []
        for url in url_list:
            eps_arrays = extract_video_links(url)
            if eps_arrays:
                all_eps_arrays.extend(eps_arrays)

        if not all_eps_arrays:
            continue

        current_eps_array_index   = 0
        all_links                 = all_eps_arrays[current_eps_array_index]
        total_episodes_in_season  = max(len(arr) for arr in all_eps_arrays)

        if total_episodes_in_season == 0:
            continue

        episode_counter = 1

        if start_season != 0:
            season_keys = [s for s, _ in seasons]
            try:
                start_index   = season_keys.index(start_season)
                current_index = season_keys.index(display_season)
                if current_index < start_index:
                    print(f"⏭️ Saison {display_season.upper()} ignorée (avant S{start_season})")
                    continue
                if current_index == start_index and start_episode > 1:
                    episode_counter = start_episode
                    if only_episode:
                        print(f"🎬 Téléchargement de S{display_season} E{start_episode} uniquement")
                    else:
                        print(f"➡️ Reprise à S{display_season} E{start_episode}")
            except ValueError:
                pass

        if only_episode:
            if start_episode > total_episodes_in_season:
                UI.error(
                    f"L'épisode {start_episode} n'existe pas pour la saison {display_season} "
                    f"({total_episodes_in_season} épisodes disponibles)."
                )
                continue
            print(f"🎬 Téléchargement de la Saison {display_season.upper()} — Épisode {start_episode} uniquement")
        else:
            print(f"♾️ Téléchargement de la Saison {display_season.upper()} ({total_episodes_in_season} épisodes)")

        while episode_counter <= total_episodes_in_season:
            episode_index = episode_counter - 1
            if episode_index >= len(all_links):
                break

            # Animation de chargement sur Android uniquement (style old.py)
            if IS_ANDROID:
                sys.stdout.write("🌐 Chargement")
                sys.stdout.flush()
                for _ in range(3):
                    time.sleep(1)
                    sys.stdout.write(".")
                    sys.stdout.flush()
                sys.stdout.write("\r")
                sys.stdout.flush()

            link_type, link_value = all_links[episode_index]

            if link_type == "sibnet" and check_http_403(link_value):
                episode_counter += 1
                if only_episode:
                    break
                continue

            download_dir = os.path.join(get_download_path(), folder_name)
            os.makedirs(download_dir, exist_ok=True)

            if episode_counter == 1 and display_season == seasons[0][0]:
                get_anime_image(anime_name_capitalized, download_dir, formatted_url_name)

            filename = os.path.join(download_dir, f"s{display_season}_e{episode_counter}.mp4")
            success  = download_video(link_type, link_value, filename,
                                      display_season, episode_counter, total_episodes_in_season)

            if not success:
                # ── Fallback multi-lecteur (logique Co-chan.py) ───────────────
                fallback_success = False
                for fallback_index, fallback_links_candidate in enumerate(all_eps_arrays):
                    if fallback_index == current_eps_array_index:
                        continue
                    fallback_links = fallback_links_candidate
                    if len(fallback_links) >= episode_counter:
                        fb_type, fb_value = fallback_links[episode_counter - 1]
                        if IS_ANDROID:
                            print(f"🔄 Lecteur {fallback_index + 1} pour S{display_season} E{episode_counter} ({fb_type})...")
                        success = download_video(fb_type, fb_value, filename,
                                                 display_season, episode_counter, total_episodes_in_season)
                        if success:
                            current_eps_array_index  = fallback_index
                            all_links                = fallback_links
                            total_episodes_in_season = len(all_links)
                            fallback_success         = True
                            break

                        # Nettoyage du fichier partiel
                        if os.path.exists(filename) and os.path.getsize(filename) == 0:
                            os.remove(filename)

                        if IS_ANDROID:
                            print(f"⚠️ Échec lecteur {fallback_index + 1} pour E{episode_counter}, essai du lecteur suivant...")

                if not fallback_success:
                    sys.stdout.write("\r")
                    sys.stdout.flush()
                    print(f"⚠️  [S{display_season} E{episode_counter}/{total_episodes_in_season}] Aucun lecteur disponible — épisode ignoré.")

            episode_counter += 1
            if only_episode:
                break

        if only_episode:
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if IS_ANDROID:
            print("\n👋 Merci d'avoir utilisé Co-Chan !")
            print("🌸 À bientôt !")
        else:
            ConsoleUI.clear()
            ConsoleUI.print_logo()
            print(f"\n  {ConsoleUI.CYAN}👋  Merci d'avoir utilisé Co-Chan !{ConsoleUI.RESET}")
            print("  🌸  À bientôt !")
            print(ConsoleUI.CYAN + "  " + "═"*58 + ConsoleUI.RESET + "\n")
        time.sleep(1)
        sys.exit(0)