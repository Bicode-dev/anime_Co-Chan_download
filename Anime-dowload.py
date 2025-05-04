#lesjeuxmathis autor
import os
import platform
import shutil
import sys
import requests
import re
import time
from yt_dlp import YoutubeDL

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)
def set_title(title_text):
    system = platform.system()
    
    # Check if running on Termux (Android)
    is_termux = system == "Linux" and "ANDROID_STORAGE" in os.environ
    
    if system == "Windows":
        os.system(f"title {title_text}")
    elif system == "Linux" and not is_termux:
        # For regular Linux terminals that support title setting
        os.system(f'echo -e "\033]0;{title_text}\007"')
    # Skip title setting on Termux as it's not supported

set_title("Co-Chan")
def check_disk_space(min_gb=1):
    """ Vérifie si l'espace disque disponible est supérieur à 1 Go """
    system = platform.system()

    if system == "Windows":
        total, used, free = shutil.disk_usage("C:\\")
        free_space_gb = free / (1024 ** 3)
    
    elif system == "Linux" and "ANDROID_STORAGE" in os.environ:
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
        free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024 ** 3)

    return free_space_gb >= min_gb

def progress_hook(d, season, episode, max_episode):
    """Affiche la progression du téléchargement"""
    if d["status"] == "downloading":
        percent = d["_percent_str"].strip()
        sys.stdout.write(f"\r🔄 [S{season} E{episode}/{max_episode}] {percent} complet")
        sys.stdout.flush()
    elif d["status"] == "finished":
        sys.stdout.write(f"\r✅ [S{season} E{episode}/{max_episode}] Téléchargement terminé !\n")
        sys.stdout.flush()

def get_download_path():
    """Retourne le chemin de téléchargement adapté à la plateforme"""
    if platform.system() == "Windows":
        return os.path.join(os.getcwd())
    elif platform.system() == "Linux" and "ANDROID_STORAGE" in os.environ:
        return "/storage/emulated/0/Download/anime"
    else:
        print("Ce script ne fonctionne que sous Windows ou Android.")
        exit(1)

def format_url_name(name):
    """Format URL : suppression des apostrophes, remplacement des espaces par des tirets"""
    return name.lower().replace("'", "").replace(" ", "-")

def format_folder_name(name, language):
    """Format du dossier de téléchargement"""
    capitalized_name = ' '.join(word.capitalize() for word in name.split())
    return f"{capitalized_name} {language.upper()}"


def check_available_languages(base_url, name):
    """Vérifie toutes les versions linguistiques disponibles"""
    all_languages = ["vf", "va", "vkr", "vcn", "vqc", "vf1", "vf2", "vf3", "vf4", "vf5"]
    available_languages = []
    for lang in all_languages:
        season_url = f"{base_url}{name}/saison1/{lang}/episodes.js"
        season_response = requests.get(season_url)
        
        film_url = f"{base_url}{name}/film/{lang}/episodes.js"
        film_response = requests.get(film_url)
        
        if (season_response.status_code == 200 and season_response.text.strip()) or \
           (film_response.status_code == 200 and film_response.text.strip()):
            available_languages.append(lang)
    return available_languages

def check_seasons(base_url, name, language):
    """Vérifie les saisons, films et OAVs disponibles avec des variantes de numérotation"""
    available_seasons = []
    season_info = {}
    
    season = 1
    while True:
        found_any = False
        
        main_url = f"{base_url}{name}/saison{season}/{language}/episodes.js"
        response = requests.get(main_url)
        
        if response.status_code == 200 and response.text.strip():
            print(f"\u2714 Saison {season} trouvée.")
            
            season_info[season] = {
                'main_url': main_url,
                'variants': [],
                'has_main': True
            }
            
            found_any = True
        else:
            # Si pas de saison principale, vérifier si on a des variantes
            season_info[season] = {
                'main_url': None,
                'variants': [],
                'has_main': False
            }
        
        # Vérifier toutes les variantes pour cette saison
        for i in range(1, 11):
            variant_url = f"{base_url}{name}/saison{season}-{i}/{language}/episodes.js"
            response = requests.get(variant_url)
            
            if response.status_code == 200 and response.text.strip():
                print(f"\u2714 Saison {season}-{i} trouvée.")
                season_info[season]['variants'].append((i, variant_url))
                found_any = True
        
        if not found_any:
            # Si aucune URL principale ou variante n'a été trouvée pour cette saison,
            # on la supprime du dictionnaire et on arrête la boucle
            if season in season_info:
                del season_info[season]
            break
        
        season += 1

    # Vérification des films
    film_url = f"{base_url}{name}/film/{language}/episodes.js"
    response = requests.get(film_url)
    if response.status_code == 200 and response.text.strip():
        print(f"\u2714 Film trouvé.")
        season_info['film'] = {
            'main_url': film_url,
            'variants': [],
            'has_main': True
        }
    
    # Vérification des OAVs
    oav_url = f"{base_url}{name}/oav/{language}/episodes.js"
    response = requests.get(oav_url)
    if response.status_code == 200 and response.text.strip():
        print(f"\u2714 OAV trouvé.")
        season_info['oav'] = {
            'main_url': oav_url,
            'variants': [],
            'has_main': True
        }
    
    # Construire la liste finale des saisons à télécharger
    for season_num, info in season_info.items():
        # D'abord ajouter la saison principale si elle existe
        if info['has_main']:
            available_seasons.append((season_num, info['main_url'], False, 0))
        
        # Ensuite ajouter les variantes dans l'ordre
        for variant_num, variant_url in sorted(info['variants']):
            available_seasons.append((season_num, variant_url, True, variant_num))
    
    return available_seasons

