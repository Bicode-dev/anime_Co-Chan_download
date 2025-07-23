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
        print(msg)  # Affiche seulement les erreurs

def set_title(title_text):
    s = platform.system()
    is_termux = s == "Linux" and "ANDROID_STORAGE" in os.environ
    
    if s == "Windows":
        os.system(f"title {title_text}")
    elif s == "Linux" and not is_termux:
        os.system(f'echo -e "\033]0;{title_text}\007"')

set_title("Co-Chan")

def check_disk_space(min_gb=1):
    """Vérifie l'espace disque disponible (minimum 1GB par défaut)"""
    s = platform.system()
    
    if s == "Windows":
        # Vérifie l'espace sur le disque C:
        total, used, free = shutil.disk_usage("C:\\")
        free_space_gb = free / (1024**3)  # Conversion en GB
        
    elif s == "Linux" and "ANDROID_STORAGE" in os.environ:
        # Spécifique pour Android/Termux
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
        # Pour les systèmes Unix/Linux classiques
        statvfs = os.statvfs("/")
        free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
    
    return free_space_gb >= min_gb

def progress_hook(d, season, episode, max_episode):
    """Affiche la progression du téléchargement avec yt-dlp"""
    if d["status"] == "downloading":
        percent = d["_percent_str"].strip()
        # Affiche la progression en temps réel sur la même ligne
        sys.stdout.write(f"\r🔄 [S{season} E{episode}/{max_episode}] {percent} complet")
        sys.stdout.flush()
    elif d["status"] == "finished":
        # Confirmation de fin de téléchargement
        sys.stdout.write(f"\r✅ [S{season} E{episode}/{max_episode}] Téléchargement terminé !\n")
        sys.stdout.flush()

def get_download_path():
    """Détermine le chemin de téléchargement selon l'OS"""
    if platform.system() == "Windows":
        return os.path.join(os.getcwd())  # Répertoire courant
    elif platform.system() == "Linux" and "ANDROID_STORAGE" in os.environ:
        return "/storage/emulated/0/Download/anime"  # Dossier Download Android
    else:
        print("Ce script ne fonctionne que sous Windows ou Android.")
        exit(1)

def format_url_name(name):
    """Formate le nom pour l'URL (minuscules, tirets au lieu d'espaces)"""
    return name.lower().replace("'", "").replace(" ", "-")

def format_folder_name(name, language):
    """Formate le nom du dossier avec la langue en majuscules"""
    return f"{' '.join(word.capitalize() for word in name.split())} {language.upper()}"

def normalize_anime_name(name):
    """
    Normalise le nom de l'anime en supprimant les espaces multiples, 
    tabulations et sauts de ligne
    Exemple: "one      piece\n\t" devient "one piece"
    """
    return ' '.join(name.strip().split()).lower()

def check_anime_exists(base_url, formatted_url_name):
    """
    Vérifie si l'anime existe en testant différentes langues et types de contenu
    Teste les saisons, films et OAV dans plusieurs langues
    """
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
    """Vérifie toutes les langues disponibles pour un anime donné"""
    all_languages = ["vf", "va", "vkr", "vcn", "vqc", "vf1", "vf2", "vf3", "vf4", "vf5"]
    available_languages = []
    
    for lang in all_languages:
        # Teste à la fois les saisons et les films
        season_url = f"{base_url}{name}/saison1/{lang}/episodes.js"
        season_response = requests.get(season_url)
        
        film_url = f"{base_url}{name}/film/{lang}/episodes.js"
        film_response = requests.get(film_url)
        
        # Si l'une des deux URL répond positivement, la langue est disponible
        if ((season_response.status_code == 200 and season_response.text.strip()) or 
            (film_response.status_code == 200 and film_response.text.strip())):
            available_languages.append(lang)
    
    return available_languages

