# ── CHANGEMENT 1 : tous les imports regroupés en haut ─────────────────────────
import os
import platform
import shutil
import sys
import requests
import re
import time
import random
import importlib.util
import tempfile      # ← était injecté dans download_video, maintenant en haut
import json          # ← nouveau
import subprocess    # ← nouveau

# Imports optionnels (nouveau — change 1)
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

pil_available = importlib.util.find_spec("PIL") is not None
if pil_available:
    from PIL import Image, ImageOps
    import io

from yt_dlp import YoutubeDL


# ── Logger yt-dlp (inchangé) ──────────────────────────────────────────────────
class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


# ── Logger silencieux (utilisé par le GUI) ────────────────────────────────────
class _SilentLogger:
    def debug(self, msg):   pass
    def warning(self, msg): pass
    def error(self, msg):   pass


# ── Config persistante (utilisée par le GUI) ──────────────────────────────────
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


# ── Utilitaires plateforme (inchangés) ────────────────────────────────────────
def is_ios_device():
    """Détecte si on est sur un appareil iOS (iPhone/iPad)"""
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
        os.system(f'echo -e "\033]0;{title_text}\007"')
    elif s == "Darwin" and not is_ios:
        os.system(f'echo -e "\033]0;{title_text}\007"')


if __name__ == "__main__":
    set_title("Co-Chan")


# ── Priorité processus ────────────────────────────────────────────────────────
def set_process_priority():
    """
    Augmente la priorité du processus pour éviter que Windows (ou l'OS)
    lui attribue moins de ressources pendant les téléchargements.

    Windows  : passe en HIGH_PRIORITY_CLASS via ctypes (ne nécessite pas admin).
               On évite REALTIME_PRIORITY_CLASS qui peut geler le système.
    Linux/Mac: tente os.nice(-10) pour réduire la valeur nice (plus haute prio).
               Échoue silencieusement si les droits sont insuffisants (pas root).
    """
    s = platform.system()
    if s == "Windows":
        if ctypes:
            try:
                # GetCurrentProcess() → handle du processus courant
                # SetPriorityClass() → 0x00000080 = HIGH_PRIORITY_CLASS
                handle = ctypes.windll.kernel32.GetCurrentProcess()
                ctypes.windll.kernel32.SetPriorityClass(handle, 0x00000080)
            except Exception:
                pass  # Pas critique, on continue sans
    else:
        try:
            current = os.nice(0)           # lire la valeur actuelle
            os.nice(max(-10, -current))    # baisser de 10 sans dépasser -20
        except (PermissionError, AttributeError, OSError):
            pass  # Pas root → silencieux, pas bloquant


