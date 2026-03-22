#!/bin/sh

# Script d'installation compatible iSH Shell (iOS) et Termux (Android)
# iSH utilise Alpine Linux avec apk comme gestionnaire de paquets
# Termux utilise pkg/apt

echo "🔍 Détection de l'environnement..."

# Détection de la plateforme
PLATFORM=$(uname -s)
IS_ISH=false
IS_TERMUX=false
IS_IOS=false

# Détection iSH (Alpine Linux sur iOS)
if [ -f "/etc/alpine-release" ]; then
    echo "📱 Plateforme détectée : iSH Shell (iOS - iPhone/iPad)"
    echo ""
    echo "❌ Co-chan n'est pas compatible avec iPhone/iPad."
    echo "   Ce script nécessite Termux sur Android ou un système Linux/macOS."
    echo ""
    echo "💡 Astuce : Utilisez un PC, un Mac ou un appareil Android avec Termux."
    exit 1
    
# Détection Termux (Android)
elif [ -d "/data/data/com.termux" ]; then
    IS_TERMUX=true
    echo "📱 Plateforme détectée : Termux (Android)"
    PKG_MANAGER="pkg"
    
# Détection iOS (autres apps comme Pythonista)
elif [ "$PLATFORM" = "Darwin" ]; then
    if [ -d "/var/mobile" ] || [ -f "/System/Library/CoreServices/SpringBoard.app/SpringBoard" ]; then
        echo "📱 Plateforme détectée : iOS (iPhone/iPad)"
        echo ""
        echo "❌ Co-chan n'est pas compatible avec iPhone/iPad."
        echo "   Ce script nécessite Termux sur Android ou un système Linux/macOS."
        echo ""
        echo "💡 Astuce : Utilisez un PC, un Mac ou un appareil Android avec Termux."
        exit 1
    else
        echo "🖥️ Plateforme détectée : macOS"
    fi
    
# Android standard
elif [ -d "/storage/emulated/0" ] || [ -d "/sdcard" ]; then
    IS_TERMUX=true
    echo "📱 Plateforme détectée : Android (Termux)"
    PKG_MANAGER="pkg"
    
else
    echo "🖥️ Plateforme détectée : Linux"
fi

echo ""

# Configuration du stockage selon la plateforme
if [ "$IS_ISH" = true ]; then
    echo "⚙️ Configuration iSH (Alpine Linux)..."
    echo "Les fichiers seront téléchargés dans ~/anime/"
    mkdir -p ~/anime
    DOWNLOAD_PATH="$HOME/anime"
    
elif [ "$IS_TERMUX" = true ]; then
    echo "⚙️ Configuration Termux (Android)..."
    # Vérifier si termux-setup-storage a été exécuté
    if [ ! -d "$HOME/storage" ]; then
        echo "Configuration du stockage Android..."
        termux-setup-storage
        echo "Le stockage Android a été configuré."
    else
        echo "Le stockage est déjà configuré."
    fi
    DOWNLOAD_PATH="/storage/emulated/0/Download/anime"
    
else
    echo "⚙️ Configuration stockage standard..."
    mkdir -p ~/Downloads/anime
    DOWNLOAD_PATH="$HOME/Downloads/anime"
fi

echo ""

# Installation des paquets selon la plateforme
if [ "$IS_ISH" = true ]; then
    echo "📦 Installation des paquets pour iSH (Alpine Linux)..."
    
    # Mise à jour des dépôts
    apk update
    apk upgrade
    
    # Installation de Python et dépendances
    echo "Installation de Python 3 et pip..."
    apk add python3 py3-pip git curl
    
    # Installation des dépendances Python essentielles
    echo "Installation des bibliothèques Python..."
    pip3 install --break-system-packages requests beautifulsoup4
    pip3 install --break-system-packages -U yt-dlp
    
    # NumPy est optionnel (pas utilisé dans le script anime)
    echo "Installation de NumPy (optionnel)..."
    apk add py3-numpy 2>/dev/null || echo "⚠️ NumPy ignoré (non essentiel pour ce script)"
    
    # Pour Pillow sur Alpine, on a besoin de dépendances supplémentaires
    echo "Installation des dépendances pour Pillow..."
    apk add jpeg-dev zlib-dev py3-pillow
    pip3 install --break-system-packages Pillow || echo "⚠️ Pillow optionnel, continuer sans..."
    
elif [ "$IS_TERMUX" = true ]; then
    echo "📦 Installation des paquets pour Termux (Android)..."
    
    # Mise à jour des paquets
    pkg update && pkg upgrade -y
    
    # Installation de Python et dépendances
    echo "Installation de Python 3 et pip..."
    pkg install python git -y
    
    # Installation des dépendances Python
    echo "Installation des bibliothèques Python..."
    pip install --upgrade pip
    pip install requests beautifulsoup4
    pip install -U yt-dlp
    pip install Pillow || echo "⚠️ Pillow optionnel, continuer sans..."
    