def check_seasons(base_url, name, language):
    """
    Découvre toutes les saisons disponibles, leurs variantes, films et OAV
    Retourne une liste des contenus disponibles
    """
    available_seasons = []
    season_info = {}
    season = 1
    consecutive_not_found = 0
    
    # Recherche des saisons principales et leurs variantes
    while consecutive_not_found < 3:  # Arrête après 3 saisons consécutives non trouvées
        found_any = False
        
        # Teste la saison principale
        main_url = f"{base_url}{name}/saison{season}/{language}/episodes.js"
        response = requests.get(main_url)
        
        if response.status_code == 200 and response.text.strip():
            print(f"✔ Saison {season} trouvée.")
            season_info[season] = {'main_url': main_url, 'variants': [], 'has_main': True}
            found_any = True
            consecutive_not_found = 0
        else:
            season_info[season] = {'main_url': None, 'variants': [], 'has_main': False}
        
        # Recherche des variantes de saison (ex: saison1-2, saison1-3, etc.)
        variant_consecutive_not_found = 0
        i = 1
        while variant_consecutive_not_found < 3:
            variant_url = f"{base_url}{name}/saison{season}-{i}/{language}/episodes.js"
            response = requests.get(variant_url)
            
            if response.status_code == 200 and response.text.strip():
                print(f"✔ Saison {season}-{i} trouvée.")
                season_info[season]['variants'].append((i, variant_url))
                found_any = True
                consecutive_not_found = 0
                variant_consecutive_not_found = 0
            else:
                variant_consecutive_not_found += 1
            i += 1
        
        if not found_any:
            consecutive_not_found += 1
            if season in season_info:
                del season_info[season]  # Supprime les saisons vides
        
        season += 1
    
    # Vérification des films
    film_url = f"{base_url}{name}/film/{language}/episodes.js"
    response = requests.get(film_url)
    if response.status_code == 200 and response.text.strip():
        print(f"✔ Film trouvé.")
        season_info['film'] = {'main_url': film_url, 'variants': [], 'has_main': True}
    
    # Vérification des OAV
    oav_url = f"{base_url}{name}/oav/{language}/episodes.js"
    response = requests.get(oav_url)
    if response.status_code == 200 and response.text.strip():
        print(f"✔ OAV trouvé.")
        season_info['oav'] = {'main_url': oav_url, 'variants': [], 'has_main': True}
    
    # Construction de la liste finale
    for season_num, info in season_info.items():
        if info['has_main']:
            available_seasons.append((season_num, info['main_url'], False, 0))
        
        for variant_num, variant_url in sorted(info['variants']):
            available_seasons.append((season_num, variant_url, True, variant_num))
    
    return available_seasons
def find_last_downloaded_episode(folder_path):
    """Trouve le dernier épisode téléchargé dans le dossier"""
    if not os.path.exists(folder_path):
        return None, None
    
    files = os.listdir(folder_path)
    episodes = []
    
    # Pattern pour matcher les fichiers d'épisodes
    pattern = re.compile(r's(\w+)_e(\d+)\.mp4')
    
    for file in files:
        match = pattern.match(file)
        if match:
            season = match.group(1)
            episode = int(match.group(2))
            
            # Convertir les saisons numériques en int pour le tri
            if season.isdigit():
                season = int(season)
            
            episodes.append((season, episode))
    
    if not episodes:
        return None, None
    
    # Trier les épisodes (saisons numériques d'abord, puis film, puis oav)
    def sort_key(x):
        season, episode = x
        if isinstance(season, int):
            return (0, season, episode)
        elif season == "film":
            return (1, 0, episode)
        elif season == "oav":
            return (2, 0, episode)
        else:
            return (3, str(season), episode)
    
    episodes.sort(key=sort_key, reverse=True)
    return episodes[0]  # Retourne le dernier épisode

def get_total_episodes_for_season(seasons, target_season):
    """Récupère le nombre total d'épisodes pour une saison donnée"""
    total_episodes = 0
    
    for season, url, is_variant, variant_num in seasons:
        if season == target_season:
            sibnet_links, vidmoly_links = extract_video_links(url)
            total_episodes += len(sibnet_links) + len(vidmoly_links)
    
    return total_episodes