# ── Domaine actif (inchangé) ──────────────────────────────────────────────────
def verify_domain_redirect(url):
    """Vérifie que l'URL redirige bien vers un domaine anime-sama valide"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.head(url, timeout=10, headers=headers, allow_redirects=True)
        final_url = response.url
        if "anime-sama" in final_url and "anime-sama.pw" not in final_url:
            return True, final_url
        return False, final_url
    except:
        return False, None


def get_active_domain():
    """Récupère le domaine actif depuis anime-sama.pw"""
    try:
        print("🔍 Recherche du serveur actif...", end=" ")
        sys.stdout.flush()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get("https://anime-sama.pw/", timeout=10, headers=headers)
        if response.status_code == 200:
            pattern = r'<a\s+class="btn-primary"\s+href="(https?://anime-sama\.[a-z]+)"'
            match = re.search(pattern, response.text)
            if match:
                base_domain = match.group(1)
                print("🔄", end=" ")
                sys.stdout.flush()
                is_valid, redirected_url = verify_domain_redirect(base_domain)
                if is_valid:
                    redirected_domain = redirected_url.split("/catalogue")[0] if "/catalogue" in redirected_url else redirected_url.rstrip("/")
                    full_url = f"{redirected_domain}/catalogue/"
                    print("✅")
                    print(f"✅ Serveur actif trouvé")
                    return full_url
                else:
                    print("⚠️")
                    print(f"⚠️ L'URL trouvée ne redirige pas correctement")

            pattern_fallback = r'href="(https?://anime-sama\.(?!pw)[a-z]+)"'
            match_fallback = re.search(pattern_fallback, response.text)
            if match_fallback:
                base_domain = match_fallback.group(1)
                print("🔄", end=" ")
                sys.stdout.flush()
                is_valid, redirected_url = verify_domain_redirect(base_domain)
                if is_valid:
                    redirected_domain = redirected_url.split("/catalogue")[0] if "/catalogue" in redirected_url else redirected_url.rstrip("/")
                    full_url = f"{redirected_domain}/catalogue/"
                    print("✅")
                    print(f"✅ Serveur actif trouvé : {redirected_domain}")
                    return full_url

        raise Exception("Impossible de trouver le serveur actif anime-sama.")

    except Exception:
        raise


def check_domain_availability():
    """Vérifie la disponibilité en récupérant le domaine actif"""
    return get_active_domain()


# ── Espace disque ─────────────────────────────────────────────────────────────
# CHANGEMENT 6 : section Android réécrite avec shutil.disk_usage()
#                au lieu de os.popen("df -h ...") peu fiable
def check_disk_space(min_gb=1):
    s = platform.system()

    if s == "Windows":
        total_c, used_c, free_c = shutil.disk_usage("C:\\")
        free_space_c_mb = free_c / (1024**2)
        if free_space_c_mb < 100:
            print(f"⚠️ Espace insuffisant sur C: ({free_space_c_mb:.0f} Mo disponibles, 100 Mo requis)")
            return False
        current_drive = os.path.splitdrive(os.getcwd())[0] + "\\"
        total, used, free = shutil.disk_usage(current_drive)
        free_space_gb = free / (1024**3)

    elif s == "Linux" and "ANDROID_STORAGE" in os.environ:
        # ← ANCIEN : os.popen("df -h /storage/emulated/0") — fragile
        # ← NOUVEAU : shutil.disk_usage() sur plusieurs chemins possibles
        free_space_gb = None
        for check_path in [
            os.path.expanduser("~/storage/downloads"),
            os.path.expanduser("~"),
            "/storage/emulated/0",
            "/data/data/com.termux/files/home",
        ]:
            try:
                if os.path.exists(check_path):
                    _, _, free = shutil.disk_usage(check_path)
                    free_space_gb = free / (1024**3)
                    break
            except Exception:
                continue
        if free_space_gb is None:
            print("⚠️ Impossible de vérifier l'espace disque. Le téléchargement continue.")
            return True

    elif s == "Darwin" and is_ios_device():
        try:
            home_path = os.path.expanduser("~")
            if os.path.exists(home_path):
                total, used, free = shutil.disk_usage(home_path)
                free_space_gb = free / (1024**3)
            else:
                free_space_gb = 0
        except:
            free_space_gb = 0
    else:
        statvfs = os.statvfs("/")
        free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)

    return free_space_gb >= min_gb


# ── Progression (inchangée) ───────────────────────────────────────────────────
def progress_hook(d, season, episode, max_episode):
    if d["status"] == "downloading":
        percent = d["_percent_str"].strip()
        sys.stdout.write(f"\r🔄 [S{season} E{episode}/{max_episode}] {percent} complet")
        sys.stdout.flush()
    elif d["status"] == "finished":
        sys.stdout.write(f"\r✅ [S{season} E{episode}/{max_episode}] Téléchargement terminé !\n")
        sys.stdout.flush()


# ── Chemins (inchangé) ────────────────────────────────────────────────────────
def get_download_path():
    """Retourne le chemin de téléchargement selon la plateforme (ou la config GUI)"""
    # Si une config GUI a été sauvegardée, on l'utilise en priorité
    cfg = _load_config()
    if cfg.get("download_dir") and os.path.isdir(cfg["download_dir"]):
        return cfg["download_dir"]

    s = platform.system()
    if s == "Windows":
        return os.path.join(os.getcwd())
    elif s == "Linux" and "ANDROID_STORAGE" in os.environ:
        return "/storage/emulated/0/Download/anime"
    elif s == "Darwin" and is_ios_device():
        possible_paths = [
            os.path.expanduser("~/Documents/anime"),
            os.path.expanduser("~/Downloads/anime"),
            os.path.join(os.getcwd(), "anime")
        ]
        for path in possible_paths:
            try:
                os.makedirs(path, exist_ok=True)
                if os.access(path, os.W_OK):
                    return path
            except:
                continue
        return os.path.join(os.getcwd(), "anime")
    elif s == "Darwin":
        return os.path.join(os.path.expanduser("~"), "Downloads", "anime")
    else:
        return os.path.join(os.path.expanduser("~"), "Downloads", "anime")


# ── Formatage (inchangé) ──────────────────────────────────────────────────────
def format_url_name(name):
    return name.lower().replace("'", "").replace(" ", "-")


def format_folder_name(name, language):
    return f"{' '.join(word.capitalize() for word in name.split())} {language.upper()}"


def normalize_anime_name(name):
    return ' '.join(name.strip().split()).lower()


# ── Existence ─────────────────────────────────────────────────────────────────
# CHANGEMENT 8 : double boucle for lang/for kind — supprime les 3 blocs
#                try/except dupliqués, code 3× plus court
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


# ── Langues disponibles ───────────────────────────────────────────────────────
# CHANGEMENT 9 : try/except sur chaque requête + break dès qu'une langue
#                est trouvée (inutile de continuer sur film si saison1 répond)
def check_available_languages(base_url, name):
    all_languages = ["vf", "va", "vkr", "vcn", "vqc", "vf1", "vf2", "vf3", "vf4", "vf5"]
    available = []
    for lang in all_languages:
        for kind in ["saison1", "film"]:
            try:
                r = requests.get(f"{base_url}{name}/{kind}/{lang}/episodes.js", timeout=5)
                if r.status_code == 200 and r.text.strip():
                    available.append(lang)
                    break  # ← langue trouvée, on passe à la suivante
            except Exception:
                continue
    return available


# ── Saisons ───────────────────────────────────────────────────────────────────
# CHANGEMENT 10 : try/except autour de chaque requests.get pour éviter
#                 les crashs en cas de coupure réseau pendant le scan
def check_seasons(base_url, name, language):
    """Détecte toutes les saisons (normales + HS) et propose un choix si les deux existent"""
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
                print(f"✔ Saison {season} (Normal + HS) trouvée → choix requis")
                season_info[f"{season}"] = {"type": "both", "normal": normal_url, "hs": hs_url, "variants": []}
            elif has_normal:
                print(f"✔ Saison {season} trouvée.")
                season_info[f"{season}"] = {"type": "normal", "url": normal_url, "variants": []}
            else:
                print(f"✔ Saison {season} HS trouvée.")
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
                            print(f"   → Variante {season}{variant_suffix}-{i} trouvée")
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
                print(f"✔ {label} trouvé.")
                season_info[special] = {"type": special, "url": url, "variants": []}
        except Exception:
            continue

    return season_info


# ── Tri des saisons (inchangé) ────────────────────────────────────────────────
def custom_sort_key(x):
    if isinstance(x, str) and x.isdigit():
        return (0, int(x))
    elif isinstance(x, str) and 'hs' in x:
        num = int(x.replace('hs', ''))
        return (0, num + 0.5)
    elif x == "film":
        return (1, 0)
    elif x == "oav":
        return (2, 0)
    else:
        return (3, str(x))


# ── Choix saison Normal/HS (inchangé) ─────────────────────────────────────────
def resolve_season_choices(season_info):
    """Si une saison a Normal + HS, on choisit automatiquement Normal (compatible GUI)."""
    final_seasons = []
    for key, info in sorted(season_info.items(), key=lambda x: custom_sort_key(x[0])):
        if info["type"] == "both":
            # En mode GUI, on sélectionne automatiquement la version Normale
            chosen_url = info["normal"]
            display = key
            urls = [chosen_url]
            if "variants" in info:
                urls.extend([v[1] for v in sorted(info["variants"])])
            final_seasons.append((display, urls))
        elif info["type"] in ["normal", "hs"]:
            display = key
            urls = [info["url"]]
            if "variants" in info:
                urls.extend([v[1] for v in sorted(info["variants"])])
            final_seasons.append((display, urls))
        elif info["type"] in ["film", "oav"]:
            final_seasons.append((key, [info["url"]]))
    return final_seasons


# ── Détection reprise (inchangée) ─────────────────────────────────────────────
def find_last_downloaded_episode(folder_path):
    """Trouve le dernier épisode téléchargé dans le dossier"""
    if not os.path.exists(folder_path):
        return None, None
    files = os.listdir(folder_path)
    episodes = []
    pattern = re.compile(r's(\w+)_e(\d+)\.mp4')
    for file in files:
        match = pattern.match(file)
        if match:
            season = match.group(1)
            episode = int(match.group(2))
            episodes.append((season, episode))
    if not episodes:
        return None, None

    def sort_key(x):
        season, episode = x
        season_num = season.replace('hs', '')
        is_hs = 'hs' in season
        if season_num.isdigit():
            return (0, int(season_num), is_hs, episode)
        elif season == "film":
            return (1, 0, False, episode)
        elif season == "oav":
            return (2, 0, False, episode)
        else:
            return (3, str(season), is_hs, episode)

    episodes.sort(key=sort_key, reverse=True)
    return episodes[0]


def count_downloaded_episodes_for_season(folder_path, target_season):
    """Compte le nombre d'épisodes téléchargés pour une saison spécifique"""
    if not os.path.exists(folder_path):
        return 0
    files = os.listdir(folder_path)
    count = 0
    pattern = re.compile(r's(\w+)_e(\d+)\.mp4')
    for file in files:
        match = pattern.match(file)
        if match:
            season = match.group(1)
            if season == target_season:
                count += 1
    return count


