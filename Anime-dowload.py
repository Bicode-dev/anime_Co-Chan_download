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
        # On affiche directement l'erreur ici, mais l'écrasement sera fait ailleurs
        print(msg)
os.system("title Anime-Chan")
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
        test_url = f"{base_url}{name}/saison1/{lang}/episodes.js"
        response = requests.get(test_url)
        if response.status_code == 200 and response.text.strip():
            available_languages.append(lang)

    return available_languages

def check_seasons(base_url, name, language):
    """Vérifie les saisons, films et OAVs disponibles avec des variantes de numérotation"""
    available_seasons = []
    season_info = {}  # Pour stocker les informations sur chaque saison et ses variantes
    
    season = 1
    while True:
        found_any = False
        
        # Vérifier l'URL standard pour cette saison
        main_url = f"{base_url}{name}/saison{season}/{language}/episodes.js"
        response = requests.get(main_url)
        
        if response.status_code == 200 and response.text.strip():
            print(f"\u2714 Saison {season} trouvée.")
            
            # Initialiser les infos de cette saison
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
        "format": "bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
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

    # Vérification que les liens sont bien définis
    if not (sibnet_links or vidmoly_links):
        print(f"⛔ Aucune vidéo trouvée pour la saison {season}.")
        return  # Si aucun lien n'a été trouvé, on quitte la fonction.

    for link in sibnet_links + vidmoly_links:
        # Afficher le message de chargement animé avec des points entre chaque épisode
        sys.stdout.write("🌐 Chargement")
        sys.stdout.flush()

        # Afficher des points pour l'animation pendant 2 secondes
        for _ in range(3):
            time.sleep(1)
            sys.stdout.write(".")
            sys.stdout.flush()

        sys.stdout.write("\r")  # Efface la ligne de chargement
        sys.stdout.flush()

        # Vérifie si le lien mène à un code HTTP 403 avant de commencer le téléchargement
        if check_http_403(link):
            continue  # Si le code 403 est détecté, on passe à l'épisode suivant

        # Format standard S{season}_E{episode_counter}
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
    
    # Vérifier si des arguments en ligne de commande ont été fournis
    if len(sys.argv) > 1:
        # Si "-h" ou "--help" est fourni, afficher l'aide
        if sys.argv[1].lower() in ["-h", "--help", "help", "/?", "-?"]:
            show_usage()
            return
            
        # Si exactement 2 arguments sont fournis (nom_anime et langage)
        if len(sys.argv) == 3:
            anime_name = sys.argv[1].strip().lower()
            language_input = sys.argv[2].strip().lower()
            
            # Convertir l'entrée en langage en choix correspondant
            if language_input == "vf":
                language_choice = "1"
            elif language_input == "vostfr":
                language_choice = "2"
            else:
                print(f"⛔ Langage '{language_input}' non reconnu. Utilisez 'vf' ou 'vostfr'.")
                show_usage()
                return
        else:
            print("⛔ Nombre d'arguments incorrect.")
            show_usage()
            return
    else:
        # Mode interactif si aucun argument n'est fourni
        anime_name = input("Entrez le nom de l'anime : ").strip().lower()
        language_choice = input("Choisissez la version (1: VF, 2: VOSTFR) : ").strip()
    
    formatted_url_name = format_url_name(anime_name)

    if language_choice == "1":
        available_vf_versions = check_available_languages(base_url, formatted_url_name)
        
        if not available_vf_versions:
            print("⛔ Aucune version VF trouvée. Arrêt du programme.")
            return
        
        if len(available_vf_versions) == 1:
            selected_language = available_vf_versions[0]
        else:
            print("\nVersions VF disponibles :")
            for i, lang in enumerate(available_vf_versions, start=1):
                print(f"{i}. {lang.upper()}")

            # En mode ligne de commande, choisir automatiquement la première version VF disponible
            if len(sys.argv) > 1:
                choice = "1"
                print(f"Mode ligne de commande : Sélection automatique de la version {available_vf_versions[0].upper()}")
            else:
                choice = input("Entrez le numéro de la version souhaitée : ").strip()
                
            if not choice.isdigit() or int(choice) < 1 or int(choice) > len(available_vf_versions):
                print("⛔ Choix invalide. Arrêt du programme.")
                return
            
            selected_language = available_vf_versions[int(choice) - 1]
    else:
        selected_language = "vostfr"

    folder_name = format_folder_name(anime_name, selected_language)

    if not check_disk_space():
        print("⛔ Espace disque insuffisant. Libérez de l'espace et réessayez.")
        exit(1)

    seasons = check_seasons(base_url, formatted_url_name, selected_language)
    
    # Dictionnaire pour suivre le nombre d'épisodes par saison et variante
    episode_counters = {}
    last_processed = {}  # Pour suivre la dernière saison/variante traitée
    
    for season, url, is_variant, variant_num in seasons:
        # Si c'est un film ou un OAV, traiter séparément
        if season in ["film", "oav"]:
            sibnet_links, vidmoly_links = extract_video_links(url)
            if sibnet_links or vidmoly_links:
                download_videos(sibnet_links, vidmoly_links, season, folder_name)
            continue
        
        sibnet_links, vidmoly_links = extract_video_links(url)
        total_episodes = len(sibnet_links) + len(vidmoly_links)
        
        if not (sibnet_links or vidmoly_links):
            print(f"⛔ Aucun épisode trouvé pour {'la Partie ' + str(variant_num) + ' de ' if is_variant else ''}la saison {season}")
            continue
            
        # Déterminer le numéro de l'épisode de départ
        start_episode = 1  # Par défaut, commencer à 1
        
        # Si c'est une variante, vérifier si on a déjà traité la saison principale ou d'autres variantes
        if is_variant:
            if season in last_processed:
                # Continuer depuis le dernier épisode de cette saison
                start_episode = last_processed[season] + 1
            else:
                # Si c'est la première variante mais pas de saison principale, commencer à 1
                start_episode = 1
        else:
            # Si c'est une saison principale, toujours commencer à 1
            start_episode = 1
        
        print(f"♾️ Traitement de {'la Partie ' + str(variant_num) + ' de ' if is_variant else ''}la saison {season}")
        print(f"🔢 Épisodes: {start_episode} à {start_episode + total_episodes - 1}")
        
        download_videos(sibnet_links, vidmoly_links, season, folder_name, start_episode)
        
        # Mettre à jour le compteur pour cette saison
        last_processed[season] = start_episode + total_episodes - 1

if __name__ == "__main__":
    main()
