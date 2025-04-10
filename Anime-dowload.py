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
    """Set console title if on Windows or regular Linux, but not on Termux"""
    system = platform.system()
    
    is_termux = system == "Linux" and "ANDROID_STORAGE" in os.environ
    
    if system == "Windows":
        os.system(f"title {title_text}")
    elif system == "Linux" and not is_termux:
        os.system(f'echo -e "\033]0;{title_text}\007"')
    
def display_available_languages(available_languages):
    """Affiche les langues disponibles avec emoji de drapeau"""
    lang_display = {
    "vostfr": "🇯🇵 [JP] VOSTFR (Sous-titré français)", 
    "vf": "🇫🇷 [FR] VF (Version française)",
    "va": "🇬🇧 [EN] VA (Version anglaise)",
    "vkr": "🇰🇷 [KR] VKR (Version coréenne)",
    "vcn": "🇨🇳 [CN] VCN (Version chinoise)",
    "vqc": "🇨🇦 [QC] VQC (Version québécoise)",
    "vf1": "🇫🇷 [FR] VF1 (Version française alternative 1)",
    "vf2": "🇫🇷 [FR] VF2 (Version française alternative 2)",
    "vf3": "🇫🇷 [FR] VF3 (Version française alternative 3)",
    "vf4": "🇫🇷 [FR] VF4 (Version française alternative 4)",
    "vf5": "🇫🇷 [FR] VF5 (Version française alternative 5)"
}
    
    print("\nVersions disponibles :")
    for i, lang in enumerate(available_languages, start=1):
        print(f"{i}. {lang_display.get(lang, lang.upper())}")
 

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
    return f"{name.lower()} {language.upper()}"

def check_available_languages(base_url, name):
    """ Vérifie les versions VF disponibles """
    vf_versions = ["vf"] + [f"vf{i}" for i in range(1, 6)]
    available_languages = []

    for lang in vf_versions:

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
            season_info[season] = {
                'main_url': None,
                'variants': [],
                'has_main': False
            }
        
        for i in range(1, 11):
            variant_url = f"{base_url}{name}/saison{season}-{i}/{language}/episodes.js"
            response = requests.get(variant_url)
            
            if response.status_code == 200 and response.text.strip():
                print(f"\u2714 Saison {season}-{i} trouvée.")
                season_info[season]['variants'].append((i, variant_url))
                found_any = True
        
        if not found_any:
            if season in season_info:
                del season_info[season]
            break
        
        season += 1

    film_url = f"{base_url}{name}/film/{language}/episodes.js"
    response = requests.get(film_url)
    if response.status_code == 200 and response.text.strip():
        print(f"\u2714 Film trouvé.")
        season_info['film'] = {
            'main_url': film_url,
            'variants': [],
            'has_main': True
        }
    
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

def download_videos(sibnet_links, vidmoly_links, season, folder_name, current_episode=1):
    """Télécharge toutes les vidéos d'une saison"""
    download_dir = os.path.join(get_download_path(), folder_name)
    os.makedirs(download_dir, exist_ok=True)

    total_episodes = len(sibnet_links) + len(vidmoly_links)
    max_episode = current_episode + total_episodes - 1  # Calculer le dernier épisode
    episode_counter = current_episode

    print(f"📥 Téléchargement [S{season}] : {download_dir} (à partir de l'épisode {episode_counter} jusqu'à {max_episode})")

    if not (sibnet_links or vidmoly_links):
        print(f"⛔ Aucune vidéo trouvée pour la saison {season}.")
        return  # Si aucun lien n'a été trouvé, on quitte la fonction.

    for link in sibnet_links + vidmoly_links:
        sys.stdout.write("🌐 Chargement")
        sys.stdout.flush()

        for _ in range(3):
            time.sleep(0.5)
            sys.stdout.write(".")
            sys.stdout.flush()

        sys.stdout.write("\r")  # Efface la ligne de chargement
        sys.stdout.flush()

        if check_http_403(link):
            continue  # Si le code 403 est détecté, on passe à l'épisode suivant

        filename = os.path.join(download_dir, f"s{season}_e{episode_counter}.mp4")
        
        download_video(link, filename, season, episode_counter, max_episode)
        episode_counter += 1