def get_actual_total_episodes_for_season(url_list):
    """Récupère le nombre réel d'épisodes qui seront téléchargés pour une saison donnée"""
    episode_counter = 0
    for url in url_list:
        eps_arrays = extract_video_links(url)
        if eps_arrays:
            episode_counter += len(eps_arrays[0])
    return episode_counter


# ── Point de départ ───────────────────────────────────────────────────────────
# CHANGEMENT 12 : retourne maintenant 4 valeurs (start_season, start_episode,
#                 only_season, only_episode) au lieu de 2.
#                 Nouveau menu simple avec 4 options de téléchargement.
def ask_for_starting_point(folder_name, seasons):
    """
    Demande le point de départ.
    Retourne (start_season, start_episode, only_season, only_episode).
    """
    download_dir = os.path.join(get_download_path(), folder_name)
    last_season, last_episode = find_last_downloaded_episode(download_dir)

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
                    if choice in ['o', 'oui', 'y', 'yes', '']:
                        print(f"➡️ Passage à la saison suivante S{next_season} E1")
                        return next_season, 1, False, False
                else:
                    print("🎉 Tous les épisodes disponibles ont été téléchargés !")
                    choice = input("Recommencer depuis le début ? (o/n): ").strip().lower()
                    if choice in ['o', 'oui', 'y', 'yes', '']:
                        print("➡️ Redémarrage depuis le début")
                        return 0, 0, False, False
                    else:
                        print("Arrêt du programme.")
                        sys.exit(0)
        else:
            choice = input(
                f"Reprendre depuis S{last_season} E{last_episode} ? (o/n): "
            ).strip().lower()
            if choice in ['o', 'oui', 'y', 'yes', '']:
                print(f"➡️ Reprise à partir de S{last_season} E{last_episode}")
                return last_season, last_episode, False, False

    # ── Menu options téléchargement (nouveau) ─────────────────────────────────
    print("\nOptions de téléchargement :")
    print("  1. Télécharger tous les épisodes")
    print("  2. Télécharger une saison complète")
    print("  3. Choisir un point de départ précis")
    print("  4. Télécharger un seul épisode")

    menu_choice = input("Votre choix (1-4) : ").strip()

    if menu_choice == "1" or menu_choice == "":
        print("➡️ Téléchargement de tous les épisodes")
        return 0, 0, False, False

    if menu_choice == "2":
        season_input = input(
            "Numéro de saison (ou 'film'/'oav', ajoutez 'hs' si HS): "
        ).strip().lower()
        print(f"➡️ Téléchargement de la saison {season_input} complète")
        return season_input, 1, True, False

    if menu_choice == "3":
        while True:
            try:
                season_input = input(
                    "Numéro de saison de départ (ou 'film'/'oav', ajoutez 'hs' si HS): "
                ).strip().lower()
                episode = int(input("Numéro d'épisode de départ : ").strip())
                print(f"➡️ Téléchargement à partir de S{season_input} E{episode}")
                return season_input, episode, False, False
            except ValueError:
                print("⚠️ Veuillez entrer un numéro d'épisode valide")

    if menu_choice == "4":
        while True:
            try:
                season_input = input(
                    "Numéro de saison (ou 'film'/'oav', ajoutez 'hs' si HS): "
                ).strip().lower()
                episode = int(input("Numéro d'épisode : ").strip())
                print(f"➡️ Téléchargement de S{season_input} E{episode} uniquement")
                return season_input, episode, False, True
            except ValueError:
                print("⚠️ Veuillez entrer un numéro d'épisode valide")

    # Fallback silencieux
    print("➡️ Téléchargement de tous les épisodes")
    return 0, 0, False, False


