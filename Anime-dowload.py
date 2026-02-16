import os
import platform
import shutil
import sys
import requests
import re
import time
import random
import importlib.util

pil_available = importlib.util.find_spec("PIL") is not None
if pil_available:
    from PIL import Image, ImageOps
    import io

from yt_dlp import YoutubeDL

class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

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

set_title("Co-Chan")

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

        print("❌")
        print("❌ Impossible de trouver le serveur actif")
        print("\n⏰ Fermeture automatique dans 10 secondes...")
        time.sleep(10)
        exit(1)

    except Exception as e:
        print("❌")
        print(f"❌ Erreur lors de la récupération du serveur : {e}")
        print("\n⏰ Fermeture automatique dans 10 secondes...")
        time.sleep(10)
        exit(1)

def check_domain_availability():
    """Vérifie la disponibilité en récupérant le domaine actif"""
    return get_active_domain()

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
        except:
            free_space_gb = 0
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

def progress_hook(d, season, episode, max_episode):
    if d["status"] == "downloading":
        percent = d["_percent_str"].strip()
        sys.stdout.write(f"\r🔄 [S{season} E{episode}/{max_episode}] {percent} complet")
        sys.stdout.flush()
    elif d["status"] == "finished":
        sys.stdout.write(f"\r✅ [S{season} E{episode}/{max_episode}] Téléchargement terminé !\n")
        sys.stdout.flush()

def get_download_path():
    """Retourne le chemin de téléchargement selon la plateforme"""
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

def format_url_name(name):
    return name.lower().replace("'", "").replace(" ", "-")

def format_folder_name(name, language):
    return f"{' '.join(word.capitalize() for word in name.split())} {language.upper()}"

def normalize_anime_name(name):
    return ' '.join(name.strip().split()).lower()

def check_anime_exists(base_url, formatted_url_name):
    test_languages = ["vf", "vostfr", "va", "vkr", "vcn", "vqc"]

    for lang in test_languages:
        season_url = f"{base_url}{formatted_url_name}/saison1/{lang}/episodes.js"
        try:
            response = requests.get(season_url, timeout=5)
            if response.status_code == 200 and response.text.strip():
                return True
        except:
            continue

        film_url = f"{base_url}{formatted_url_name}/film/{lang}/episodes.js"
        try:
            response = requests.get(film_url, timeout=5)
            if response.status_code == 200 and response.text.strip():
                return True
        except:
            continue

        oav_url = f"{base_url}{formatted_url_name}/oav/{lang}/episodes.js"
        try:
            response = requests.get(oav_url, timeout=5)
            if response.status_code == 200 and response.text.strip():
                return True
        except:
            continue

    return False

def check_available_languages(base_url, name):
    all_languages = ["vf", "va", "vkr", "vcn", "vqc", "vf1", "vf2", "vf3", "vf4", "vf5"]
    available_languages = []

    for lang in all_languages:
        season_url = f"{base_url}{name}/saison1/{lang}/episodes.js"
        season_response = requests.get(season_url)

        film_url = f"{base_url}{name}/film/{lang}/episodes.js"
        film_response = requests.get(film_url)

        if ((season_response.status_code == 200 and season_response.text.strip()) or
            (film_response.status_code == 200 and film_response.text.strip())):
            available_languages.append(lang)

    return available_languages

def check_seasons(base_url, name, language):
    """Détecte toutes les saisons (normales + HS) et propose un choix si les deux existent"""
    season_info = {}
    season = 1
    consecutive_not_found = 0

    while consecutive_not_found < 3:
        found_this_round = False

        normal_url = f"{base_url}{name}/saison{season}/{language}/episodes.js"
        normal_resp = requests.get(normal_url, timeout=10)
        has_normal = normal_resp.status_code == 200 and normal_resp.text.strip()

        hs_url = f"{base_url}{name}/saison{season}hs/{language}/episodes.js"
        hs_resp = requests.get(hs_url, timeout=10)
        has_hs = hs_resp.status_code == 200 and hs_resp.text.strip()

        if has_normal or has_hs:
            found_this_round = True
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

            for base_key, base_url_var in [(f"{season}", normal_url if has_normal else None), (f"{season}hs", hs_url if has_hs else None)]:
                if base_url_var is None:
                    continue
                i = 1
                variant_not_found = 0
                while variant_not_found < 3:
                    variant_suffix = 'hs' if 'hs' in base_key else ''
                    variant_url = f"{base_url}{name}/saison{season}{variant_suffix}-{i}/{language}/episodes.js"
                    r = requests.get(variant_url, timeout=10)
                    if r.status_code == 200 and r.text.strip():
                        season_info[base_key]["variants"].append((i, variant_url))
                        print(f"   → Variante {season}{variant_suffix}-{i} trouvée")
                        variant_not_found = 0
                    else:
                        variant_not_found += 1
                    i += 1
        else:
            consecutive_not_found += 1

        season += 1

    for special, label in [("film", "Film"), ("oav", "OAV")]:
        url = f"{base_url}{name}/{special}/{language}/episodes.js"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and r.text.strip():
            print(f"✔ {label} trouvé.")
            season_info[special] = {"type": special, "url": url, "variants": []}

    return season_info

