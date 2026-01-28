#!/data/data/com.termux/files/usr/bin/bash

# Détection de la plateforme
PLATFORM=$(uname -s)
IS_IOS=false

# Détection iOS
if [ "$PLATFORM" = "Darwin" ]; then
    if [ -d "/var/mobile" ] || [ -f "/System/Library/CoreServices/SpringBoard.app/SpringBoard" ]; then
        IS_IOS=true
        echo "📱 Plateforme détectée : iOS (iPhone/iPad)"
    else
        echo "🖥️ Plateforme détectée : macOS"
    fi
elif [ -d "/storage/emulated/0" ] || [ -d "/sdcard" ]; then
    echo "📱 Plateforme détectée : Android (Termux)"
else
    echo "🖥️ Plateforme détectée : Linux"
fi

# Configuration du stockage selon la plateforme
if [ "$IS_IOS" = true ]; then
    echo "⚠️ Sur iOS, l'accès au stockage est limité aux dossiers Documents et Downloads"
    echo "Les fichiers seront téléchargés dans le dossier Documents de Termux"
    
    # Créer le dossier anime dans Documents si nécessaire
    mkdir -p ~/Documents/anime
    
elif [ -d "/storage/emulated/0" ]; then
    # Android - Vérifier si termux-setup-storage a été exécuté
    if [ ! -d "$HOME/storage" ]; then
        echo "Configuration du stockage Android..."
        termux-setup-storage
        echo "Le stockage Android a été configuré."
    else
        echo "Le stockage est déjà configuré."
    fi
else
    echo "Configuration du stockage standard..."
fi

# Mise à jour des paquets et installation des dépendances
echo "Mise à jour de Termux et installation de Python, pip et git..."
pkg update && pkg upgrade -y
pkg install python git -y
pip install --upgrade pip

echo "Installation des dépendances Python..."
pip install requests beautifulsoup4 numpy

# Installation de yt-dlp
echo "Installation de yt-dlp..."
pip install -U yt-dlp

# Téléchargement du script Python compatible iOS
echo "Téléchargement du script de téléchargement d'anime..."
if [ "$IS_IOS" = true ]; then
    # Pour iOS, télécharger dans le dossier Documents
    curl -L -o ~/Documents/Anime-dowload-termux.py https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/Anime-dowload.py
    SCRIPT_PATH="~/Documents/Anime-dowload-termux.py"
else
    # Pour Android/Linux, télécharger dans le home
    curl -L -o ~/Anime-dowload-termux.py https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/Anime-dowload.py
    SCRIPT_PATH="~/Anime-dowload-termux.py"
fi

# Créer le répertoire de raccourcis s'il n'existe pas
mkdir -p ~/.shortcuts

# Créer le fichier shell pour exécuter le script Python
if [ "$IS_IOS" = true ]; then
    # Version iOS
    cat << 'EOF' > ~/.shortcuts/anime_downloader.sh
#!/data/data/com.termux/files/usr/bin/bash
# Se rendre dans le répertoire Documents
cd ~/Documents

# Exécution du script Python pour télécharger des vidéos d'anime
python3 Anime-dowload-termux.py
EOF
else
    # Version Android/Linux
    cat << 'EOF' > ~/.shortcuts/anime_downloader.sh
#!/data/data/com.termux/files/usr/bin/bash
# Se rendre dans le répertoire de travail
cd ~

# Exécution du script Python pour télécharger des vidéos d'anime
python3 Anime-dowload-termux.py
EOF
fi

# Rendre le fichier shell exécutable
chmod +x ~/.shortcuts/anime_downloader.sh

echo ""
echo "✅ Installation terminée !"
echo ""

if [ "$IS_IOS" = true ]; then
    echo "📱 Configuration iOS :"
    echo "  - Script installé dans : ~/Documents/Anime-dowload-termux.py"
    echo "  - Téléchargements dans : ~/Documents/anime/"
    echo "  - Raccourci créé dans : ~/.shortcuts/anime_downloader.sh"
    echo ""
    echo "Pour lancer le script :"
    echo "  1. Tapez : cd ~/Documents"
    echo "  2. Puis : python3 Anime-dowload-termux.py"
    echo "  OU utilisez le widget Termux pour lancer le raccourci"
else
    echo "📱 Configuration Android/Linux :"
    echo "  - Script installé dans : ~/Anime-dowload-termux.py"
    if [ -d "/storage/emulated/0" ]; then
        echo "  - Téléchargements dans : /storage/emulated/0/Download/anime/"
    else
        echo "  - Téléchargements dans : ~/Downloads/anime/"
    fi
    echo "  - Raccourci créé dans : ~/.shortcuts/anime_downloader.sh"
    echo ""
    echo "Pour lancer le script :"
    echo "  1. Tapez : python3 ~/Anime-dowload-termux.py"
    echo "  OU utilisez le widget Termux pour lancer le raccourci"
fi

echo ""
echo "🎉 Le script est prêt à être utilisé !"
