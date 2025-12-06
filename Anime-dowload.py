import os
import platform
import shutil
import sys
import requests
import re
import time
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

def set_title(title_text):
    s = platform.system()
    is_termux = s == "Linux" and "ANDROID_STORAGE" in os.environ
    
    if s == "Windows":
        os.system(f"title {title_text}")
    elif s == "Linux" and not is_termux:
        os.system(f'echo -e "\033]0;{title_text}\007"')

set_title("Co-Chan")

def ping_domain(domain):
    """Ping un domaine pour vérifier s'il est joignable"""
    try:
        if platform.system() == "Windows":
            result = os.system(f"ping -n 1 -w 1000 {domain} >nul 2>&1")
        else:
            result = os.system(f"ping -c 1 -W 1 {domain} >/dev/null 2>&1")
        return result == 0
    except:
        return False

def check_domain_availability():
    """Vérifie la disponibilité des domaines anime-sama.fr et anime-sama.org"""
    domains = [
        ("anime-sama.fr", "https://anime-sama.fr/catalogue/"),
        ("anime-sama.org", "https://anime-sama.org/catalogue/"),
        ("anime-sama.eu", "https://anime-sama.eu/catalogue/"),
    ]
    
    print("🔍 Vérification des serveurs...", end=" ")
    sys.stdout.flush()
    
    for domain_name, full_url in domains:
        ping_ok = ping_domain(domain_name)
        
        if ping_ok:
            print("✅ Réponse")
            return full_url
        
        # Test HTTP si le ping échoue
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(full_url, timeout=10, headers=headers)
            if response.status_code == 200:
                print("✅ Réponse")
                return full_url
        except:
            pass
    
    print("❌")
    print("❌ Co-Chan temporairement indisponible")
    print("\n⏰ Fermeture automatique dans 10 secondes...")
    time.sleep(10)
    exit(1)

def check_disk_space(min_gb=1):
    s = platform.system()
    
    if s == "Windows":
        # Vérifier le disque C: (minimum 100 Mo)
        total_c, used_c, free_c = shutil.disk_usage("C:\\")
        free_space_c_mb = free_c / (1024**2)
        
        if free_space_c_mb < 100:
            print(f"⚠️ Espace insuffisant sur C: ({free_space_c_mb:.0f} Mo disponibles, 100 Mo requis)")
            return False
        
        # Vérifier le disque où se trouve le code (minimum 1 Go)
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
    if platform.system() == "Windows":
        return os.path.join(os.getcwd())
    elif platform.system() == "Linux" and "ANDROID_STORAGE" in os.environ:
        return "/storage/emulated/0/Download/anime"
    else:
        print("Ce script ne fonctionne que sous Windows ou Android.")
        exit(1)

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
    season_info = {}  # clé = "1", "1hs", "2", "2hs", etc.
    season = 1
    consecutive_not_found = 0

    while consecutive_not_found < 3:
        found_this_round = False

        # --- Saison normale ---
        normal_url = f"{base_url}{name}/saison{season}/{language}/episodes.js"
        normal_resp = requests.get(normal_url, timeout=10)
        has_normal = normal_resp.status_code == 200 and normal_resp.text.strip()

        # --- Saison HS ---
        hs_url = f"{base_url}{name}/saison{season}hs/{language}/episodes.js"
        hs_resp = requests.get(hs_url, timeout=10)
        has_hs = hs_resp.status_code == 200 and hs_resp.text.strip()

        if has_normal or has_hs:
            found_this_round = True
            consecutive_not_found = 0

            # Cas 1 : les deux existent → on va demander plus tard à l'utilisateur
            if has_normal and has_hs:
                print(f"✔ Saison {season} (Normal + HS) trouvée → choix requis")
                season_info[f"{season}"] = {"type": "both", "normal": normal_url, "hs": hs_url, "variants": []}
            # Cas 2 : seulement normale
            elif has_normal:
                print(f"✔ Saison {season} trouvée.")
                season_info[f"{season}"] = {"type": "normal", "url": normal_url, "variants": []}
            # Cas 3 : seulement HS
            else:
                print(f"✔ Saison {season} HS trouvée.")
                season_info[f"{season}hs"] = {"type": "hs", "url": hs_url, "variants": []}

            # Variantes (ex: saison1-1, saison1hs-1, etc.)
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

    # Film & OAV (inchangés)
    for special, label in [("film", "Film"), ("oav", "OAV")]:
        url = f"{base_url}{name}/{special}/{language}/episodes.js"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and r.text.strip():
            print(f"✔ {label} trouvé.")
            season_info[special] = {"type": special, "url": url, "variants": []}

    return season_info  # ← on retourne maintenant un dict plus riche