def resolve_season_choices(season_info):
    """Si une saison a Normal + HS, on demande à l'utilisateur laquelle il veut"""
    final_seasons = []

    for key, info in sorted(season_info.items(), key=lambda x: custom_sort_key(x[0])):
        if info["type"] == "both":
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
            # Prendre le premier eps array (le meilleur)
            episode_counter += len(eps_arrays[0])
    return episode_counter

def ask_for_starting_point(folder_name, seasons):
    """Demande le point de départ avec détection automatique et vérification corrigée"""
    download_dir = os.path.join(get_download_path(), folder_name)
    last_season, last_episode = find_last_downloaded_episode(download_dir)

    if last_season is not None and last_episode is not None:
        print(f"📁 Dernier épisode détecté : S{last_season} E{last_episode}")

        downloaded_count = count_downloaded_episodes_for_season(download_dir, last_season)
        total_episodes_in_season = get_actual_total_episodes_for_season([url_list for display, url_list in seasons if display == last_season][0])

        print(f"📊 Épisodes téléchargés pour S{last_season}: {downloaded_count}/{total_episodes_in_season}")

        if total_episodes_in_season > 0 and downloaded_count >= total_episodes_in_season:
            print(f"✅ Tous les épisodes de la saison {last_season} sont déjà téléchargés")

            season_keys = [display for display, _ in seasons]

            current_season_index = season_keys.index(last_season) if last_season in season_keys else None

            if current_season_index is not None and current_season_index + 1 < len(season_keys):
                next_season = season_keys[current_season_index + 1]
                choice = input(f"Passer à la saison suivante S{next_season} E1 ? (o/n): ").strip().lower()

                if choice in ['o', 'oui', 'y', 'yes', '']:
                    print(f"➡️ Passage à la saison suivante S{next_season} E1")
                    return next_season, 1
            else:
                print("🎉 Tous les épisodes disponibles ont été téléchargés !")
                choice = input("Recommencer depuis le début ? (o/n): ").strip().lower()

                if choice in ['o', 'oui', 'y', 'yes', '']:
                    print("➡️ Redémarrage depuis le début")
                    return 0, 0
                else:
                    print("Arrêt du programme.")
                    exit(0)
        else:
            choice = input(f"Continuer en retéléchargeant le dernier épisode S{last_season} E{last_episode} ? (o/n): ").strip().lower()

            if choice in ['o', 'oui', 'y', 'yes', '']:
                print(f"➡️ Reprise à partir de S{last_season} E{last_episode} (retéléchargement)")
                return last_season, last_episode

    choice = input("Télécharger tous les épisodes ? (o/n): ").strip().lower()

    if choice in ['o', 'oui', 'y', 'yes', '']:
        print("➡️ Téléchargement de tous les épisodes")
        return 0, 0

    while True:
        try:
            season_input = input("Numéro de saison (ou 'film'/'oav', ajoutez 'hs' si HS): ").strip().lower()

            if season_input == "film":
                season = "film"
            elif season_input == "oav":
                season = "oav"
            else:
                season = season_input

            episode = int(input("Numéro d'épisode: ").strip())

            print(f"➡️ Téléchargement à partir de S{season} E{episode}")
            return season, episode

        except ValueError:
            print("⚠️ Veuillez entrer des nombres valides")

def check_http_403(url):
    attempts = 0

    while attempts < 5:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 403:
                print(f"⛔ Tentative {attempts+1} échouée : Sibnet a renvoyé un code 403. Nouvelle tentatives veuillez patienter.")
                time.sleep(10)
                attempts += 1
            else:
                return False
        except requests.exceptions.RequestException as e:
            print(f"⛔ Erreur de connexion : {e}")
            return False

    print("⛔ Sibnet vous a temporairement banni, veuillez réessayer dans un maximum de 2 jours.")
    time.sleep(20)
    return True

