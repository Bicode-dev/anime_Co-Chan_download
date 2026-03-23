#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
#   CO-INSTALL  v4.0  —  Installateur CO-TEAM pour Termux
#   Menu dense avec statut en temps réel  •  Actions par script  •  Thème/heure
# ═══════════════════════════════════════════════════════════════════════════════

RESET='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'; ITALIC='\033[3m'

# ── Thème selon l'heure ───────────────────────────────────────────────────────
HOUR=$(date +%H); START_TIME=$(date +"%H:%M"); START_DATE=$(date +"%d/%m/%Y")

if   [ "$HOUR" -ge 5  ] && [ "$HOUR" -lt 9  ]; then
    THEME="Aube";    EMOJI="🌅"
    C1='\033[38;5;214m'; C2='\033[38;5;209m'; C3='\033[38;5;228m'; BAR='▓'
elif [ "$HOUR" -ge 9  ] && [ "$HOUR" -lt 12 ]; then
    THEME="Matin";   EMOJI="☀️ "
    C1='\033[38;5;81m';  C2='\033[38;5;123m'; C3='\033[38;5;195m'; BAR='█'
elif [ "$HOUR" -ge 12 ] && [ "$HOUR" -lt 17 ]; then
    THEME="Après-midi"; EMOJI="🌞"
    C1='\033[38;5;118m'; C2='\033[38;5;156m'; C3='\033[38;5;228m'; BAR='▪'
elif [ "$HOUR" -ge 17 ] && [ "$HOUR" -lt 21 ]; then
    THEME="Soirée";  EMOJI="🌆"
    C1='\033[38;5;213m'; C2='\033[38;5;205m'; C3='\033[38;5;183m'; BAR='◆'
else
    THEME="Nuit";    EMOJI="🌙"
    C1='\033[38;5;99m';  C2='\033[38;5;135m'; C3='\033[38;5;147m'; BAR='·'
fi

OK="${C1}✔${RESET}"; WARN="${C3}⚠${RESET}"; ERR='\033[38;5;196m✘'"${RESET}"
INFO="${C2}›${RESET}"; ARR="${C1}▶${RESET}"

# ── URLs ──────────────────────────────────────────────────────────────────────
URL_COMENU="https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/Co-Menu.py"
URL_COCHAN="https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/Co-chan.py"
URL_COTUBE="https://raw.githubusercontent.com/Bicode-dev/Co-tube/main/Co-tube.py"

PY_DIR="$HOME/.local/share/CoTEAM/Co-Menu"
COMENU_PATH="$HOME/Co-Menu.py"
COCHAN_PATH="$PY_DIR/Co-chan.py"
COTUBE_PATH="$PY_DIR/Co-tube.py"
COFLIX_PATH="$PY_DIR/Co-flix.py"

# ── Helpers ───────────────────────────────────────────────────────────────────
clr() { clear; }
nl()  { echo ""; }
sep_h(){ echo -e "${C1}  $(printf '═%.0s' $(seq 1 54))${RESET}"; }
sep_l(){ echo -e "${DIM}  $(printf '─%.0s' $(seq 1 54))${RESET}"; }
line_ok()  { echo -e "  ${OK}  $1"; }
line_warn(){ echo -e "  ${WARN}  $1"; }
line_err() { echo -e "  ${ERR}  $1"; }
line_info(){ echo -e "  ${INFO}  $1"; }
section()  { echo -e "\n  ${ARR} ${BOLD}${C1}$1${RESET}"; sep_l; }
pause()    { printf "  ${DIM}Entrée pour continuer...${RESET} "; read -r; }

# ── Taille distante ───────────────────────────────────────────────────────────
remote_size() {
    curl -sLI "$1" 2>/dev/null \
        | grep -i "^content-length:" | tail -1 \
        | awk '{print $2}' | tr -d '\r\n'
}