def ask_for_starting_point(folder_name, seasons):
    """Demande le point de départ avec détection automatique et vérification"""
    download_dir = os.path.join(get_download_path(), folder_name)
    last_season, last_episode = find_last_downloaded_episode(download_dir)
    
    if last_season is not None and last_episode is not None:
        print(f"📁 Dernier épisode détecté : S{last_season} E{last_episode}")
        
        # Vérifier le nombre total d'épisodes pour cette saison
        total_episodes_in_season = get_total_episodes_for_season(seasons, last_season)
        
        if total_episodes_in_season > 0 and last_episode >= total_episodes_in_season:
            print(f"✅ Tous les épisodes de la saison {last_season} sont déjà téléchargés ({last_episode}/{total_episodes_in_season})")
            
            # Vérifier s'il y a une saison suivante
            season_keys = []
            for season, _, _, _ in seasons:
                if season not in season_keys:
                    season_keys.append(season)
            
            # Trier les saisons
            def custom_sort_key(x):
                if isinstance(x, int):
                    return (0, x)
                elif x == "film":
                    return (1, 0)
                elif x == "oav":
                    return (2, 0)
                else:
                    return (3, str(x))
            
            season_keys.sort(key=custom_sort_key)
            current_season_index = None
            
            try:
                current_season_index = season_keys.index(last_season)
            except ValueError:
                pass
            
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
            next_episode = last_episode + 1
            choice = input(f"Continuer à partir de S{last_season} E{next_episode} ? (o/n): ").strip().lower()
            
            if choice in ['o', 'oui', 'y', 'yes', '']:
                print(f"➡️ Reprise à partir de S{last_season} E{next_episode}")
                return last_season, next_episode
    
    # Si pas de détection ou refus de continuer
    choice = input("Télécharger tous les épisodes ? (o/n): ").strip().lower()
    
    if choice in ['o', 'oui', 'y', 'yes', '']:
        print("➡️ Téléchargement de tous les épisodes")
        return 0, 0
    
    # Demander saison et épisode spécifiques
    while True:
        try:
            season_input = input("Numéro de saison (ou 'film'/'oav'): ").strip().lower()
            
            if season_input == "film":
                season = "film"
            elif season_input == "oav":
                season = "oav"
            elif season_input.isdigit():
                season = int(season_input)
            else:
                print("⚠️ Saison invalide. Utilisez un numéro, 'film' ou 'oav'")
                continue
            
            episode = int(input("Numéro d'épisode: ").strip())
            
            print(f"➡️ Téléchargement à partir de S{season} E{episode}")
            return season, episode
            
        except ValueError:
            print("⚠️ Veuillez entrer des nombres valides")

def check_http_403(url):
    """
    Vérifie si l'URL renvoie un code 403 (Interdit)
    Implémente un système de retry en cas de bannissement temporaire
    """
    attempts = 0
    
    while attempts < 5:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 403:
                print(f"⛔ Tentative {attempts+1} échouée : Sibnet a renvoyé un code 403. Nouvelle tentatives veuillez patienter.")
                time.sleep(10)  # Attente avant nouvelle tentative
                attempts += 1
            else:
                return False  # Pas de problème 403
        except requests.exceptions.RequestException as e:
            print(f"⛔ Erreur de connexion : {e}")
            return False
    
    # Après 5 tentatives échouées
    print("⛔ Sibnet vous a temporairement banni, veuillez réessayer dans un maximum de 2 jours.")
    time.sleep(20)
    return True

def get_anime_image(anime_name, folder_name):
    """
    Télécharge l'image de couverture de l'anime depuis l'API Jikan (MyAnimeList)
    Crée une icône de dossier personnalisée pour Windows
    """
    try:
        # Recherche de l'anime via l'API Jikan
        url_name = anime_name.replace(" ", "+")
        url = f"https://api.jikan.moe/v4/anime?q={url_name}&limit=1"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if not data["data"]:
            return  # Aucun résultat trouvé
        
        anime = data["data"][0]
        image_url = anime["images"]["jpg"]["large_image_url"]
        
        # Téléchargement de l'image
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        image_data = image_response.content
        
        # Sauvegarde en tant que cover.jpg
        jpg_path = os.path.join(folder_name, "cover.jpg")
        with open(jpg_path, 'wb') as f:
            f.write(image_data)
        
        # Création d'une icône de dossier Windows (.ico)
        ico_path = os.path.join(folder_name, "folder.ico")
        image = Image.open(io.BytesIO(image_data))
        
        # Redimensionnement en carré de 256x256 pixels
        size = 256
        square_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        width, height = image.size
        
        # Calcul du redimensionnement en gardant les proportions
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
        
        # Sauvegarde de l'icône
        square_img.save(ico_path, format='ICO', sizes=[(size, size)])
        
        # Masquage de l'icône sur Windows
        if os.name == 'nt':
            os.system(f'attrib +h "{ico_path}"')
        
        # Création du fichier desktop.ini pour personnaliser l'icône du dossier
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
        
        # Application des attributs Windows pour l'icône personnalisée
        if os.name == 'nt':
            os.system(f'attrib +s "{folder_name}"')  # Marque le dossier comme système
            os.system(f'attrib +h +s "{desktop_ini_path}"')  # Masque desktop.ini
            
    except Exception:
        pass  # Ignore silencieusement les erreurs d'image