def get_anime_image(anime_name, folder_name, formatted_url_name):
    """Télécharge l'image de couverture depuis GitHub Anime-Sama, fallback Jikan"""
    try:
        # Tentative 1 : GitHub Anime-Sama
        image_data = None
        github_url = f"https://raw.githubusercontent.com/Anime-Sama/IMG/img/contenu/{formatted_url_name}.jpg"
        github_response = requests.get(github_url, timeout=10)
        if github_response.status_code == 200:
            image_data = github_response.content
        else:
            # Tentative 2 : fallback API Jikan
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

                absolute_ico_path = os.path.abspath(ico_path)
                desktop_ini_path = os.path.join(folder_name, "desktop.ini")

                with open(desktop_ini_path, "w") as ini_file:
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

def get_vidmoly_m3u8(video_id):
    """Extrait l'URL m3u8 depuis vidmoly (5 tentatives silencieuses)"""
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
    
    # 5 tentatives silencieuses sans rien afficher
    for attempt in range(5):
        try:
            url = f"https://vidmoly.biz/embed-{video_id}.html"
            resp = session.get(url, headers=headers, timeout=15)
            text = resp.content.decode("utf-8", errors="ignore")
            m3u8 = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', text)
            if m3u8:
                return m3u8.group(0)
        except Exception:
            pass  # Silent fail, on retente
        
        if attempt < 4:  # Pause avant la prochaine tentative (sauf après la dernière)
            time.sleep(1)
    
    # Après 5 échecs, retourne None (géré par le système de fallback)
    return None

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