def resolve_season_choices(season_info):
    """Si une saison a Normal + HS, on demande à l'utilisateur laquelle il veut"""
    final_seasons = []  # (display_name, url_list)

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

    return final_seasons  # ← liste de (nom_affiché, [liste_des_urls])

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
        sibnet_links, vidmoly_links = extract_video_links(url)
        episode_counter += len(sibnet_links) + len(vidmoly_links)
    
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

def get_anime_image(anime_name, folder_name):
    """Télécharge l'image de couverture depuis l'API Jikan"""
    try:
        url_name = anime_name.replace(" ", "+")
        url = f"https://api.jikan.moe/v4/anime?q={url_name}&limit=1"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if not data["data"]:
            return
        
        anime = data["data"][0]
        image_url = anime["images"]["jpg"]["large_image_url"]
        
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        image_data = image_response.content
        
        jpg_path = os.path.join(folder_name, "cover.jpg")
        with open(jpg_path, 'wb') as f:
            f.write(image_data)
        
        if pil_available:
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

def extract_video_links(url):
    response = requests.get(url)
    if response.status_code != 200:
        return [], []
    
    sibnet_pattern = r"(https://video\.sibnet\.ru/shell\.php\?videoid=\d+)"
    vidmoly_pattern = r"(https://vidmoly\.to/embed/\w+)"
    
    sibnet_links = re.findall(sibnet_pattern, response.text)
    vidmoly_links = re.findall(vidmoly_pattern, response.text)
    
    return sibnet_links, vidmoly_links

def download_video(link, filename, season, episode, max_episode):
    if not check_disk_space():
        print(f"⛔ Espace disque insuffisant. Arrêt du téléchargement pour [S{season} E{episode}/{max_episode}].")
        return
    
    ydl_opts = {
        "outtmpl": filename,
        "quiet": False,
        "ignoreerrors": True,
        "progress_hooks": [lambda d: progress_hook(d, season, episode, max_episode)],
        "no_warnings": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "merge_output_format": "mp4",
        "logger": MyLogger(),
        "socket_timeout": 60,
        "retries": 15
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
    except Exception as e:
        sys.stdout.write("\r")
        sys.stdout.flush()
        print(f"⛔ Erreur lors du téléchargement: {e}")
        return

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

def main():
    # Vérification de la disponibilité des domaines
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
        total_episodes_in_season = 0
        all_links = []

        for url in url_list:
            sibnet, vidmoly = extract_video_links(url)
            all_links.extend(sibnet + vidmoly)

        total_episodes_in_season = len(all_links)

        if total_episodes_in_season == 0:
            continue

        episode_counter = 1

        # Gestion du point de reprise
        if start_season != 0 and str(display_season) == str(start_season):
            if start_episode > 1:
                all_links = all_links[start_episode - 1:]
                episode_counter = start_episode

        print(f"♾️ Téléchargement de la Saison {display_season.upper()} ({total_episodes_in_season} épisodes)")

        for link in all_links:
            sys.stdout.write("🌐 Chargement")
            sys.stdout.flush()
            for _ in range(3):
                time.sleep(1)
                sys.stdout.write(".")
                sys.stdout.flush()
            sys.stdout.write("\r")
            sys.stdout.flush()
            
            if check_http_403(link):
                continue
            
            download_dir = os.path.join(get_download_path(), folder_name)
            os.makedirs(download_dir, exist_ok=True)
            
            if episode_counter == 1 and display_season == seasons[0][0]:
                get_anime_image(anime_name_capitalized, download_dir)
            
            filename = os.path.join(download_dir, f"s{display_season}_e{episode_counter}.mp4")
            download_video(link, filename, display_season, episode_counter, total_episodes_in_season)
            episode_counter += 1

if __name__ == "__main__":
    main()