# ── Sibnet 403 ────────────────────────────────────────────────────────────────
# CHANGEMENT 13 : ajout d'un time.sleep(5) + nouvelle tentative sur erreur réseau
#                 (connexion refusée, timeout, etc.) au lieu d'un return False immédiat
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
            # ← ANCIEN : return False immédiat
            # ← NOUVEAU : sleep(5) puis nouvelle tentative
            print(f"⛔ Erreur réseau tentative {attempt+1} : {e}. Nouvelle tentative...")
            time.sleep(5)

    print("⛔ Sibnet vous a temporairement banni, veuillez réessayer dans un maximum de 2 jours.")
    time.sleep(20)
    return True


# ── Image de couverture (inchangée) ──────────────────────────────────────────
def get_anime_image(anime_name, folder_name, formatted_url_name):
    """Télécharge l'image de couverture depuis GitHub Anime-Sama, fallback Jikan"""
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

        if pil_available:
            if platform.system() == "Windows":
                ico_path = os.path.join(folder_name, "folder.ico")
                image = Image.open(io.BytesIO(image_data))
                size = 256
                square_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                width, height = image.size
                if width > height:
                    new_height = int(height * size / width)
                    resized_img = image.resize((size, new_height))
                    y_offset = (size - new_height) // 2
                    square_img.paste(resized_img, (0, y_offset))
                else:
                    new_width = int(width * size / height)
                    resized_img = image.resize((new_width, size))
                    x_offset = (size - new_width) // 2
                    square_img.paste(resized_img, (x_offset, 0))
                square_img.save(ico_path, format='ICO', sizes=[(size, size)])

                if os.name == 'nt':
                    os.system(f'attrib +h "{ico_path}"')

                desktop_ini_path = os.path.join(folder_name, "desktop.ini")

                # ── Chemin RELATIF dans desktop.ini ───────────────────────────
                # ANCIEN : IconResource=C:\chemin\absolu\folder.ico,0
                #   → cassait sur disque externe (lettre change) ou réseau
                # NOUVEAU : IconResource=folder.ico,0  (chemin relatif)
                #   → Windows résout le chemin depuis le dossier contenant
                #     desktop.ini, quel que soit le disque ou le chemin monté.
                #
                # Encodage UTF-16 LE avec BOM : requis par Windows pour lire
                # correctement desktop.ini (notamment sur NTFS externe).
                ini_content = (
                    "[.ShellClassInfo]\r\n"
                    "IconResource=folder.ico,0\r\n"
                    "[ViewState]\r\n"
                    "Mode=\r\n"
                    "Vid=\r\n"
                    "FolderType=Generic\r\n"
                )
                with open(desktop_ini_path, "w", encoding="utf-16-le") as ini_file:
                    ini_file.write("\ufeff" + ini_content)  # BOM explicite

                if os.name == 'nt':
                    # +s sur le dossier = System (requis pour que Windows lise desktop.ini)
                    # +h +s sur desktop.ini = caché + système (évite qu'il soit visible)
                    os.system(f'attrib +s "{folder_name}"')
                    os.system(f'attrib +h +s "{desktop_ini_path}"')
    except Exception:
        pass