def parse_eps_arrays(js_text):
    """
    Parse toutes les variables epsX du JS d'anime-sama.
    Chaque epsX est un lecteur différent pouvant contenir des liens mixtes.
    Retourne une liste de dicts avec total, compatibles et liens classifiés.
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
            "total": len(all_urls),
            "compatible": len(compatible),
            "links": compatible
        })

    results.sort(key=lambda x: (x["compatible"], x["total"]), reverse=True)

    if len(results) > 1:
        best = results[0]
        tied = [r for r in results if r["compatible"] == best["compatible"] and r["total"] == best["total"]]
        if len(tied) > 1:
            results[0] = random.choice(tied)
    return results

def extract_video_links(url):
    """
    Récupère TOUS les epsX depuis le JS anime-sama pour permettre les fallbacks.
    Retourne une liste de listes de tuples (link_type, link_value).
    Le premier élément est le meilleur lecteur, les suivants sont les fallbacks.
    """
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return []

    eps_list = parse_eps_arrays(response.text)
    if not eps_list:
        return []

    # Retourne tous les eps arrays (pas juste le meilleur)
    return [eps["links"] for eps in eps_list]

def download_video(link_type, link_value, filename, season, episode, max_episode):
    if not check_disk_space():
        print(f"⛔ Espace disque insuffisant. Arrêt du téléchargement pour [S{season} E{episode}/{max_episode}].")
        return False

    final_url = None

    if link_type == "vidmoly":
        m3u8 = get_vidmoly_m3u8(link_value)
        if not m3u8:
            return False  # Échec silencieux, sera géré par le fallback
        final_url = m3u8
    else:
        final_url = link_value

    # Dossier temp nommé d'après l'anime
    import tempfile
    anime_folder_name = os.path.basename(os.path.dirname(filename))
    is_termux = platform.system() == "Linux" and "ANDROID_STORAGE" in os.environ

    if is_termux:
        # Termux : dossier temp à côté du script
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        temp_dir = os.path.join(script_dir, "temp", anime_folder_name)
    else:
        # Windows / macOS / Linux : dossier temp système de l'OS
        temp_dir = os.path.join(tempfile.gettempdir(), "anime-dl", anime_folder_name)

    os.makedirs(temp_dir, exist_ok=True)

    # Vidmoly = flux HLS (m3u8) : pistes vidéo et audio séparées dans le stream
    # → on essaie toutes les combinaisons pour trouver la meilleure qualité
    # Sibnet / Sendvid = fichier déjà muxé (vidéo+audio dans 1 seul fichier)
    # → on cible directement mp4+m4a, et si ça marche pas on prend le meilleur dispo
    if link_type == "vidmoly":
        video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
    else:
        # sibnet, sendvid (et tout autre lecteur)
        # sendvid utilise généralement AAC (m4a), le fallback /best couvre les autres cas
        video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"

    ydl_opts = {
        "outtmpl": filename,
        "quiet": False,
        "ignoreerrors": True,
        "progress_hooks": [lambda d: progress_hook(d, season, episode, max_episode)],
        "no_warnings": True,
        "format": video_format,
        "merge_output_format": "mp4",
        "logger": MyLogger(),
        "socket_timeout": 60,
        "retries": 15,
        "paths": {"temp": temp_dir},
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([final_url])
        return True

    except Exception as e:
        sys.stdout.write("\r")
        sys.stdout.flush()
        return False

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

def main():
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

    start_season, start_episode = ask_for_starting_point(folder_name, seasons)

    for display_season, url_list in seasons:
        # Extraire TOUS les eps arrays pour permettre les fallbacks
        all_eps_arrays = []
        for url in url_list:
            eps_arrays = extract_video_links(url)
            if eps_arrays:
                all_eps_arrays.extend(eps_arrays)
        
        if not all_eps_arrays:
            continue
        
        # Utiliser le premier eps array comme principal
        current_eps_array_index = 0
        all_links = all_eps_arrays[current_eps_array_index]
        total_episodes_in_season = len(all_links)

        if total_episodes_in_season == 0:
            continue

        episode_counter = 1

        if start_season != 0:
            season_keys = [s for s, _ in seasons]
            try:
                start_index = season_keys.index(start_season)
                current_index = season_keys.index(display_season)

                if current_index < start_index:
                    print(f"⏭️ Saison {display_season.upper()} ignorée (avant S{start_season})")
                    continue
                elif current_index == start_index and start_episode > 1:
                    episode_counter = start_episode
                    print(f"➡️ Reprise à S{display_season} E{start_episode}")
            except ValueError:
                pass

        print(f"♾️ Téléchargement de la Saison {display_season.upper()} ({total_episodes_in_season} épisodes)")

        while episode_counter <= total_episodes_in_season:
            episode_index = episode_counter - 1
            
            if episode_index >= len(all_links):
                break
                
            link_type, link_value = all_links[episode_index]

            if link_type == "sibnet" and check_http_403(link_value):
                episode_counter += 1
                continue

            download_dir = os.path.join(get_download_path(), folder_name)
            os.makedirs(download_dir, exist_ok=True)

            if episode_counter == 1 and display_season == seasons[0][0]:
                get_anime_image(anime_name_capitalized, download_dir, formatted_url_name)

            filename = os.path.join(download_dir, f"s{display_season}_e{episode_counter}.mp4")
            success = download_video(link_type, link_value, filename, display_season, episode_counter, total_episodes_in_season)
            
            if not success:
                # Échec du téléchargement - essayer les autres lecteurs (eps arrays)
                fallback_success = False
                
                for fallback_index in range(len(all_eps_arrays)):
                    if fallback_index == current_eps_array_index:
                        continue  # Skip le lecteur actuel
                    
                    fallback_links = all_eps_arrays[fallback_index]
                    
                    # Vérifier si le fallback a au moins autant d'épisodes
                    if len(fallback_links) >= episode_counter:
                        fallback_episode_index = episode_counter - 1
                        fallback_link_type, fallback_link_value = fallback_links[fallback_episode_index]
                        
                        # Réessayer avec ce lecteur alternatif
                        success = download_video(fallback_link_type, fallback_link_value, filename, 
                                                display_season, episode_counter, total_episodes_in_season)
                        
                        if success:
                            # Le fallback a marché ! Basculer sur ce lecteur pour les prochains épisodes
                            current_eps_array_index = fallback_index
                            all_links = fallback_links
                            total_episodes_in_season = len(all_links)
                            fallback_success = True
                            break
                
                if not fallback_success:
                    # Aucun lecteur n'a fonctionné, afficher un message clair
                    sys.stdout.write("\r")
                    sys.stdout.flush()
                    print(f"❌ [S{display_season} E{episode_counter}/{total_episodes_in_season}] Téléchargement échoué ! Passage à l'épisode suivant...")
                    episode_counter += 1
                else:
                    # Succès avec le fallback, continuer normalement
                    episode_counter += 1
            else:
                # Téléchargement réussi
                episode_counter += 1

if __name__ == "__main__":
    main()
