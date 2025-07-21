import os
import platform
import shutil
import sys
import requests
import re
import time
import importlib.util

# Vérification de la disponibilité de PIL (Python Imaging Library)
pil_available = importlib.util.find_spec("PIL") is not None
if pil_available:
    from PIL import Image, ImageOps
    import io

from yt_dlp import YoutubeDL

class MyLogger:
    """Classe logger personnalisée pour yt-dlp - supprime les messages de debug et warning"""
    def debug(self, msg):
        pass  # Ignore les messages de debug
    
    def warning(self, msg):
        pass  # Ignore les messages d'avertissement
    
    def error(self, msg):
        print(msg)  # Affiche seulement les erreurs

def set_title(title_text):
    """Définit le titre de la fenêtre de terminal selon l'OS"""
    s = platform.system()
    is_termux = s == "Linux" and "ANDROID_STORAGE" in os.environ
    
    if s == "Windows":
        os.system(f"title {title_text}")
    elif s == "Linux" and not is_termux:
        # Séquence d'échappement ANSI pour définir le titre du terminal
        os.system(f'echo -e "\033]0;{title_text}\007"')

# Définit le titre initial de l'application
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
        # Test saison 1
        season_url = f"{base_url}{formatted_url_name}/saison1/{lang}/episodes.js"
        try:
            response = requests.get(season_url, timeout=5)
            if response.status_code == 200 and response.text.strip():
                return True
        except:
            continue
            
        # Test film
        film_url = f"{base_url}{formatted_url_name}/film/{lang}/episodes.js"
        try:
            response = requests.get(film_url, timeout=5)
            if response.status_code == 200 and response.text.strip():
                return True
        except:
            continue
            
        # Test OAV (Original Animation Video)
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
    """
    Calcule le nombre total d'épisodes pour toutes les saisons ou une saison spécifique
    Retourne aussi un dictionnaire avec le total par saison
    """
    total = 0
    season_totals = {}
    
    for season, url, is_variant, variant_num in seasons:
        # Si une saison spécifique est sélectionnée, ignore les autres
        if selected_season is not None and season != selected_season:
            continue
        
        # Extrait les liens pour compter les épisodes
        sibnet_links, vidmoly_links = extract_video_links(url)
        episode_count = len(sibnet_links) + len(vidmoly_links)
        
        # Accumule par saison
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
    """Fonction principale du programme"""
    base_url = "https://anime-sama.fr/catalogue/"
    
    # Gestion des arguments en ligne de commande
    if len(sys.argv) > 1:
        if sys.argv[1].lower() in ["-h", "--help", "help", "/?", "-?"]:
            show_usage()
            return
        
        if len(sys.argv) == 3:
            # Mode avec arguments: nom + langue
            anime_name = normalize_anime_name(sys.argv[1])
            language_input = sys.argv[2].strip().lower()
            anime_name_capitalized = anime_name.title()
            set_title(f"Co-Chan : {anime_name_capitalized}")
            
            # Conversion des langues communes
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
        # Mode interactif: demande à l'utilisateur
        anime_name = normalize_anime_name(input("Entrez le nom de l'anime : "))
        anime_name_capitalized = anime_name.title()
        set_title(f"Co-Chan : {anime_name_capitalized}")
    
    formatted_url_name = format_url_name(anime_name)
    
    # Vérification de l'existence de l'anime
    print(f"🔍 Vérification de l'existence de '{anime_name_capitalized}'...")
    if not check_anime_exists(base_url, formatted_url_name):
        print(f"❌ L'anime '{anime_name_capitalized}' n'existe pas ou essayez avec le nom en japonais. ")
        print("   Ni en version française (VF), ni en version sous-titrée (VOSTFR).")
        print("   Vérifiez l'orthographe ou essayez avec un autre nom.")
        print("\n⏰ Fermeture automatique dans 5 secondes...")
        time.sleep(5)
        exit(1)
    
    print(f"✅ Anime '{anime_name_capitalized}' trouvé !")
    
    # Vérification des langues disponibles
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
    
    # Vérification de l'espace disque
    if not check_disk_space():
        print("⛔ Espace disque insuffisant. Libérez de l'espace et réessayez.")
        exit(1)
    
    # Découverte des saisons/films/OAV disponibles
    seasons = check_seasons(base_url, formatted_url_name, selected_language)
    
    # Demande du point de départ
    start_season, start_episode = ask_for_starting_point()
    
    # Calcul du total des épisodes
    _, season_totals = calculate_total_episodes(seasons)
    
    global_episode_counter = 1
    
    # Groupement des saisons et variantes
    season_groups = {}
    for season, url, is_variant, variant_num in seasons:
        if season not in season_groups:
            season_groups[season] = []
        season_groups[season].append((url, is_variant, variant_num))
    
    # Traitement de chaque saison dans l'ordre
    for season_key in sorted(season_groups.keys(), key=custom_sort_key):
        season_parts = season_groups[season_key]
        
        # Filtrage selon le point de départ demandé
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
        
        # Tri des parties de saison (principale puis variantes)
        season_parts.sort(key=lambda x: (x[1], x[2]))
        
        # Traitement de chaque partie de saison
        for url, is_variant, variant_num in season_parts:
            sibnet_links, vidmoly_links = extract_video_links(url)
            
            if not (sibnet_links or vidmoly_links):
                continue
            
            current_links = sibnet_links + vidmoly_links
            
            # Gestion du point de départ spécifique
            if start_season != 0 and season_key == start_season and global_episode_counter == 1:
                if start_episode > 1:
                    skip_episodes = start_episode - 1
                    if skip_episodes < len(current_links):
                        # Saute les épisodes précédents
                        current_links = current_links[skip_episodes:]
                        global_episode_counter += skip_episodes
                        season_episode_counter += skip_episodes
                    else:
                        # Tous les épisodes de cette partie sont à ignorer
                        continue
            
            # Affichage du traitement en cours
            if is_variant:
                print(f"♾️ Traitement de la Partie {variant_num} de la saison {season_key}")
            else:
                print(f"♾️ Traitement de la saison {season_key}")
            
            # Téléchargement de chaque épisode
            for link in current_links:
                # Animation de chargement avec points
                sys.stdout.write("🌐 Chargement")
                sys.stdout.flush()
                for _ in range(3):
                    time.sleep(1)
                    sys.stdout.write(".")
                    sys.stdout.flush()
                sys.stdout.write("\r")
                sys.stdout.flush()
                
                # Vérification du statut 403 (bannissement temporaire)
                if check_http_403(link):
                    continue
                
                # Création du dossier de téléchargement
                download_dir = os.path.join(get_download_path(), folder_name)
                os.makedirs(download_dir, exist_ok=True)
                
                # Nom du fichier final
                filename = os.path.join(download_dir, f"s{season_key}_e{global_episode_counter}.mp4")
                
                # Lancement du téléchargement
                download_video(link, filename, season_key, global_episode_counter, total_episodes_in_season)
                
                # Incrémentation des compteurs
                global_episode_counter += 1
                season_episode_counter += 1

# Point d'entrée du programme
if __name__ == "__main__":
    main()