else
    echo "📦 Installation des paquets (Linux standard)..."
    echo "⚠️ Utilisez votre gestionnaire de paquets (apt/dnf/pacman) pour installer:"
    echo "   - python3"
    echo "   - python3-pip"
    echo "   - git"
    echo ""
    echo "Puis installez les dépendances Python:"
    pip3 install --break-system-packages requests beautifulsoup4 yt-dlp Pillow 2>/dev/null || \
    pip3 install requests beautifulsoup4 yt-dlp Pillow
fi

echo ""

# Téléchargement du script Python
echo "📥 Téléchargement du script de téléchargement d'anime..."

if [ "$IS_ISH" = true ] || [ "$IS_IOS" = true ]; then
    # Pour iSH/iOS, télécharger dans le home
    SCRIPT_PATH="$HOME/Co-chan.py"
else
    # Pour Termux/Android, télécharger dans le home
    SCRIPT_PATH="$HOME/Co-chan.py"
fi

# Télécharger le script depuis GitHub
curl -L -o "$SCRIPT_PATH" https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/Co-chan.py

if [ -f "$SCRIPT_PATH" ]; then
    echo "✅ Script téléchargé avec succès"
    chmod +x "$SCRIPT_PATH"
else
    echo "❌ Erreur lors du téléchargement du script"
    exit 1
fi

echo ""

# Créer le répertoire de raccourcis
mkdir -p ~/.shortcuts

# Créer le fichier shell pour exécuter le script Python
if [ "$IS_ISH" = true ]; then
    # Version iSH
    cat << 'EOF' > ~/.shortcuts/anime_downloader.sh
#!/bin/sh
# iSH Shell - Lancer le téléchargeur d'anime
cd ~
python3 Co-chan.py
EOF

    # Créer un script helper pour copier les vidéos vers l'iPad
    cat << 'EOF' > ~/.shortcuts/copy_to_ipad.sh
#!/bin/sh
# iSH Shell - Copier les vidéos vers l'iPad
echo "📱 Copie des vidéos vers l'iPad..."
echo ""
echo "🔌 Montage du système de fichiers iOS..."
echo "   Une fenêtre va s'ouvrir, choisissez un dossier (ex: 'Sur mon iPad')"
echo ""

# Créer le point de montage si nécessaire
mkdir -p /mnt

# Monter le système iOS
mount -t ios dummy /mnt