# ── Statut d'un fichier (retourne une ligne formatée) ─────────────────────────
# Usage : file_status_line <path> <url> <label>
file_status_line() {
    local path="$1" url="$2" label="$3"
    local pad=12
    local lpad=$(( pad - ${#label} ))
    [ "$lpad" -lt 1 ] && lpad=1
    local spaces=$(printf '%*s' "$lpad" '')

    if [ ! -f "$path" ]; then
        echo -e "  ${ERR}  ${BOLD}${label}${RESET}${spaces}${ERR} Manquant${RESET}          ${DIM}—${RESET}"
        return
    fi

    local lsize=$(wc -c < "$path" | tr -d ' ')
    local ldate=$(date -r "$path" "+%d/%m %H:%M" 2>/dev/null || stat -c "%y" "$path" 2>/dev/null | cut -d' ' -f1,2 | cut -c1-11)
    local rsize=$(remote_size "$url")
    local size_fmt

    if   [ "$lsize" -gt 999999 ] 2>/dev/null; then size_fmt="$(( lsize/1024 ))Ko"
    elif [ "$lsize" -gt 999    ] 2>/dev/null; then size_fmt="$(( lsize/1024 ))Ko"
    else size_fmt="${lsize}o"; fi

    if [ -z "$rsize" ] || [ "$rsize" = "0" ]; then
        echo -e "  ${WARN}  ${BOLD}${label}${RESET}${spaces}${C3} Installé${RESET}  ${DIM}${size_fmt}${RESET}   ${DIM}màj: ${ldate}${RESET}  ${DIM}(taille distante inconnue)${RESET}"
        return
    fi

    local diff=$(( rsize - lsize ))
    [ "$diff" -lt 0 ] && diff=$(( -diff ))
    if [ "$diff" -le 1 ]; then
        echo -e "  ${OK}  ${BOLD}${label}${RESET}${spaces}${C1} À jour${RESET}    ${DIM}${size_fmt}${RESET}   ${DIM}màj: ${ldate}${RESET}"
    else
        local rdiff=$(( (rsize - lsize > 0 ? rsize - lsize : lsize - rsize) ))
        echo -e "  ${WARN}  ${BOLD}${label}${RESET}${spaces}${C3} MàJ dispo${RESET} ${DIM}${size_fmt}${RESET}   ${DIM}màj: ${ldate}  (+${rdiff}o)${RESET}"
    fi
}

# ── Barre de progression ──────────────────────────────────────────────────────
progress_bar() {
    local label="$1" W=36 i=0
    while [ "$i" -le 100 ]; do
        local f=$(( i * W / 100 )) e=$(( W - i * W / 100 ))
        local bar=""
        local x=0; while [ "$x" -lt "$f" ]; do bar="${bar}${BAR}"; x=$((x+1)); done
        local y=0; while [ "$y" -lt "$e" ]; do bar="${bar}─";       y=$((y+1)); done
        printf "\r  ${C1}[${RESET}${C2}%s${RESET}${C1}]${RESET} ${BOLD}%3d%%${RESET}  ${DIM}%s${RESET}   " "$bar" "$i" "$label"
        i=$((i+4)); sleep 0.03
    done; echo ""
}

# ── Téléchargement avec comparaison taille ────────────────────────────────────
fetch_script() {
    local url="$1" dest="$2" label="$3"; nl
    local rsize=$(remote_size "$url")

    if [ -f "$dest" ] && [ -n "$rsize" ] && [ "$rsize" != "0" ]; then
        local lsize=$(wc -c < "$dest" | tr -d ' ')
        local diff=$(( rsize - lsize < 0 ? lsize - rsize : rsize - lsize ))
        if [ "$diff" -le 1 ]; then
            line_ok "${BOLD}${label}${RESET}${C1} — Déjà à jour${RESET} ${DIM}(${lsize}o)${RESET}"
            return 0
        fi
        line_info "${BOLD}${label}${RESET} ${DIM}${lsize}o → ${rsize}o${RESET}"
    elif [ -f "$dest" ]; then
        line_info "${BOLD}${label}${RESET} ${DIM}— taille distante inconnue, mise à jour...${RESET}"
    else
        line_info "${BOLD}${label}${RESET} ${C3}— Première installation...${RESET}"
    fi

    mkdir -p "$(dirname "$dest")"
    progress_bar "$label"
    if curl -sL -o "$dest" "$url"; then
        local nsize=$(wc -c < "$dest" | tr -d ' ')
        line_ok "${BOLD}${label}${RESET}${C1} — OK${RESET} ${DIM}(${nsize}o)${RESET}"
        chmod +x "$dest"; return 0
    else
        line_err "${label} — Échec"; return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
#  BANNIÈRE
# ═══════════════════════════════════════════════════════════════════════════════
banner() {
    echo -e "${C1}"
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║  ██████╗ ██████╗    ████████╗███████╗ █████╗        ║"
    echo "  ║  ██╔════╝██╔═══██╗     ██╔══╝██╔════╝██╔══██╗       ║"
    echo "  ║  ██║     ██║   ██║     ██║   █████╗  ███████║       ║"
    echo "  ║  ╚██████╗╚██████╔╝     ██║   ███████╗██║  ██║       ║"
    echo -e "  ║${RESET}${C3}  ${EMOJI}  ${THEME}  ·  ${START_TIME}  ·  ${START_DATE}              ${C1}║"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo -e "${RESET}"
}

# ═══════════════════════════════════════════════════════════════════════════════
#  MENU PRINCIPAL DENSE
# ═══════════════════════════════════════════════════════════════════════════════
print_menu() {
    clr
    banner

    # ── Section ÉTAT DES FICHIERS ─────────────────────────────────────────────
    echo -e "  ${C1}${BOLD}═══ ÉTAT DES FICHIERS ${DIM}(vérification en cours...)${RESET}${C1} $(printf '═%.0s' $(seq 1 18))${RESET}"
    file_status_line "$COMENU_PATH" "$URL_COMENU" "Co-Menu.py"
    file_status_line "$COCHAN_PATH" "$URL_COCHAN" "Co-chan.py"
    file_status_line "$COTUBE_PATH" "$URL_COTUBE" "Co-tube.py"
    if [ -f "$COFLIX_PATH" ]; then
        local lsize=$(wc -c < "$COFLIX_PATH" | tr -d ' ')
        local ldate=$(date -r "$COFLIX_PATH" "+%d/%m %H:%M" 2>/dev/null || echo "—")
        echo -e "  ${WARN}  ${BOLD}Co-flix.py${RESET}  ${C3} Manuel${RESET}     ${DIM}${lsize}o   màj: ${ldate}  (pas d'URL publique)${RESET}"
    else
        echo -e "  ${ERR}  ${BOLD}Co-flix.py${RESET}        ${ERR} Manquant${RESET}          ${DIM}màj manuelle requise${RESET}"
    fi
    nl

    # ── Section PAR SCRIPT ───────────────────────────────────────────────────
    echo -e "  ${C2}${BOLD}═══ PAR SCRIPT $(printf '═%.0s' $(seq 1 38))${RESET}"
    echo -e "  ${C1}${BOLD} [1] ${RESET} Co-Menu.py   ${DIM}→ installer ou mettre à jour${RESET}"
    echo -e "  ${C1}${BOLD} [2] ${RESET} Co-chan.py   ${DIM}→ installer ou mettre à jour${RESET}"
    echo -e "  ${C1}${BOLD} [3] ${RESET} Co-tube.py  ${DIM}→ installer ou mettre à jour${RESET}"
    nl

    # ── Section INSTALLATION ─────────────────────────────────────────────────
    echo -e "  ${C2}${BOLD}═══ INSTALLATION $(printf '═%.0s' $(seq 1 36))${RESET}"
    echo -e "  ${C1}${BOLD} [4] ${RESET} Installation complète          ${DIM}paquets + scripts + config${RESET}"
    echo -e "  ${C1}${BOLD} [5] ${RESET} Mettre à jour tous les scripts ${DIM}Co-Menu + Co-chan + Co-tube${RESET}"
    nl

    # ── Section OUTILS ───────────────────────────────────────────────────────
    echo -e "  ${C3}${BOLD}═══ OUTILS $(printf '═%.0s' $(seq 1 42))${RESET}"
    echo -e "  ${C2}${BOLD} [6] ${RESET} Stockage Android               ${DIM}termux-setup-storage${RESET}"
    echo -e "  ${C2}${BOLD} [7] ${RESET} Alias & raccourcis Termux      ${DIM}co / anime / cotube / coupdate${RESET}"
    echo -e "  ${C2}${BOLD} [8] ${RESET} Supprimer les animes           ${DIM}/storage/.../Download/anime${RESET}"
    echo -e "  ${C3}${BOLD} [9] ${RESET} Tout désinstaller              ${DIM}scripts + alias + raccourcis${RESET}"
    nl

    sep_l
    echo -e "  ${DIM} [0]  Quitter${RESET}"
    sep_l
    nl
    printf "  ${C1}${BOLD}›› ${RESET}Choix : "
}

# ═══════════════════════════════════════════════════════════════════════════════
#  ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

update_packages() {
    section "Mise à jour des paquets Termux"
    pkg update -y && pkg upgrade -y
    line_ok "Paquets à jour"
}

install_pkg() {
    section "Paquets système"
    for p in python git curl; do
        if pkg list-installed 2>/dev/null | grep -q "^${p}/"; then
            line_ok "${BOLD}${p}${RESET} ${DIM}déjà installé${RESET}"
        else
            line_info "Installation de ${BOLD}${p}${RESET}..."
            pkg install "$p" -y && line_ok "${p} installé" || line_warn "Impossible d'installer ${p}"
        fi
    done
}

install_pip() {
    section "Bibliothèques Python"
    pip install --upgrade pip -q && line_ok "pip à jour"; nl
    for pkg_name in requests beautifulsoup4 yt-dlp Pillow; do
        if pip show "$pkg_name" >/dev/null 2>&1; then
            local cur=$(pip show "$pkg_name" 2>/dev/null | grep "^Version:" | awk '{print $2}')
            local lat=$(pip index versions "$pkg_name" 2>/dev/null | head -1 | grep -oP '\(.*?\)' | tr -d '()' | cut -d',' -f1)
            if [ -n "$lat" ] && [ "$lat" != "$cur" ]; then
                line_info "${BOLD}${pkg_name}${RESET} ${DIM}${cur} → ${lat}${RESET}"
                pip install --upgrade "$pkg_name" -q \
                    && line_ok "${pkg_name} → ${lat}" || line_warn "${pkg_name} échoué"
            else
                line_ok "${BOLD}${pkg_name}${RESET} ${DIM}(${cur})${RESET}"
            fi
        else
            line_info "Installation de ${BOLD}${pkg_name}${RESET}..."
            pip install "$pkg_name" -q && line_ok "${pkg_name}" || line_warn "${pkg_name} optionnel, ignoré"
        fi
    done
}

setup_storage() {
    section "Stockage Android"
    if [ ! -d "$HOME/storage" ]; then
        line_info "Ouverture de termux-setup-storage..."
        termux-setup-storage && line_ok "Stockage configuré"
    else
        line_ok "Stockage déjà configuré"
    fi
    mkdir -p "/storage/emulated/0/Download/anime" 2>/dev/null \
        && line_ok "Dossier anime prêt" \
        || line_warn "Dossier non créé (permissions ?)"
}

setup_shortcuts() {
    section "Raccourcis Termux Widget"
    mkdir -p "$HOME/.shortcuts"

    cat > "$HOME/.shortcuts/CO-MENU.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
python3 ~/Co-Menu.py
EOF
    cat > "$HOME/.shortcuts/CO-CHAN-Anime.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
python3 ~/.local/share/CoTEAM/Co-Menu/Co-chan.py
EOF
    cat > "$HOME/.shortcuts/CO-TUBE-YouTube.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
python3 ~/.local/share/CoTEAM/Co-Menu/Co-tube.py
EOF
    cat > "$HOME/.shortcuts/CO-UPDATE.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
curl -sL https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/Co-install.sh -o /tmp/co-install.sh && bash /tmp/co-install.sh
EOF
    cat > "$HOME/.shortcuts/RM-ANIME.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
DIR="/storage/emulated/0/Download/anime"
count=$(find "$DIR" -name "*.mp4" 2>/dev/null | wc -l)
echo "Animes trouvés : $count"
read -p "Supprimer ? (o/n) : " c
[ "$c" = "o" ] && rm -rf "$DIR"/* && echo "✔ Supprimé" || echo "Annulé"
EOF
    for f in CO-MENU.sh CO-CHAN-Anime.sh CO-TUBE-YouTube.sh CO-UPDATE.sh RM-ANIME.sh; do
        chmod +x "$HOME/.shortcuts/$f"
        line_ok "${DIM}~/.shortcuts/${f}${RESET}"
    done
    nl; line_info "${DIM}Installe Termux:Widget sur ton écran d'accueil pour y accéder.${RESET}"
}

setup_alias() {
    section "Alias ~/.bashrc"
    nl
    echo -e "   ${C1}${BOLD}co${RESET}        ${DIM}→ lance CO-MENU${RESET}"
    echo -e "   ${C1}${BOLD}anime${RESET}     ${DIM}→ lance Co-chan${RESET}"
    echo -e "   ${C1}${BOLD}cotube${RESET}    ${DIM}→ lance Co-tube${RESET}"
    echo -e "   ${C1}${BOLD}coupdate${RESET}  ${DIM}→ relance cet installateur${RESET}"
    echo -e "   ${C1}${BOLD}rmanime${RESET}   ${DIM}→ supprime les animes téléchargés${RESET}"
    nl
    printf "  ${C1}${BOLD}›› ${RESET}Créer / mettre à jour les alias ? ${DIM}[o]${RESET} : "
    read -r ch; [ -z "$ch" ] && ch="o"
    if [ "$ch" = "o" ] || [ "$ch" = "O" ] || [ "$ch" = "y" ]; then
        sed -i '/# ── CO-TEAM START/,/# ── CO-TEAM END/d' "$HOME/.bashrc" 2>/dev/null
        cat >> "$HOME/.bashrc" << 'ALIASES'
# ── CO-TEAM START ──────────────────────────────────────
alias co="python3 ~/Co-Menu.py"
alias anime="python3 ~/.local/share/CoTEAM/Co-Menu/Co-chan.py"
alias cotube="python3 ~/.local/share/CoTEAM/Co-Menu/Co-tube.py"
alias coupdate="bash ~/.shortcuts/CO-UPDATE.sh"
alias rmanime="bash ~/.shortcuts/RM-ANIME.sh"
# ── CO-TEAM END ────────────────────────────────────────
ALIASES
        line_ok "Alias mis à jour dans ${DIM}~/.bashrc${RESET}"
        line_warn "Tape ${BOLD}source ~/.bashrc${RESET} ou redémarre Termux"
    else
        line_info "Ignoré"
    fi
}

delete_animes() {
    section "Supprimer les animes"
    local DIR="/storage/emulated/0/Download/anime"
    if [ ! -d "$DIR" ]; then line_warn "Dossier introuvable : $DIR"; nl; pause; return; fi
    local count=$(find "$DIR" -name "*.mp4" 2>/dev/null | wc -l)
    local total_size=$(du -sh "$DIR" 2>/dev/null | cut -f1)
    nl
    echo -e "  ${C3}Dossier   : ${DIM}${DIR}${RESET}"
    echo -e "  ${C3}Vidéos    : ${BOLD}${count} fichier(s)${RESET}"
    echo -e "  ${C3}Taille    : ${BOLD}${total_size}${RESET}"
    nl
    printf "  ${C1}${BOLD}›› ${RESET}Confirmer la suppression ? ${DIM}(oui/non)${RESET} : "
    read -r cf
    if [ "$cf" = "oui" ] || [ "$cf" = "yes" ]; then
        rm -rf "$DIR"/* && line_ok "${count} fichier(s) supprimé(s)"
    else
        line_info "Annulé"
    fi
}

uninstall_all() {
    clr; banner
    section "Désinstallation complète"
    nl
    echo -e "  ${C3}Éléments ciblés :${RESET}"
    echo -e "  ${DIM}  ~/Co-Menu.py${RESET}"
    echo -e "  ${DIM}  ~/.local/share/CoTEAM/Co-Menu/${RESET}"
    echo -e "  ${DIM}  ~/.shortcuts/CO-*.sh  +  RM-ANIME.sh${RESET}"
    echo -e "  ${DIM}  Alias CO-TEAM dans ~/.bashrc${RESET}"
    nl
    printf "  ${C1}${BOLD}›› ${RESET}Confirmer ? ${DIM}(oui/non)${RESET} : "
    read -r cf
    if [ "$cf" = "oui" ] || [ "$cf" = "yes" ]; then
        rm -f "$COMENU_PATH"; rm -rf "$PY_DIR"
        rm -f "$HOME/.shortcuts/CO-MENU.sh" "$HOME/.shortcuts/CO-CHAN-Anime.sh" \
              "$HOME/.shortcuts/CO-TUBE-YouTube.sh" "$HOME/.shortcuts/CO-UPDATE.sh" \
              "$HOME/.shortcuts/RM-ANIME.sh"
        sed -i '/# ── CO-TEAM START/,/# ── CO-TEAM END/d' "$HOME/.bashrc" 2>/dev/null
        nl; line_ok "Désinstallation terminée"
    else
        line_info "Annulé"
    fi
}

full_install() {
    clr; banner
    nl
    echo -e "  ${C3}${BOLD}Installation complète CO-TEAM${RESET}"
    echo -e "  ${DIM}Durée estimée : 2-5 min selon votre connexion${RESET}"
    nl; pause

    update_packages
    install_pkg
    install_pip

    section "Scripts"
    fetch_script "$URL_COMENU" "$COMENU_PATH" "Co-Menu.py"
    fetch_script "$URL_COCHAN" "$COCHAN_PATH" "Co-chan.py"
    fetch_script "$URL_COTUBE" "$COTUBE_PATH" "Co-tube.py"
    nl; line_warn "Co-flix.py — pas d'URL publique, màj manuelle"

    setup_storage
    setup_shortcuts
    setup_alias

    nl; sep_h
    echo -e "  ${C1}${BOLD}  ✔  Installation terminée !${RESET}"
    sep_h; nl
    echo -e "  ${C3}Lancer :${RESET}  ${C1}${BOLD}python3 ~/Co-Menu.py${RESET}  ${DIM}ou${RESET}  ${C1}${BOLD}co${RESET}"
    nl; pause
}

update_all_scripts() {
    clr; banner
    section "Mise à jour de tous les scripts"
    fetch_script "$URL_COMENU" "$COMENU_PATH" "Co-Menu.py"
    fetch_script "$URL_COCHAN" "$COCHAN_PATH" "Co-chan.py"
    fetch_script "$URL_COTUBE" "$COTUBE_PATH" "Co-tube.py"
    nl; line_warn "Co-flix.py — màj manuelle uniquement"
    nl; pause
}

# ═══════════════════════════════════════════════════════════════════════════════
#  VÉRIFICATION TERMUX
# ═══════════════════════════════════════════════════════════════════════════════
if [ ! -d "/data/data/com.termux" ]; then
    banner; nl
    line_err "Ce script est réservé à Termux (Android)."; nl; exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  BOUCLE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════
while true; do
    print_menu
    read -r choice

    case "$choice" in
        1) clr; banner; fetch_script "$URL_COMENU" "$COMENU_PATH" "Co-Menu.py";  nl; pause ;;
        2) clr; banner; fetch_script "$URL_COCHAN" "$COCHAN_PATH" "Co-chan.py";   nl; pause ;;
        3) clr; banner; fetch_script "$URL_COTUBE" "$COTUBE_PATH" "Co-tube.py";  nl; pause ;;
        4) full_install ;;
        5) update_all_scripts ;;
        6) clr; banner; setup_storage;   nl; pause ;;
        7) clr; banner; setup_shortcuts; setup_alias; nl; pause ;;
        8) clr; banner; delete_animes;   nl; pause ;;
        9) uninstall_all; nl; pause ;;
        0|q|"")
            clr; banner; nl
            echo -e "  ${C1}${BOLD}À bientôt ! ${RESET}${DIM}— CO-TEAM  ${EMOJI}${RESET}"; nl
            exit 0 ;;
        *)
            line_warn "Choix invalide (0–9)"; sleep 0.5 ;;
    esac
done
