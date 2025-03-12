import os
import platform
import shutil
import sys
import requests
import re
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from yt_dlp import YoutubeDL
import io
from contextlib import redirect_stdout

class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = io.StringIO()

    def write(self, string):
        self.buffer.write(string)
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)

    def flush(self):
        self.buffer.flush()

class AnimeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Anime Downloader")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        self.root.configure(bg="#f0f0f0")
        self.download_path = os.getcwd()
        self.running = False
        self.download_thread = None
        self.last_log_message = None  # Ajout d'un attribut pour le dernier message de log

        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TButton', background='#4CAF50', foreground='black', font=('Helvetica', 10, 'bold'))
        self.style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 10))
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TProgressbar', troughcolor='#f0f0f0', background='#4CAF50')

        self.create_widgets()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Input frame
        input_frame = ttk.Frame(main_frame, padding="5")
        input_frame.pack(fill=tk.X, pady=5)

        # Anime name entry
        ttk.Label(input_frame, text="Nom de l'anime:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.anime_name_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.anime_name_var, width=40).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Language selection
        ttk.Label(input_frame, text="Version:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.language_var = tk.StringVar(value="vf")
        ttk.Radiobutton(input_frame, text="VF", variable=self.language_var, value="vf").grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(input_frame, text="VOSTFR", variable=self.language_var, value="vostfr").grid(row=1, column=1, sticky=tk.W, padx=95)

        # Download path selection
        ttk.Label(input_frame, text="Dossier de téléchargement:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.download_path_var = tk.StringVar(value=self.download_path)
        ttk.Entry(input_frame, textvariable=self.download_path_var, width=40).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(input_frame, text="Parcourir", command=self.browse_directory).grid(row=2, column=2, padx=5, pady=5)

        # Action buttons
        button_frame = ttk.Frame(main_frame, padding="5")
        button_frame.pack(fill=tk.X, pady=5)

        self.search_button = ttk.Button(button_frame, text="Rechercher", command=self.search_anime)
        self.search_button.pack(side=tk.LEFT, padx=5)

        self.download_button = ttk.Button(button_frame, text="Télécharger", command=self.start_download, state=tk.DISABLED)
        self.download_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Annuler", command=self.cancel_download, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        # Progress bar
        progress_frame = ttk.Frame(main_frame, padding="5")
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

        # Label for progress message
        self.progress_label = ttk.Label(progress_frame, text="", background="#f0f0f0")
        self.progress_label.pack(pady=5)

        # Season selection
        self.season_frame = ttk.LabelFrame(main_frame, text="Saisons disponibles", padding="5")
        self.season_frame.pack(fill=tk.X, pady=5)
        
        self.season_vars = []
        self.season_checkboxes = []

        # Console output
        console_frame = ttk.LabelFrame(main_frame, text="Console", padding="5")
        console_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.console = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, height=15)
        self.console.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.console.config(state=tk.DISABLED)

        # Redirect stdout to our console
        self.stdout_redirect = RedirectText(self.console)
        sys.stdout = self.stdout_redirect

        # Status bar
        self.status_var = tk.StringVar(value="Prêt")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.download_path)
        if directory:
            self.download_path = directory
            self.download_path_var.set(directory)

    def log(self, message):
        self.console.config(state=tk.NORMAL)
        
        # Si un message précédent existe, le remplacer
        if self.last_log_message is not None:
            # Supprimer la dernière ligne
            self.console.delete('end-1c linestart', 'end-1c lineend')
        
        # Insérer le nouveau message
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)
        
        # Mettre à jour le dernier message
        self.last_log_message = message
        self.root.update_idletasks()

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def check_disk_space(self, min_gb=1):
        """ Vérifie si l'espace disque disponible est supérieur à 1 Go """
        try:
            total, used, free = shutil.disk_usage(self.download_path)
            free_space_gb = free / (1024 ** 3)
            return free_space_gb >= min_gb
        except Exception as e:
            self.log(f"Erreur lors de la vérification de l'espace disque: {e}")
            return False

    def format_url_name(self, name):
        """Format URL : suppression des apostrophes, remplacement des espaces par des tirets"""
        return name.lower().replace("'", "").replace(" ", "-")

    def format_folder_name(self, name, language):
        """Format du dossier de téléchargement"""
        return f"{name.lower()} {language.upper()}"

    def check_available_languages(self, base_url, name):
        """ Vérifie les versions VF disponibles """
        vf_versions = ["vf"] + [f"vf{i}" for i in range(1, 6)]
        available_languages = []

        for lang in vf_versions:
            test_url = f"{base_url}{name}/saison1/{lang}/episodes.js"
            response = requests.get(test_url)
            if response.status_code == 200 and response.text.strip():
                available_languages.append(lang)

        return available_languages

    def check_seasons(self, base_url, name, language):
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
                self.log(f"\u2714 Saison {season} trouvée: {main_url}")
                
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
                    self.log(f"\u2714 Saison {season}-{i} trouvée: {variant_url}")
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
            self.log(f"\u2714 Film trouvé: {film_url}")
            season_info['film'] = {
                'main_url': film_url,
                'variants': [],
                'has_main': True
            }
        
        # Vérification des OAVs
        oav_url = f"{base_url}{name}/oav/{language}/episodes.js"
        response = requests.get(oav_url)
        if response.status_code == 200 and response.text.strip():
            self.log(f"\u2714 OAV trouvé: {oav_url}")
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

    def extract_video_links(self, url):
        """Extrait les liens vidéo Sibnet et Vidmoly"""
        response = requests.get(url)
        
        if response.status_code != 200:
            return [], []

        sibnet_pattern = r"(https://video\.sibnet\.ru/shell\.php\?videoid=\d+)"
        vidmoly_pattern = r"(https://vidmoly\.to/embed/\w+)"

        sibnet_links = re.findall(sibnet_pattern, response.text)
        vidmoly_links = re.findall(vidmoly_pattern, response.text)

        return sibnet_links, vidmoly_links

    def check_http_403(self, url):
        """Vérifie si l'URL retourne un code HTTP 403 avec 5 tentatives"""
        attempts = 0
        while attempts < 5:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 403:
                    self.log(f"⛔ Tentative {attempts + 1} échouée : Sibnet a renvoyé un code 403. Nouvelle tentative, veuillez patienter.")
                    time.sleep(10)  # Attente de 10 secondes avant de réessayer
                    attempts += 1
                else:
                    return False
            except requests.exceptions.RequestException as e:
                self.log(f"⛔ Erreur de connexion : {e}")
                return False

        # Après 5 tentatives infructueuses, afficher un message de bannissement
        self.log("⛔ Sibnet vous a temporairement banni, veuillez réessayer dans un maximum de 2 jours.")
        return True

    def progress_hook(self, d, season, episode, max_episode):
        """Affiche la progression du téléchargement"""
        if d["status"] == "downloading":
            percent = d["_percent_str"].strip()
            self.update_status(f"🔄 [S{season} E{episode}/{max_episode}] {percent} complet")
            self.progress_label.config(text=f"🔄 [S{season} E{episode}/{max_episode}] {percent} complet")  # Mettre à jour le label
        elif d["status"] == "finished":
            self.log(f"✅ [S{season} E{episode}/{max_episode}] Téléchargement terminé !")
            self.progress_label.config(text="")  # Effacer le message de progression

    def download_video(self, link, filename, season, episode, max_episode):
        """Télécharge une vidéo en affichant la progression"""
        if not self.check_disk_space():
            self.log(f"⛔ Espace disque insuffisant. Arrêt du téléchargement pour [S{season} E{episode}/{max_episode}].")
            return

        class MyLogger(object):
            def __init__(self, gui):
                self.gui = gui
                
            def debug(self, msg):
                pass

            def warning(self, msg):
                pass

            def error(self, msg):
                self.gui.log(msg)

        ydl_opts = {
            "outtmpl": filename,
            "quiet": False,
            "ignoreerrors": True,
            "progress_hooks": [lambda d: self.progress_hook(d, season, episode, max_episode)],
            "no_warnings": True,
            "format": "bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "merge_output_format": "mp4",
            "logger": MyLogger(self),
            "socket_timeout": 60,  # Augmenter le délai d'attente avant un timeout (en secondes)
            "retries": 15,  # Nombre de tentatives en cas d'échec
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])
        except Exception as e:
            self.log(f"⛔ Erreur lors du téléchargement: {e}")
            return

    def download_videos(self, sibnet_links, vidmoly_links, season, folder_name, current_episode=1):
        """Télécharge toutes les vidéos d'une saison"""
        if not self.running:
            return
            
        download_dir = os.path.join(self.download_path, folder_name)
        os.makedirs(download_dir, exist_ok=True)

        total_episodes = len(sibnet_links) + len(vidmoly_links)
        max_episode = current_episode + total_episodes - 1  # Calculer le dernier épisode
        episode_counter = current_episode

        self.log(f"📥 Téléchargement [S{season}] : {download_dir} (à partir de l'épisode {episode_counter} jusqu'à {max_episode})")

        # Vérification que les liens sont bien définis
        if not (sibnet_links or vidmoly_links):
            self.log(f"⛔ Aucune vidéo trouvée pour la saison {season}.")
            return  # Si aucun lien n'a été trouvé, on quitte la fonction.

        for link in sibnet_links + vidmoly_links:
            if not self.running:
                self.log("⛔ Téléchargement annulé par l'utilisateur.")
                return
                
            # Afficher le message de chargement
            self.update_status(f"🌐 Chargement de l'épisode {episode_counter}...")

            # Vérifie si le lien mène à un code HTTP 403 avant de commencer le téléchargement
            if self.check_http_403(link):
                continue  # Si le code 403 est détecté, on passe à l'épisode suivant

            # Format standard S{season}_E{episode_counter}
            filename = os.path.join(download_dir, f"s{season}_e{episode_counter}.mp4")
            
            self.download_video(link, filename, season, episode_counter, max_episode)
            episode_counter += 1

    def search_anime(self):
        """Recherche les saisons disponibles pour l'anime"""
        anime_name = self.anime_name_var.get().strip()
        if not anime_name:
            messagebox.showerror("Erreur", "Veuillez entrer un nom d'anime")
            return

        # Effacer la console avant de commencer la recherche
        self.console.config(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)  # Effacer tout le contenu de la console
        self.console.config(state=tk.DISABLED)

        self.progress_bar.start()
        self.search_button.config(state=tk.DISABLED)
        self.update_status("Recherche en cours...")
        
        # Effacer les anciennes checkboxes
        for checkbox in self.season_checkboxes:
            checkbox.destroy()
        self.season_vars.clear()
        self.season_checkboxes.clear()
        
        def search_thread():
            base_url = "https://anime-sama.fr/catalogue/"
            formatted_url_name = self.format_url_name(anime_name)
            
            selected_language = self.language_var.get()
            
            # Si VF est sélectionné, vérifier les versions disponibles
            if selected_language == "vf":
                available_vf_versions = self.check_available_languages(base_url, formatted_url_name)
                
                if not available_vf_versions:
                    self.root.after(0, lambda: messagebox.showerror("Erreur", "Aucune version VF trouvée pour cet anime."))
                    self.root.after(0, lambda: self.update_status("Recherche terminée. Aucune version VF trouvée."))
                    self.root.after(0, lambda: self.search_button.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.progress_bar.stop())
                    return
                
                if len(available_vf_versions) == 1:
                    selected_language = available_vf_versions[0]
                else:
                    # Afficher une fenêtre de dialogue pour choisir la version VF
                    def choose_vf_version():
                        dialog = tk.Toplevel(self.root)
                        dialog.title("Choix de la version VF")
                        dialog.geometry("300x200")
                        dialog.transient(self.root)
                        dialog.grab_set()
                        
                        tk.Label(dialog, text="Versions VF disponibles:").pack(pady=10)
                        
                        vf_var = tk.StringVar()
                        for i, lang in enumerate(available_vf_versions):
                            tk.Radiobutton(dialog, text=lang.upper(), variable=vf_var, value=lang).pack(anchor=tk.W, padx=20)
                        
                        vf_var.set(available_vf_versions[0])  # Sélectionner la première par défaut
                        
                        def confirm():
                            nonlocal selected_language
                            selected_language = vf_var.get()
                            dialog.destroy()
                            
                        tk.Button(dialog, text="Confirmer", command=confirm).pack(pady=10)
                        
                        # Attendre que la fenêtre soit fermée
                        self.root.wait_window(dialog)
                    
                    self.root.after(0, choose_vf_version)
            
            # Rechercher les saisons disponibles
            try:
                seasons = self.check_seasons(base_url, formatted_url_name, selected_language)
                
                # Créer les checkboxes pour les saisons trouvées
                if seasons:
                    def create_checkboxes():
                        # Select All checkbox
                        self.select_all_var = tk.BooleanVar(value=True)
                        select_all_cb = ttk.Checkbutton(self.season_frame, text="Tout sélectionner", 
                                                      variable=self.select_all_var, command=self.toggle_all)
                        select_all_cb.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
                        self.season_checkboxes.append(select_all_cb)
                        
                        row = 1
                        col = 0
                        
                        for i, (season_num, url, is_variant, variant_num) in enumerate(seasons):
                            # Formater le texte du checkbox
                            if isinstance(season_num, str):  # Film ou OAV
                                text = season_num.upper()
                            else:
                                text = f"Saison {season_num}" + (f" Partie {variant_num}" if is_variant else "")
                            
                            # Créer le checkbox
                            var = tk.BooleanVar(value=True)
                            self.season_vars.append((var, season_num, url, is_variant, variant_num))
                            
                            cb = ttk.Checkbutton(self.season_frame, text=text, variable=var)
                            cb.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
                            self.season_checkboxes.append(cb)
                            
                            # Gérer la mise en page
                            col += 1
                            if col > 2:  # 3 checkboxes par ligne
                                col = 0
                                row += 1
                    
                    self.root.after(0, create_checkboxes)
                    self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.update_status(f"Recherche terminée. {len(seasons)} saisons trouvées."))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Erreur", "Aucune saison trouvée pour cet anime."))
                    self.root.after(0, lambda: self.update_status("Recherche terminée. Aucune saison trouvée."))
            
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erreur", f"Erreur lors de la recherche: {str(e)}"))
                self.root.after(0, lambda: self.log(f"Erreur: {str(e)}"))
            
            finally:
                self.root.after(0, lambda: self.search_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.progress_bar.stop())
        
        # Lancer la recherche dans un thread séparé
        threading.Thread(target=search_thread, daemon=True).start()

    def toggle_all(self):
        """Active ou désactive toutes les saisons"""
        state = self.select_all_var.get()
        for var, _, _, _, _ in self.season_vars:
            var.set(state)

    def start_download(self):
        """Démarre le téléchargement des saisons sélectionnées"""
        # Vérifier si des saisons sont sélectionnées
        selected_seasons = [(season_num, url, is_variant, variant_num) 
                            for var, season_num, url, is_variant, variant_num in self.season_vars 
                            if var.get()]
        
        if not selected_seasons:
            messagebox.showerror("Erreur", "Veuillez sélectionner au moins une saison à télécharger")
            return
        
        # Vérifier l'espace disque
        if not self.check_disk_space():
            messagebox.showerror("Erreur", "Espace disque insuffisant. Libérez de l'espace et réessayez.")
            return
        
        # Configurer l'interface pour le téléchargement
        self.search_button.config(state=tk.DISABLED)
        self.download_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.progress_bar.start()
        self.running = True
        
        # Préparer les informations
        anime_name = self.anime_name_var.get().strip()
        selected_language = self.language_var.get()
        folder_name = self.format_folder_name(anime_name, selected_language)
        
        # Fonction de téléchargement à exécuter dans un thread séparé
        def download_thread():
            try:
                # Dictionnaire pour suivre le nombre d'épisodes par saison et variante
                last_processed = {}  # Pour suivre la dernière saison/variante traitée
                
                for season, url, is_variant, variant_num in selected_seasons:
                    if not self.running:
                        break
                        
                    # Si c'est un film ou un OAV, traiter séparément
                    if season in ["film", "oav"]:
                        sibnet_links, vidmoly_links = self.extract_video_links(url)
                        if sibnet_links or vidmoly_links:
                            self.download_videos(sibnet_links, vidmoly_links, season, folder_name)
                        continue
                    
                    sibnet_links, vidmoly_links = self.extract_video_links(url)
                    total_episodes = len(sibnet_links) + len(vidmoly_links)
                    
                    if not (sibnet_links or vidmoly_links):
                        self.log(f"⛔ Aucun épisode trouvé pour {'la Partie ' + str(variant_num) + ' de ' if is_variant else ''}la saison {season}")
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
                    
                    self.log(f"♾️ Traitement de {'la Partie ' + str(variant_num) + ' de ' if is_variant else ''}la saison {season}")
                    self.log(f"🔢 Épisodes: {start_episode} à {start_episode + total_episodes - 1}")
                    
                    self.download_videos(sibnet_links, vidmoly_links, season, folder_name, start_episode)
                    
                    # Mettre à jour le compteur pour cette saison
                    last_processed[season] = start_episode + total_episodes - 1
                
                if self.running:
                    self.root.after(0, lambda: messagebox.showinfo("Terminé", "Téléchargement terminé avec succès!"))
                    self.root.after(0, lambda: self.update_status("Téléchargement terminé"))
            
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erreur", f"Erreur lors du téléchargement: {str(e)}"))
                self.root.after(0, lambda: self.log(f"Erreur: {str(e)}"))
            
            finally:
                self.running = False
                self.root.after(0, lambda: self.search_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.cancel_button.config(state=tk.DISABLED))
                self.root.after(0, lambda: self.progress_bar.stop())
        
        # Lancer le téléchargement dans un thread séparé
        self.download_thread = threading.Thread(target=download_thread, daemon=True)
        self.download_thread.start()

    def cancel_download(self):
        """Annule le téléchargement en cours"""
        if self.running:
            self.running = False
            self.update_status("Annulation du téléchargement...")
            self.log("⚠️ Demande d'annulation... Le téléchargement va s'arrêter après l'épisode en cours.")

def main():
    root = tk.Tk()
    app = AnimeDownloaderGUI(root)
    
    # Icône de l'application (commenter si pas d'icône disponible)
    # root.iconbitmap("anime_icon.ico")
    
    # Centrer la fenêtre
    window_width = 700
    window_height = 600
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    position_top = int(screen_height / 2 - window_height / 2)
    position_right = int(screen_width / 2 - window_width / 2)
    root.geometry(f"{window_width}x{window_height}+{position_right}+{position_top}")
    
    root.mainloop()

if __name__ == "__main__":
    main()