# ── Extraction m3u8 Vidmoly ───────────────────────────────────────────────────
# CHANGEMENT 14 : 5 tentatives avec time.sleep(1) entre chaque ;
#                 retour immédiat sur 404 (inutile de réessayer)
def get_vidmoly_m3u8(video_id):
    """
    Extrait l'URL m3u8 depuis Vidmoly.
    5 tentatives silencieuses — retour immédiat sur 404.
    """
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
    url = f"https://vidmoly.biz/embed-{video_id}.html"
    for attempt in range(5):
        try:
            resp = session.get(url, headers=headers, timeout=15)
            if resp.status_code == 404:
                return None  # 404 → inutile de réessayer
            text = resp.content.decode("utf-8", errors="ignore")
            m3u8 = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', text)
            if m3u8:
                return m3u8.group(0)
        except Exception:
            pass
        if attempt < 4:
            time.sleep(1)
    return None


# ── Classification des liens (inchangée) ──────────────────────────────────────
def classify_link(url):
    """Retourne (link_type, link_value) si le lien est compatible, sinon None"""
    if "sibnet" in url:
        return ("sibnet", url)
    elif "vidmoly" in url:
        m = re.search(r"embed-([\w]+)\.html", url)
        if m:
            return ("vidmoly", m.group(1))
    elif "sendvid" in url:
        return ("sendvid", url)
    return None