def check_http_403(url):
    """Vérifie si l'URL retourne un code HTTP 403 avec 5 tentatives"""
    attempts = 0
    while attempts < 5:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 403:
                print(f"⛔ Tentative {attempts + 1} échouée : Sibnet a renvoyé un code 403. Nouvelle tentatives veuillez patienter.")
                time.sleep(10)  # Attente de 10 secondes avant de réessayer
                attempts += 1
            else:
                return False
        except requests.exceptions.RequestException as e:
            print(f"⛔ Erreur de connexion : {e}")
            return False

    # Après 5 tentatives infructueuses, afficher un message de bannissement
    print("⛔ Sibnet vous a temporairement banni, veuillez réessayer dans un maximum de 2 jours.")
    time.sleep(20)  # Pause de 20 secondes pour permettre à l'utilisateur de voir le message
    return True

def extract_video_links(url):
    """Extrait les liens vidéo Sibnet et Vidmoly"""
    response = requests.get(url)
    
    if response.status_code != 200:
        return [], []

    sibnet_pattern = r"(https://video\.sibnet\.ru/shell\.php\?videoid=\d+)"
    vidmoly_pattern = r"(https://vidmoly\.to/embed/\w+)"

    sibnet_links = re.findall(sibnet_pattern, response.text)
    vidmoly_links = re.findall(vidmoly_pattern, response.text)

    return sibnet_links, vidmoly_links

def download_video(link, filename, season, episode, max_episode):
    """Télécharge une vidéo en affichant la progression"""
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
        "socket_timeout": 60,  # Augmenter le délai d'attente avant un timeout (en secondes)
        "retries": 15,  # Nombre de tentatives en cas d'échec
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
    except Exception as e:
        # Efface la ligne d'erreur précédente et affiche l'erreur
        sys.stdout.write("\r")  # Efface la ligne de l'erreur précédente
        sys.stdout.flush()
        print(f"⛔ Erreur lors du téléchargement: {e}")
        return

def ask_for_starting_point():
    while True:
        starting_point = input("Spécifiez un point de départ (exemple: s1_e5, film_e1, oav_e1) ou 0 pour tout télécharger: ").strip().lower()
        
        if starting_point == "0":
            print("➡️ Téléchargement de tous les épisodes de toutes les saisons")
            return 0, 0
        
        # Pattern pour saisons normales: s1_e5    
        season_pattern = re.compile(r's(\d+)_e(\d+)')
        season_match = season_pattern.match(starting_point)
        
        # Pattern pour films: film_e1
        film_pattern = re.compile(r'film_e(\d+)')
        film_match = film_pattern.match(starting_point)
        
        # Pattern pour OAVs: oav_e1
        oav_pattern = re.compile(r'oav_e(\d+)')
        oav_match = oav_pattern.match(starting_point)
        
        if season_match:
            season_num = int(season_match.group(1))
            episode_num = int(season_match.group(2))
            print(f"➡️ Téléchargement à partir de la saison {season_num}, épisode {episode_num}")
            return season_num, episode_num
        elif film_match:
            episode_num = int(film_match.group(1))
            print(f"➡️ Téléchargement à partir du film, épisode {episode_num}")
            return "film", episode_num
        elif oav_match:
            episode_num = int(oav_match.group(1))
            print(f"➡️ Téléchargement à partir de l'OAV, épisode {episode_num}")
            return "oav", episode_num
        else:
            print("⚠️ Format incorrect. Utilisez s<saison>_e<episode>, film_e<episode>, oav_e<episode> ou 0 pour tout")