def extract_video_links(url):
    """
    Extrait les liens vidéo Sibnet et Vidmoly depuis une page web
    Utilise des expressions régulières pour trouver les liens
    """
    response = requests.get(url)
    if response.status_code != 200:
        return [], []
    
    # Patterns pour extraire les liens vidéo
    sibnet_pattern = r"(https://video\.sibnet\.ru/shell\.php\?videoid=\d+)"
    vidmoly_pattern = r"(https://vidmoly\.to/embed/\w+)"
    
    # Recherche des liens dans le HTML
    sibnet_links = re.findall(sibnet_pattern, response.text)
    vidmoly_links = re.findall(vidmoly_pattern, response.text)
    
    return sibnet_links, vidmoly_links

def download_video(link, filename, season, episode, max_episode):
    """
    Télécharge une vidéo en utilisant yt-dlp avec gestion des erreurs
    """
    # Vérification de l'espace disque avant téléchargement
    if not check_disk_space():
        print(f"⛔ Espace disque insuffisant. Arrêt du téléchargement pour [S{season} E{episode}/{max_episode}].")
        return
    
    # Configuration de yt-dlp
    ydl_opts = {
        "outtmpl": filename,  # Nom du fichier de sortie
        "quiet": False,
        "ignoreerrors": True,  # Continue même en cas d'erreurs
        "progress_hooks": [lambda d: progress_hook(d, season, episode, max_episode)],
        "no_warnings": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",  # Meilleure qualité MP4
        "merge_output_format": "mp4",  # Force la sortie en MP4
        "logger": MyLogger(),  # Utilise notre logger personnalisé
        "socket_timeout": 60,  # Timeout de 60 secondes
        "retries": 15  # 15 tentatives en cas d'échec
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
    except Exception as e:
        # Nettoie l'affichage et affiche l'erreur
        sys.stdout.write("\r")
        sys.stdout.flush()
        print(f"⛔ Erreur lors du téléchargement: {e}")
        return

def ask_for_starting_point():
    """
    Demande à l'utilisateur de spécifier un point de départ pour le téléchargement
    Supporte les formats: s1_e5, film_e1, oav_e1 ou 0 pour tout télécharger
    """
    while True:
        starting_point = input("Spécifiez un point de départ (exemple: s1_e5, film_e1, oav_e1) ou 0 pour tout télécharger: ").strip().lower()
        
        if starting_point == "0":
            print("➡️ Téléchargement de tous les épisodes de toutes les saisons")
            return 0, 0
        
        # Patterns pour analyser l'entrée utilisateur
        season_pattern = re.compile(r's(\d+)_e(\d+)')
        season_match = season_pattern.match(starting_point)
        
        film_pattern = re.compile(r'film_e(\d+)')
        film_match = film_pattern.match(starting_point)
        
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

def calculate_total_episodes(seasons, selected_season=None):
    total = 0
    season_totals = {}
    
    for season, url, is_variant, variant_num in seasons:
        if selected_season is not None and season != selected_season:
            continue
        
        sibnet_links, vidmoly_links = extract_video_links(url)
        episode_count = len(sibnet_links) + len(vidmoly_links)
        
        if season not in season_totals:
            season_totals[season] = 0
        season_totals[season] += episode_count
        total += episode_count
    
    return total, season_totals


def download_videos(sibnet_links, vidmoly_links, season, folder_name, global_episode_counter, season_episode_counter, total_episodes_in_season):
    """
    FONCTION ACTUELLEMENT INUTILISÉE - Remplacée par la logique dans main()
    Télécharge tous les épisodes d'une saison
    """
    download_dir = os.path.join(get_download_path(), folder_name)
    os.makedirs(download_dir, exist_ok=True)
    
    # Récupère le nom de l'anime pour l'image
    anime_name = folder_name.split(" ")[:-1]
    anime_name = " ".join(anime_name)
    get_anime_image(anime_name, download_dir)
    
    print(f"📥 Téléchargement [S{season}] : {download_dir}")
    
    if not (sibnet_links or vidmoly_links):
        print(f"⛔ Aucune vidéo trouvée pour la saison {season}.")
        return global_episode_counter
    
    all_links = sibnet_links + vidmoly_links
    
    for i, link in enumerate(all_links):
        # Animation de chargement
        sys.stdout.write("🌐 Chargement")
        sys.stdout.flush()
        for _ in range(3):
            time.sleep(1)
            sys.stdout.write(".")
            sys.stdout.flush()
        sys.stdout.write("\r")
        sys.stdout.flush()
        
        # Vérification du ban 403
        if check_http_403(link):
            continue
        
        # Téléchargement
        filename = os.path.join(download_dir, f"s{season}_e{global_episode_counter}.mp4")
        download_video(link, filename, season, global_episode_counter, total_episodes_in_season)
        global_episode_counter += 1
    
    return global_episode_counter

def custom_sort_key(x):
    """
    Clé de tri personnalisée pour ordonner les saisons
    Ordre: saisons numériques, puis films, puis OAV, puis autres
    """
    if isinstance(x, int):
        return (0, x)  # Saisons numériques en premier
    elif x == "film":
        return (1, 0)  # Films en deuxième
    elif x == "oav":
        return (2, 0)  # OAV en troisième
    else:
        return (3, str(x))  # Autres à la fin

def show_usage():
    """Affiche l'aide d'utilisation du script"""
    print("Usage:")
    print("  python script.py <nom_anime> <langue>")
    print("  python script.py -h|--help|help|/?|-?")
    print()
    print("Exemples:")
    print("  python script.py \"one piece\" vf")
    print("  python script.py \"naruto\" vostfr")

def main():
    base_url = "https://anime-sama.fr/catalogue/"
    
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
    
    seasons = check_seasons(base_url, formatted_url_name, selected_language)
    
    # Fonction modifiée avec passage des seasons
    start_season, start_episode = ask_for_starting_point(folder_name, seasons)
    
    _, season_totals = calculate_total_episodes(seasons)
    
    global_episode_counter = 1
    
    season_groups = {}
    for season, url, is_variant, variant_num in seasons:
        if season not in season_groups:
            season_groups[season] = []
        season_groups[season].append((url, is_variant, variant_num))
    
    for season_key in sorted(season_groups.keys(), key=custom_sort_key):
        season_parts = season_groups[season_key]
        
        if start_season != 0:
            if start_season == "film" and season_key != "film":
                continue
            elif start_season == "oav" and season_key != "oav":
                continue
            elif isinstance(start_season, int) and season_key in ["film", "oav"]:
                continue
            elif isinstance(start_season, int) and isinstance(season_key, int) and season_key < start_season:
                continue
        
        total_episodes_in_season = season_totals.get(season_key, 0)
        season_episode_counter = 1
        
        season_parts.sort(key=lambda x: (x[1], x[2]))
        
        for url, is_variant, variant_num in season_parts:
            sibnet_links, vidmoly_links = extract_video_links(url)
            
            if not (sibnet_links or vidmoly_links):
                continue
            
            current_links = sibnet_links + vidmoly_links
            
            if start_season != 0 and season_key == start_season and global_episode_counter == 1:
                if start_episode > 1:
                    skip_episodes = start_episode - 1
                    if skip_episodes < len(current_links):
                        current_links = current_links[skip_episodes:]
                        global_episode_counter += skip_episodes
                        season_episode_counter += skip_episodes
                    else:
                        continue
            
            if is_variant:
                print(f"♾️ Traitement de la Partie {variant_num} de la saison {season_key}")
            else:
                print(f"♾️ Traitement de la saison {season_key}")
            
            for link in current_links:
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
                
                # Téléchargement de l'image seulement au premier épisode
                if global_episode_counter == 1 or (start_episode > 1 and season_episode_counter == start_episode):
                    get_anime_image(anime_name_capitalized, download_dir)
                
                filename = os.path.join(download_dir, f"s{season_key}_e{global_episode_counter}.mp4")
                
                download_video(link, filename, season_key, global_episode_counter, total_episodes_in_season)
                
                global_episode_counter += 1
                season_episode_counter += 1

if __name__ == "__main__":
    main()
