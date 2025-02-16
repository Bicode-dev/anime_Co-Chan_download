#!/data/data/com.termux/files/usr/bin/bash

# Vérifier si termux-setup-storage a été exécuté, sinon le faire
if [ ! -d "/storage/emulated/0" ]; then
    echo "Configuration du stockage Android..."
    termux-setup-storage
    echo "Le stockage Android a été configuré."
else
    echo "Le stockage est déjà configuré."
fi

# Mettre à jour les paquets et installer les dépendances nécessaires
echo "Mise à jour de Termux et installation de Python, pip et git..."
pkg update && pkg upgrade -y
pkg install python git -y
pip install --upgrade pip
pip install requests yt-dlp beautifulsoup4 numpy


# Télécharger le fichier Python Anime-dowload-termux.py depuis GitHub
echo "Téléchargement du fichier Anime-dowload-termux.py depuis GitHub..."
curl -L -o ~/Anime-dowload-termux.py https://raw.githubusercontent.com/les-developpeur/anime-soma/refs/heads/main/Anime-dowload.py

# Créer le répertoire de raccourcis s'il n'existe pas
mkdir -p ~/.shortcuts

# Créer le fichier shell pour exécuter le script Python
cat << 'EOF' > ~/.shortcuts/anime_downloader.sh
#!/data/data/com.termux/files/usr/bin/bash

# Se rendre dans le répertoire de travail
cd ~

# Exécution du script Python pour télécharger des vidéos d'anime
python3 Anime-dowload-termux.py
EOF

# Rendre le fichier shell exécutable
chmod +x ~/.shortcuts/anime_downloader.sh

echo "Le script a été créé dans le répertoire des raccourcis !"