if [ $? -eq 0 ]; then
    echo "✅ Système iOS monté"
    echo ""
    echo "📂 Copie des fichiers depuis ~/anime/ vers /mnt/ ..."
    
    # Compter les fichiers
    count=$(ls -1 ~/anime/*.mp4 2>/dev/null | wc -l)
    
    if [ "$count" -gt 0 ]; then
        cp ~/anime/*.mp4 /mnt/
        echo "✅ $count vidéo(s) copiée(s) vers l'iPad"
        echo ""
        echo "📱 Ouvrez l'app Fichiers sur votre iPad pour voir les vidéos"
    else
        echo "⚠️ Aucune vidéo trouvée dans ~/anime/"
    fi
else
    echo "❌ Erreur lors du montage du système iOS"
fi
EOF

    chmod +x ~/.shortcuts/copy_to_ipad.sh
    
    # Créer un script pour supprimer tous les animes
    cat << 'EOF' > ~/.shortcuts/remove_all_anime.sh
#!/bin/sh
# iSH Shell - Supprimer tous les animes de la VM
echo "🗑️ Suppression de tous les animes..."
echo ""
echo "⚠️ ATTENTION : Cette action va supprimer TOUS les dossiers d'animes dans ~/anime/"
echo ""
printf "Êtes-vous sûr de vouloir continuer ? (o/n): "
read -r confirm

if [ "$confirm" = "o" ] || [ "$confirm" = "oui" ] || [ "$confirm" = "y" ] || [ "$confirm" = "yes" ]; then
    if [ -d ~/anime ]; then
        # Compter les fichiers avant suppression
        count=$(find ~/anime -name "*.mp4" 2>/dev/null | wc -l)
        
        # Supprimer tout le contenu
        rm -rf ~/anime/*
        
        echo "✅ $count vidéo(s) supprimée(s)"
        echo "📁 Le dossier ~/anime/ a été vidé"
    else
        echo "ℹ️ Le dossier ~/anime/ n'existe pas"
    fi
else
    echo "❌ Suppression annulée"
fi
EOF

    chmod +x ~/.shortcuts/remove_all_anime.sh
    
    echo ""
    echo "✅ Scripts helpers créés :"
    echo "   • ~/.shortcuts/copy_to_ipad.sh - Pour copier les vidéos vers l'iPad"
    echo "   • ~/.shortcuts/remove_all_anime.sh - Pour supprimer tous les animes"

elif [ "$IS_TERMUX" = true ]; then
    # Version Termux
    cat << 'EOF' > ~/.shortcuts/anime_downloader.sh
#!/data/data/com.termux/files/usr/bin/bash
# Termux - Lancer le téléchargeur d'anime
cd ~
python3 Co-chan.py
EOF

else
    # Version Linux/macOS standard
    cat << 'EOF' > ~/.shortcuts/anime_downloader.sh
#!/bin/bash
# Lancer le téléchargeur d'anime
cd ~
python3 Co-chan.py
EOF
fi

# Rendre le fichier shell exécutable
chmod +x ~/.shortcuts/anime_downloader.sh

echo ""

# Proposer de créer l'alias automatiquement
if [ "$IS_ISH" = true ] || [ "$IS_TERMUX" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 Configuration de l'alias 'anime'"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Voulez-vous créer un alias 'anime' pour lancer facilement le script ?"
    echo "Vous pourrez ensuite taper simplement: anime"
    echo ""
    printf "Créer l'alias ? (o/n) [o]: "
    read -r create_alias
    
    # Par défaut : oui
    if [ -z "$create_alias" ]; then
        create_alias="o"
    fi
    
    if [ "$create_alias" = "o" ] || [ "$create_alias" = "y" ] || [ "$create_alias" = "yes" ] || [ "$create_alias" = "oui" ]; then
        if [ "$IS_ISH" = true ]; then
            # Pour iSH, utiliser .profile
            if ! grep -q "alias anime=" ~/.profile 2>/dev/null; then
                echo 'alias anime="python3 ~/Co-chan.py"' >> ~/.profile
                echo 'alias voiranime="sh ~/.shortcuts/copy_to_ipad.sh"' >> ~/.profile
                echo 'alias rmanime="sh ~/.shortcuts/remove_all_anime.sh"' >> ~/.profile
                echo "✅ Alias créés dans ~/.profile"
                echo "   • anime           → Lance le téléchargeur"
                echo "   • voiranime       → Copie les vidéos vers l'iPad"
                echo "   • rmanime         → Supprime tous les animes de la VM"
                echo ""
                echo "   Redémarrez iSH puis utilisez ces commandes"
            else
                echo "ℹ️ Alias déjà présent dans ~/.profile"
            fi
        else
            # Pour Termux, utiliser .bashrc
            if ! grep -q "alias anime=" ~/.bashrc 2>/dev/null; then
                echo 'alias anime="python3 ~/Co-chan.py"' >> ~/.bashrc
                echo "✅ Alias créé dans ~/.bashrc"
                echo "   Redémarrez Termux puis tapez: anime"
            else
                echo "ℹ️ Alias déjà présent dans ~/.bashrc"
            fi
        fi
    else
        echo "⏭️ Alias non créé"
    fi
    echo ""
fi

echo ""
echo "✅ Installation terminée !"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$IS_ISH" = true ]; then
    echo "📱 Configuration iSH Shell (iOS) :"
    echo "  • Script installé : ~/Co-chan.py"
    echo "  • Téléchargements : ~/anime/"
    echo "  • Raccourci : ~/.shortcuts/anime_downloader.sh"
    echo ""
    echo "🚀 Pour lancer le script :"
    echo "   python3 ~/Co-chan.py"
    echo ""
    echo "💡 Astuce iSH :"
    echo "   Vous pouvez créer un alias dans ~/.profile :"
    echo "   echo 'alias anime=\"python3 ~/Co-chan.py\"' >> ~/.profile"
    echo "   Puis redémarrer iSH et taper simplement: anime"
    echo ""
    echo "📂 Pour voir les vidéos sur iPad :"
    echo "   Utilisez la commande: voiranime"
    echo ""
    echo "🗑️ Pour supprimer tous les animes de la VM :"
    echo "   Utilisez la commande: rmanime"
    
elif [ "$IS_TERMUX" = true ]; then
    echo "📱 Configuration Termux (Android) :"
    echo "  • Script installé : ~/Co-chan.py"
    echo "  • Téléchargements : /storage/emulated/0/Download/anime/"
    echo "  • Raccourci : ~/.shortcuts/anime_downloader.sh"
    echo ""
    echo "🚀 Pour lancer le script :"
    echo "   python3 ~/Co-chan.py"
    echo ""
    echo "💡 Méthode recommandée - Créer un alias :"
    echo "   echo 'alias anime=\"python3 ~/Co-chan.py\"' >> ~/.bashrc"
    echo "   Puis redémarrer Termux et taper simplement: anime"
    echo ""
    echo "💡 Alternative - Utiliser le widget Termux :"
    echo "   Le widget peut exécuter les raccourcis dans ~/.shortcuts/"
    
else
    echo "🖥️ Configuration Linux/macOS :"
    echo "  • Script installé : ~/Co-chan.py"
    echo "  • Téléchargements : ~/Downloads/anime/"
    echo "  • Raccourci : ~/.shortcuts/anime_downloader.sh"
    echo ""
    echo "🚀 Pour lancer le script :"
    echo "   python3 ~/Co-chan.py"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 Tout est prêt ! Bon téléchargement ! 🎌"
echo ""
