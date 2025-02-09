import os
import platform
import shutil
import sys
import requests
import re
from youtube_dl import YoutubeDL

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

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

def progress_hook(d, season, episode, total_episodes):
    """Affiche la progression du téléchargement"""
    if d["status"] == "downloading":
        percent = d["_percent_str"].strip()
        sys.stdout.write(f"\r[S{season} E{episode}/{total_episodes}] {percent} complet")
        sys.stdout.flush()
    elif d["status"] == "finished":
        sys.stdout.write(f"\r✅ [S{season} E{episode}/{total_episodes}] Téléchargement terminé !\n")
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
    """Vérifie les saisons et films disponibles"""
    available_seasons = []
    season = 1

    while True:
        url = f"{base_url}{name}/saison{season}/{language}/episodes.js"
        response = requests.get(url)

        if response.status_code == 200 and response.text.strip():
            print(f"\u2714 Saison {season} trouvée: {url}")
            available_seasons.append((season, url))
        else:
            break
        season += 1

    film_url = f"{base_url}{name}/film/{language}/episodes.js"
    response = requests.get(film_url)

    if response.status_code == 200 and response.text.strip():
        print(f"\u2714 Film trouvé: {film_url}")
        available_seasons.append(("film", film_url))

    return available_seasons

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

def download_video(link, filename, season, episode, total_episodes):
    """Télécharge une vidéo en affichant la progression"""
    if not check_disk_space():
        print(f"⛔ Espace disque insuffisant. Arrêt du téléchargement pour [S{season} E{episode}/{total_episodes}].")
        return

    ydl_opts = {
        "outtmpl": filename,
        "quiet": True,
        "ignoreerrors": True,
        "progress_hooks": [lambda d: progress_hook(d, season, episode, total_episodes)],
        "no_warnings": True,
        "logger": MyLogger(),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "merge_output_format": "mp4",
        "postprocessors": [],
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])

def download_videos(sibnet_links, vidmoly_links, season, folder_name):
    """Télécharge toutes les vidéos d'une saison"""
    download_dir = os.path.join(get_download_path(), folder_name)
    os.makedirs(download_dir, exist_ok=True)

    total_episodes = len(sibnet_links) + len(vidmoly_links)
    episode_counter = 1

    for link in sibnet_links + vidmoly_links:
        filename = os.path.join(download_dir, f"{'film' if season == 'film' else f's{season}_e{episode_counter}'}.mp4")
        print(f"📥 Téléchargement : {filename} depuis {link}")
        download_video(link, filename, season, episode_counter, total_episodes)
        episode_counter += 1

def main():
    base_url = "https://anime-sama.fr/catalogue/"
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
    
    for season, url in seasons:
        sibnet_links, vidmoly_links = extract_video_links(url)
        if sibnet_links or vidmoly_links:
            download_videos(sibnet_links, vidmoly_links, season, folder_name)

if __name__ == "__main__":
    main()