def download_videos(sibnet_links, vidmoly_links, season, folder_name, current_episode=1):
    download_dir = os.path.join(get_download_path(), folder_name)
    os.makedirs(download_dir, exist_ok=True)

    total_episodes = len(sibnet_links) + len(vidmoly_links)
    max_episode = total_episodes
    
    print(f"📥 Téléchargement [S{season}] : {download_dir} (à partir de l'épisode {current_episode} jusqu'à {max_episode})")

    if not (sibnet_links or vidmoly_links):
        print(f"⛔ Aucune vidéo trouvée pour la saison {season}.")
        return

    all_links = sibnet_links + vidmoly_links
    if current_episode > 1:
        if current_episode > len(all_links):
            print(f"⛔ L'épisode de départ ({current_episode}) dépasse le nombre total d'épisodes ({len(all_links)})")
            return
        all_links = all_links[current_episode - 1:]

    episode_counter = current_episode
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

        filename = os.path.join(download_dir, f"s{season}_e{episode_counter}.mp4")
        
        download_video(link, filename, season, episode_counter, max_episode)
        episode_counter += 1


def main():
    base_url = "https://anime-sama.fr/catalogue/"
    
    if len(sys.argv) > 1:
        if sys.argv[1].lower() in ["-h", "--help", "help", "/?", "-?"]:
            show_usage()
            return
            
        if len(sys.argv) == 3:
            anime_name = sys.argv[1].strip().lower()
            language_input = sys.argv[2].strip().lower()
            anime_name_capitalized = anime_name.capitalize()
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
        anime_name = input("Entrez le nom de l'anime : ").strip().lower()
        anime_name_capitalized = anime_name.capitalize()
        set_title(f"Co-Chan : {anime_name_capitalized}")
    formatted_url_name = format_url_name(anime_name)

    available_vf_versions = check_available_languages(base_url, formatted_url_name)
    
    if available_vf_versions:
        print("\nVersions disponibles :")
        for i, lang in enumerate(available_vf_versions, start=1):
            print(f"{i}. {lang.upper()}")

        print(f"{len(available_vf_versions) + 1}. VOSTFR")
        
        choice = input("Choisissez la version : ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(available_vf_versions):
            selected_language = available_vf_versions[int(choice) - 1]
        else:
            selected_language = "vostfr"
    else:
        print("⛔ Aucune version VF trouvée, VOSTFR sélectionné automatiquement.")
        selected_language = "vostfr"

    folder_name = format_folder_name(anime_name_capitalized, selected_language)

    if not check_disk_space():
        print("⛔ Espace disque insuffisant. Libérez de l'espace et réessayez.")
        exit(1)

    seasons = check_seasons(base_url, formatted_url_name, selected_language)
    
    start_season, start_episode = ask_for_starting_point()
    
    episode_counters = {}
    last_processed = {}
    # Dans la fonction main(), modifiez la section qui traite les saisons comme ceci:
    for season, url, is_variant, variant_num in seasons:
        # Vérification pour sauter les saisons antérieures si un point de départ a été défini
        if start_season != 0 and start_season != "film" and start_season != "oav":
            # C'est une saison normale
            if season != "film" and season != "oav" and season < start_season:
                print(f"⏭️ Saison {season} ignorée (démarre à S{start_season})")
                continue
            
        # Traitement des films et OAVs
        if season in ["film", "oav"]:
            # Si l'utilisateur a demandé spécifiquement ce type de contenu
            if start_season == season:
                sibnet_links, vidmoly_links = extract_video_links(url)
                if sibnet_links or vidmoly_links:
                    download_videos(sibnet_links, vidmoly_links, season, folder_name, start_episode)
            # Sinon, télécharger tous les contenus si l'utilisateur a demandé tout
            elif start_season == 0:
                sibnet_links, vidmoly_links = extract_video_links(url)
                if sibnet_links or vidmoly_links:
                    download_videos(sibnet_links, vidmoly_links, season, folder_name)
            continue
        
        # Traitement des saisons normales
        sibnet_links, vidmoly_links = extract_video_links(url)
        total_episodes = len(sibnet_links) + len(vidmoly_links)
        
        if not (sibnet_links or vidmoly_links):
            print(f"⛔ Aucun épisode trouvé pour {'la Partie ' + str(variant_num) + ' de ' if is_variant else ''}la saison {season}")
            continue
            
        current_episode = 1
        
        if season == start_season and start_season != 0:
            current_episode = start_episode
        
        if is_variant:
            if season in last_processed:
                current_episode = last_processed[season] + 1
        
        print(f"♾️ Traitement de {'la Partie ' + str(variant_num) + ' de ' if is_variant else ''}la saison {season}")
        print(f"🔢 Épisodes: {current_episode} à {current_episode + total_episodes - 1}")
        
        download_videos(sibnet_links, vidmoly_links, season, folder_name, current_episode)
        
        last_processed[season] = current_episode + total_episodes - 1

if __name__ == "__main__":
    main()