# ── Parsing eps arrays (inchangé) ─────────────────────────────────────────────
def parse_eps_arrays(js_text):
    """
    Parse toutes les variables epsX du JS d'anime-sama.
    Retourne une liste de dicts triée par meilleur lecteur.
    """
    eps_blocks = re.findall(
        r"var\s+eps\d+\s*=\s*\[(.*?)\]\s*;",
        js_text,
        re.DOTALL
    )
    results = []
    for block in eps_blocks:
        all_urls = re.findall(r"'(https?://[^']+)'", block)
        if not all_urls:
            continue
        compatible = []
        for url in all_urls:
            classified = classify_link(url)
            if classified:
                compatible.append(classified)
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


# ── Extraction liens vidéo ────────────────────────────────────────────────────
# CHANGEMENT 15 : retourne TOUTES les listes de lecteurs (liste de listes)
#                 au lieu du seul meilleur lecteur.
#                 Le premier élément reste le meilleur, les suivants sont des fallbacks.
def extract_video_links(url):
    """
    Récupère TOUS les epsX depuis le JS anime-sama.
    Retourne une liste de listes de tuples (link_type, link_value).
    Le premier élément est le meilleur lecteur, les suivants sont les fallbacks.
    """
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []
    except Exception:
        return []
    eps_list = parse_eps_arrays(response.text)
    if not eps_list:
        return []
    # ← ANCIEN : return eps_list[0]["links"]  (un seul lecteur)
    # ← NOUVEAU : toutes les listes pour permettre le fallback
    return [eps["links"] for eps in eps_list]