def show_usage():
    """Affiche l'aide d'utilisation du script"""
    print("Usage: python Code.py [nom_anime] [langage]")
    print("Exemples:")
    print("  python Code.py \"one piece\" vf     # Télécharge One Piece en VF")
    print("  python Code.py naruto vostfr      # Télécharge Naruto en VOSTFR")
    print("\nOu lancez le script sans arguments pour le mode interactif.")


def main():
    base_url = "https://anime-sama.fr/catalogue/"
    
    if len(sys.argv) > 1:
        # Si "-h" ou "--help" est fourni, afficher l'aide
        if sys.argv[1].lower() in ["-h", "--help", "help", "/?", "?"]:
            show_usage()
            return
            
        if len(sys.argv) == 3:
            anime_name = sys.argv[1].strip().lower()
            language_input = sys.argv[2].strip().lower()
            set_title(f"Co-Chan : {anime_name_capitalized}")
            
            valid_languages = ["vf", "vostfr", "va", "vkr", "vcn", "vqc", "vf1", "vf2", "vf3", "vf4", "vf5"]
            
            if language_input not in valid_languages:
                print(f"⛔ Langage '{language_input}' non reconnu.")
                print(f"Langages disponibles: {', '.join(valid_languages)}")
                show_usage()
                return
                
            selected_languages = [language_input]
        else:
            print("⛔ Nombre d'arguments incorrect.")
            show_usage()
            return
    else:
        anime_name = input("Entrez le nom de l'anime : ").strip().lower()
        anime_name_capitalized = anime_name.title()  # Première lettre de chaque mot en majuscule
        set_title(f"Co-Chan : {anime_name_capitalized}")
        
        formatted_url_name = format_url_name(anime_name)
        
        print(f"🔍 Recherche des versions disponibles pour {anime_name_capitalized}...")
        available_languages = check_available_languages(base_url, formatted_url_name)
        
        if not available_languages:
            print(f"⛔ Aucune version disponible pour {anime_name_capitalized}.")
            return
        
        lang_display = {
        "vostfr": "🇯🇵 [JP] VOSTFR (Sous-titré français)", 
        "vf": "🇫🇷 [FR] VF (Version française)",
        "va": "🇬🇧 [EN] VA (Version anglaise)",
        "vkr": "🇰🇷 [KR] VKR (Version coréenne)",
        "vcn": "🇨🇳 [CN] VCN (Version chinoise)",
        "vqc": "🇨🇦 [QC] VQC (Version québécoise)",
        "vf1": "🇫🇷 [FR] VF1 (Version française alternative 1)",
        "vf2": "🇫🇷 [FR] VF2 (Version française alternative 2)",
        "vf3": "🇫🇷 [FR] VF3 (Version française alternative 3)",
        "vf4": "🇫🇷 [FR] VF4 (Version française alternative 4)",
        "vf5": "🇫🇷 [FR] VF5 (Version française alternative 5)"
        }
        
        print("\n📺 Versions disponibles :")
        for i, lang in enumerate(available_languages, start=1):
            print(f"{i}. {lang_display.get(lang, lang.upper())}")
                
        choice = input("\nChoisissez la version (numéro ou numéros séparés par des virgules) : ").strip()
        
        selected_languages = []
        
        if choice == str(len(available_languages) + 1):
            selected_languages = available_languages
        elif "," in choice:
            for c in choice.split(","):
                if c.strip().isdigit() and 1 <= int(c.strip()) <= len(available_languages):
                    selected_languages.append(available_languages[int(c.strip()) - 1])
        elif choice.isdigit() and 1 <= int(choice) <= len(available_languages):
            selected_languages.append(available_languages[int(choice) - 1])
        else:
            print("⚠️ Choix non valide. Sélection par défaut utilisée.")
            if "vostfr" in available_languages:
                selected_languages.append("vostfr")
                print(f"✅ VOSTFR sélectionné par défaut.")
            else:
                selected_languages.append(available_languages[0])
                print(f"✅ {lang_display.get(available_languages[0], available_languages[0].upper())} sélectionné par défaut.")
    
    formatted_url_name = format_url_name(anime_name)
    
    if not check_disk_space(1): 
        print("⛔ Espace disque insuffisant. Libérez de l'espace et réessayez.")
        return
    
    if len(selected_languages) > 1:
        main_folder = os.path.join(get_download_path(), anime_name.title())
        os.makedirs(main_folder, exist_ok=True)
    
    successful_downloads = 0
    for selected_language in selected_languages:
        set_title(f"Co-Chan : {anime_name_capitalized} - {selected_language.upper()}")
        
        if len(selected_languages) > 1:
            folder_name = os.path.join(anime_name.title(), f"{anime_name}_{selected_language}")
        else:
            folder_name = format_folder_name(anime_name, selected_language)
        
        print(f"\n🌟 Téléchargement de {anime_name_capitalized} en {selected_language.upper()}")
        
        print(f"🔍 Recherche des saisons disponibles...")
        seasons = check_seasons(base_url, formatted_url_name, selected_language)
        
        if not seasons:
            print(f"⛔ Aucune saison trouvée pour {anime_name_capitalized} en {selected_language.upper()}.")
            continue
        
        print(f"✅ {len(seasons)} saison(s)/partie(s) trouvée(s).")
        
        episode_counters = {}
        last_processed = {}  # Pour suivre la dernière saison/variante traitée
        
        sorted_seasons = sorted(seasons, key=lambda x: str(x[0]))
        
        for season, url, is_variant, variant_num in sorted_seasons:
            if not check_disk_space():
                print("⛔ Espace disque insuffisant. Arrêt du téléchargement.")
                break
                
            if season in ["film", "oav"]:
                print(f"\n🎬 Traitement {'des OAVs' if season == 'oav' else 'du film'} en {selected_language.upper()}")
                sibnet_links, vidmoly_links = extract_video_links(url)
                if sibnet_links or vidmoly_links:
                    download_videos(sibnet_links, vidmoly_links, season, folder_name)
                    successful_downloads += 1
                else:
                    print(f"⛔ Aucun lien vidéo trouvé pour {'les OAVs' if season == 'oav' else 'le film'}.")
                continue
            
            sibnet_links, vidmoly_links = extract_video_links(url)
            total_episodes = len(sibnet_links) + len(vidmoly_links)
            
            if not (sibnet_links or vidmoly_links):
                print(f"⛔ Aucun épisode trouvé pour {'la Partie ' + str(variant_num) + ' de ' if is_variant else ''}la saison {season}")
                continue
                
            start_episode = 1  # Par défaut, commencer à 1
            
            if is_variant:
                if season in last_processed:
                    start_episode = last_processed[season] + 1
                else:
                    start_episode = 1
            else:
                start_episode = 1
            
            print(f"\n🎬 Traitement de {'la Partie ' + str(variant_num) + ' de ' if is_variant else ''}la saison {season}")
            print(f"🔢 Épisodes: {start_episode} à {start_episode + total_episodes - 1}")
            
            download_videos(sibnet_links, vidmoly_links, season, folder_name, start_episode)
            successful_downloads += 1
            
            last_processed[season] = start_episode + total_episodes - 1
    

    if successful_downloads > 0:
        print(f"\n✅ Téléchargement terminé pour {anime_name_capitalized}!")
        print(f"📂 Les fichiers ont été enregistrés dans: {get_download_path()}")
    else:
        print(f"\n⛔ Aucun téléchargement réussi pour {anime_name_capitalized}.")
    
 
if __name__ == "__main__":
    main()