# ── Téléchargement ────────────────────────────────────────────────────────────
# Note : ajout minimal de silent + retour True/False requis par le changement 17
def download_video(link_type, link_value, filename, season, episode, max_episode,
                   silent=False):
    """
    Télécharge un épisode. Retourne True si succès, False sinon.
    silent=True : aucun message affiché (utilisé pour les tentatives de fallback).
    """
    if not check_disk_space():
        if not silent:
            print(f"⛔ Espace disque insuffisant. Arrêt du téléchargement pour [S{season} E{episode}/{max_episode}].")
        return False

    final_url = None

    if link_type == "vidmoly":
        m3u8 = get_vidmoly_m3u8(link_value)
        if not m3u8:
            return False
        final_url = m3u8
    else:
        final_url = link_value

    anime_folder_name = os.path.basename(os.path.dirname(filename))
    is_termux = platform.system() == "Linux" and "ANDROID_STORAGE" in os.environ
    if is_termux:
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        temp_dir = os.path.join(script_dir, "temp", anime_folder_name)
    else:
        temp_dir = os.path.join(tempfile.gettempdir(), "anime-dl", anime_folder_name)
    os.makedirs(temp_dir, exist_ok=True)

    if link_type == "vidmoly":
        video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
    else:
        video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"

    if silent:
        hooks = []
        quiet = True
        logger = type('_Silent', (), {'debug': lambda s,m: None, 'warning': lambda s,m: None, 'error': lambda s,m: None})()
    else:
        hooks = [lambda d: progress_hook(d, season, episode, max_episode)]
        quiet = False
        logger = MyLogger()

    ydl_opts = {
        "outtmpl":             filename,
        "quiet":               quiet,
        "ignoreerrors":        True,
        "progress_hooks":      hooks,
        "no_warnings":         True,
        "noprogress":          silent,
        "format":              video_format,
        "merge_output_format": "mp4",
        "logger":              logger,
        "socket_timeout":      60,
        "retries":             15,
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


# ── Aide CLI (inchangée) ──────────────────────────────────────────────────────
def show_usage():
    print("Usage:")
    print("  python script.py <nom_anime> <langue>")
    print("  python script.py -h|--help|help|/?|-?")
    print()
    print("Exemples:")
    print("  python script.py \"one piece\" vf")
    print("  python script.py \"naruto\" vostfr")
    print()
    print("Plateformes supportées:")
    print("  - Windows")
    print("  - macOS")
    print("  - Linux")
    print("  - Android (Termux)")
    print()
    print("Sources vidéo supportées:")
    print("  - Sibnet")
    print("  - Vidmoly (via extraction m3u8 automatique)")
    print("  - Sendvid")


# ── Point d'entrée ────────────────────────────────────────────────────────────
def main():
    set_process_priority()  # ← monte la priorité dès le démarrage
    base_url = check_domain_availability()

    if len(sys.argv) > 1:
        if sys.argv[1].lower() in ["-h", "--help", "help", "/?", "-?"]:
            show_usage()
            return
        if len(sys.argv) == 3:
            anime_name = normalize_anime_name(sys.argv[1])
            language_input = sys.argv[2].strip().lower()
            anime_name_capitalized = anime_name.title()
            set_title(f"Co-Chan : {anime_name_capitalized}")
            if language_input == "vf":
                language_choice = "1"
            elif language_input == "vostfr":
                language_choice = "2"
            else:
                print(f"⛔ Langage '{language_input}' non reconnu. Utilisez 'vf' ou 'vostfr' ou autre valide.")
                show_usage()
                return
        else:
            print("⛔ Nombre d'arguments incorrect.")
            show_usage()
            return
    else:
        anime_name = normalize_anime_name(input("Entrez le nom de l'anime : "))
        anime_name_capitalized = anime_name.title()
        set_title(f"Co-Chan : {anime_name_capitalized}")

    formatted_url_name = format_url_name(anime_name)

    print(f"🔍 Vérification de l'existence de '{anime_name_capitalized}'...")
    if not check_anime_exists(base_url, formatted_url_name):
        print(f"❌ L'anime '{anime_name_capitalized}' n'existe pas ou essayez avec le nom en japonais.")
        print("   Ni en version française (VF), ni en version sous-titrée (VOSTFR).")
        print("   Vérifiez l'orthographe ou essayez avec un autre nom.")
        print("\n⏰ Fermeture automatique dans 5 secondes...")
        time.sleep(5)
        exit(1)

    print(f"✅ Anime '{anime_name_capitalized}' trouvé !")

    available_vf_versions = check_available_languages(base_url, formatted_url_name)

    if available_vf_versions:
        print("\nVersions disponibles :")
        for i, lang in enumerate(available_vf_versions, start=1):
            print(f"{i}. {lang.upper()}")
        print(f"{len(available_vf_versions)+1}. VOSTFR")
        choice = input("Choisissez la version : ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(available_vf_versions):
            selected_language = available_vf_versions[int(choice)-1]
        else:
            selected_language = "vostfr"
    else:
        print("⛔ Aucune version VF trouvée, VOSTFR sélectionné automatiquement.")
        selected_language = "vostfr"

    folder_name = format_folder_name(anime_name_capitalized, selected_language)

    if not check_disk_space():
        print("⛔ Espace disque insuffisant. Libérez de l'espace et réessayez.")
        exit(1)

    raw_season_info = check_seasons(base_url, formatted_url_name, selected_language)
    seasons = resolve_season_choices(raw_season_info)

    # CHANGEMENT 12 : déballage de 4 valeurs au lieu de 2
    start_season, start_episode, only_season, only_episode = ask_for_starting_point(folder_name, seasons)

    if start_season is None:
        return

    # ── CHANGEMENT 17 : boucle de téléchargement avec fallback multi-lecteur ──
    for display_season, url_list in seasons:
        # Filtrage selon only_season / only_episode
        if only_season and start_season != 0 and display_season != start_season:
            continue
        if only_episode and display_season != start_season:
            continue

        # Charger TOUS les eps arrays pour permettre les fallbacks
        all_eps_arrays = []
        for url in url_list:
            eps_arrays = extract_video_links(url)  # renvoie maintenant une liste de listes
            if eps_arrays:
                all_eps_arrays.extend(eps_arrays)

        if not all_eps_arrays:
            continue

        current_eps_array_index  = 0
        all_links                = all_eps_arrays[current_eps_array_index]
        total_episodes_in_season = max(len(arr) for arr in all_eps_arrays)

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
                print(
                    f"⛔ L'épisode {start_episode} n'existe pas pour la saison {display_season} "
                    f"({total_episodes_in_season} épisodes disponibles)."
                )
                continue
            print(f"🎬 Téléchargement de la Saison {display_season.upper()} — Épisode {start_episode} uniquement")
        else:
            print(f"♾️ Téléchargement de la Saison {display_season.upper()} ({total_episodes_in_season} épisodes)")

        while episode_counter <= total_episodes_in_season:
            episode_index = episode_counter - 1

            # Animation de chargement
            sys.stdout.write("🌐 Chargement")
            sys.stdout.flush()
            for _ in range(3):
                time.sleep(1)
                sys.stdout.write(".")
                sys.stdout.flush()
            sys.stdout.write("\r")
            sys.stdout.flush()

            # Récupérer le lien du lecteur principal
            if episode_index < len(all_links):
                link_type, link_value = all_links[episode_index]
                if link_type == "sibnet" and check_http_403(link_value):
                    episode_counter += 1
                    if only_episode:
                        break
                    continue
                primary_ok = True
            else:
                primary_ok = False  # Lecteur courant n'a pas cet épisode

            download_dir = os.path.join(get_download_path(), folder_name)
            os.makedirs(download_dir, exist_ok=True)

            # Icône de dossier au premier épisode de la première saison
            if episode_counter == 1 and display_season == seasons[0][0]:
                get_anime_image(anime_name_capitalized, download_dir, formatted_url_name)

            filename = os.path.join(download_dir, f"s{display_season}_e{episode_counter}.mp4")

            # ── Tentative avec le lecteur principal ───────────────────────────
            success = False
            if primary_ok:
                success = download_video(
                    link_type, link_value, filename,
                    display_season, episode_counter, total_episodes_in_season,
                    silent=False,
                )

            # ── Fallback multi-lecteur (silencieux) ───────────────────────────
            if not success:
                fallback_success = False
                for fallback_index, fallback_links in enumerate(all_eps_arrays):
                    if fallback_index == current_eps_array_index:
                        continue  # Sauter le lecteur déjà essayé

                    if len(fallback_links) >= episode_counter:
                        fb_type, fb_value = fallback_links[episode_counter - 1]
                        success = download_video(
                            fb_type, fb_value, filename,
                            display_season, episode_counter, total_episodes_in_season,
                            silent=True,
                        )
                        if success:
                            # Basculer sur ce lecteur pour les prochains épisodes
                            current_eps_array_index = fallback_index
                            all_links               = fallback_links
                            fallback_success        = True
                            sys.stdout.write(
                                f"\r✅ [S{display_season} E{episode_counter}/{total_episodes_in_season}] "
                                f"Téléchargement terminé !\n"
                            )
                            sys.stdout.flush()
                            break

                        # Supprimer un fichier vide éventuel laissé par l'échec
                        if os.path.exists(filename) and os.path.getsize(filename) == 0:
                            os.remove(filename)

                if not fallback_success:
                    sys.stdout.write("\r")
                    sys.stdout.flush()
                    print(
                        f"⚠️  [S{display_season} E{episode_counter}/{total_episodes_in_season}] "
                        f"Aucun lecteur disponible — épisode ignoré."
                    )

            episode_counter += 1
            if only_episode:
                break

        if only_episode:
            break


# ── CHANGEMENT 19 : handler KeyboardInterrupt autour de main() ────────────────
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Merci d'avoir utilisé Co-Chan !")
        print("🌸 À bientôt !")
        time.sleep(1)
        sys.exit(0)
