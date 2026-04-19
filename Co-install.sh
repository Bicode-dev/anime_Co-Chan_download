#!/data/data/com.termux/files/usr/bin/bash
# ── Co-Chan Installer ─────────────────────────────────────────────────────────

RESET='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'
C1='\033[38;5;183m'
OK="${C1}✔${RESET}"; WARN='\033[38;5;228m'"⚠${RESET}"; ERR='\033[38;5;203m'"✘${RESET}"

URL_NEW="https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/Co-chan.py"
URL_OLD="https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/Old_script.py"

DIR="$HOME/.local/share/CoChan"
SCRIPT="$DIR/Co-chan.py"
VERFILE="$DIR/.version"
CHOSEN_URL=""

# ── Helpers ───────────────────────────────────────────────────────────────────
nl()   { echo ""; }
ok()   { echo -e "  ${OK}  $1"; }
warn() { echo -e "  ${WARN}  $1"; }
err()  { echo -e "  ${ERR}  $1"; }
info() { echo -e "  ${DIM}›  $1${RESET}"; }
sep()  { echo -e "  ${DIM}────────────────────────────────${RESET}"; }
pause(){ printf "\n  ${DIM}Entrée pour continuer...${RESET} "; read -r; }

remote_size() {
    curl -sLI "$1" 2>/dev/null | grep -i "^content-length:" | tail -1 | awk '{print $2}' | tr -d '\r\n'
}

# ── Statut Co-chan ────────────────────────────────────────────────────────────
cochan_status() {
    local ver="Nouvelle (TUI)"
    [ -f "$VERFILE" ] && [ "$(cat "$VERFILE")" = "old" ] && ver="Ancienne (console)"

    if [ ! -f "$SCRIPT" ]; then
        echo -e "  ${ERR}  Co-chan.py  ${DIM}non installé${RESET}"; return
    fi

    local url; url=$(get_url)
    local lsize; lsize=$(wc -c < "$SCRIPT" | tr -d ' ')
    local rsize; rsize=$(remote_size "$url")
    local ldate; ldate=$(date -r "$SCRIPT" "+%d/%m %H:%M" 2>/dev/null || echo "—")
    local ksize=$(( lsize / 1024 ))

    if [ -z "$rsize" ] || [ "$rsize" = "0" ]; then
        echo -e "  ${WARN}  Co-chan.py  ${DIM}${ksize}Ko · ${ldate} · ${ver} · (réseau indisponible)${RESET}"
        return
    fi

    local diff=$(( rsize - lsize < 0 ? lsize - rsize : rsize - lsize ))
    if [ "$diff" -le 1 ]; then
        echo -e "  ${OK}  Co-chan.py  ${DIM}${ksize}Ko · ${ldate} · ${ver}${RESET}"
    else
        echo -e "  ${WARN}  Co-chan.py  ${DIM}${ksize}Ko · ${ldate} · ${ver} · mise à jour disponible${RESET}"
    fi
}

# ── Version ───────────────────────────────────────────────────────────────────
get_url() {
    [ -f "$VERFILE" ] && [ "$(cat "$VERFILE")" = "old" ] && echo "$URL_OLD" || echo "$URL_NEW"
}

choose_version() {
    nl
    local cur=""; [ -f "$VERFILE" ] && cur=$(cat "$VERFILE")
    echo -e "  ${C1}${BOLD}[1]${RESET}  Nouvelle  ${DIM}interface TUI (recommandée)${RESET}"
    echo -e "  ${C1}${BOLD}[2]${RESET}  Ancienne  ${DIM}console uniquement${RESET}"
    nl
    [ -n "$cur" ] && printf "  Choix ${DIM}[Entrée = garder l'actuelle]${RESET} : " || printf "  Choix : "
    read -r v

    mkdir -p "$DIR"
    case "$v" in
        1) echo "new" > "$VERFILE"; CHOSEN_URL="$URL_NEW"; info "Nouvelle (TUI) sélectionnée" ;;
        2) echo "old" > "$VERFILE"; CHOSEN_URL="$URL_OLD"; info "Ancienne (console) sélectionnée" ;;
        "") [ "$cur" = "old" ] && CHOSEN_URL="$URL_OLD" || { echo "new" > "$VERFILE"; CHOSEN_URL="$URL_NEW"; }
            info "Version conservée" ;;
        *) echo "new" > "$VERFILE"; CHOSEN_URL="$URL_NEW"; warn "Invalide — version nouvelle utilisée" ;;
    esac
}

# ── Téléchargement ────────────────────────────────────────────────────────────
fetch() {
    local url="$1" dest="$2"; nl
    local rsize; rsize=$(remote_size "$url")

    if [ -f "$dest" ] && [ -n "$rsize" ] && [ "$rsize" != "0" ]; then
        local lsize; lsize=$(wc -c < "$dest" | tr -d ' ')
        local diff=$(( rsize - lsize < 0 ? lsize - rsize : rsize - lsize ))
        [ "$diff" -le 1 ] && ok "Co-chan.py — déjà à jour" && return 0
        info "Mise à jour en cours..."
    else
        info "Téléchargement en cours..."
    fi

    mkdir -p "$(dirname "$dest")"
    if curl -sL -o "$dest" "$url"; then
        chmod +x "$dest"
        ok "Co-chan.py — OK  ${DIM}($(( $(wc -c < "$dest" | tr -d ' ') / 1024 ))Ko)${RESET}"
    else
        err "Échec du téléchargement"; return 1
    fi
}

# ── Paquets ───────────────────────────────────────────────────────────────────
install_packages() {
    info "Mise à jour Termux..."; pkg update -y -q && pkg upgrade -y -q; ok "Paquets système à jour"; nl
    for p in python git curl; do
        pkg list-installed 2>/dev/null | grep -q "^${p}/" \
            && ok "${p}  ${DIM}déjà installé${RESET}" \
            || { info "Installation de ${p}..."; pkg install "$p" -y -q && ok "$p" || warn "$p — échec"; }
    done; nl
    pip install --upgrade pip -q && ok "pip à jour"; nl
    for lib in requests yt-dlp textual rich Pillow; do
        pip show "$lib" >/dev/null 2>&1 \
            && ok "${lib}  ${DIM}$(pip show "$lib" 2>/dev/null | grep "^Version:" | awk '{print $2}')${RESET}" \
            || { info "Installation de ${lib}..."; pip install "$lib" -q && ok "$lib" || warn "$lib — échec"; }
    done
}

# ── Stockage ──────────────────────────────────────────────────────────────────
setup_storage() {
    if [ ! -d "$HOME/storage" ]; then
        info "Ouverture de termux-setup-storage..."
        termux-setup-storage && ok "Stockage configuré"
    else
        ok "Stockage déjà configuré"
    fi
    mkdir -p "/storage/emulated/0/Download/anime" 2>/dev/null \
        && ok "Dossier anime prêt" \
        || warn "Dossier non créé — vérifiez les permissions"
}

# ── Alias & raccourcis ────────────────────────────────────────────────────────
setup_alias() {
    mkdir -p "$HOME/.shortcuts"

    cat > "$HOME/.shortcuts/CO-CHAN.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
python3 ~/.local/share/CoChan/Co-chan.py
EOF
    cat > "$HOME/.shortcuts/CO-UPDATE.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
curl -sL https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/Co-install.sh | bash
EOF
    cat > "$HOME/.shortcuts/RM-ANIME.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
DIR="/storage/emulated/0/Download/anime"
count=$(find "$DIR" -name "*.mp4" 2>/dev/null | wc -l)
echo "Animes trouvés : $count"
read -p "Supprimer ? (o/n) : " c
[ "$c" = "o" ] && rm -rf "$DIR"/* && echo "Supprimé" || echo "Annulé"
EOF
    chmod +x "$HOME/.shortcuts/CO-CHAN.sh" "$HOME/.shortcuts/CO-UPDATE.sh" "$HOME/.shortcuts/RM-ANIME.sh"
    ok "Raccourcis Termux:Widget créés"

    sed -i '/# ── CO-CHAN START/,/# ── CO-CHAN END/d' "$HOME/.bashrc" 2>/dev/null
    cat >> "$HOME/.bashrc" << 'ALIASES'
# ── CO-CHAN START ──────────────────────────────────────
alias anime="python3 ~/.local/share/CoChan/Co-chan.py"
alias coupdate="bash ~/.shortcuts/CO-UPDATE.sh"
alias rmanime="bash ~/.shortcuts/RM-ANIME.sh"
# ── CO-CHAN END ────────────────────────────────────────
ALIASES
    ok "Alias créés  ${DIM}(anime · coupdate · rmanime)${RESET}"
    warn "Tape  ${BOLD}source ~/.bashrc${RESET}  ou redémarre Termux"
}

# ── Suppression animes ────────────────────────────────────────────────────────
delete_animes() {
    local D="/storage/emulated/0/Download/anime"
    [ ! -d "$D" ] && warn "Dossier introuvable : $D" && return
    local n; n=$(find "$D" -name "*.mp4" 2>/dev/null | wc -l)
    local s; s=$(du -sh "$D" 2>/dev/null | cut -f1)
    nl; echo -e "  ${DIM}$n fichier(s)  ·  $s${RESET}"; nl
    printf "  Confirmer la suppression ? (oui/non) : "; read -r cf
    [ "$cf" = "oui" ] && rm -rf "$D"/* && ok "$n fichier(s) supprimé(s)" || info "Annulé"
}

# ── Désinstallation ───────────────────────────────────────────────────────────
uninstall() {
    nl; echo -e "  ${DIM}Supprime : ~/.local/share/CoChan/  ·  raccourcis  ·  alias${RESET}"; nl
    printf "  Confirmer ? (oui/non) : "; read -r cf
    if [ "$cf" = "oui" ]; then
        rm -rf "$DIR"
        rm -f "$HOME/.shortcuts/CO-CHAN.sh" "$HOME/.shortcuts/CO-UPDATE.sh" "$HOME/.shortcuts/RM-ANIME.sh"
        sed -i '/# ── CO-CHAN START/,/# ── CO-CHAN END/d' "$HOME/.bashrc" 2>/dev/null
        ok "Co-Chan désinstallé"
    else
        info "Annulé"
    fi
}

# ── Vérification Termux ───────────────────────────────────────────────────────
if [ ! -d "/data/data/com.termux" ]; then
    err "Ce script est réservé à Termux."; exit 1
fi

# ── Boucle principale ─────────────────────────────────────────────────────────
while true; do
    clear; nl
    echo -e "  ${C1}${BOLD}Co-Chan${RESET}  ${DIM}Installateur Termux${RESET}"
    sep; cochan_status; sep; nl
    echo -e "  ${C1}${BOLD}[1]${RESET}  Installer / mettre à jour"
    echo -e "  ${C1}${BOLD}[2]${RESET}  Installation complète  ${DIM}paquets + script + config${RESET}"
    echo -e "  ${C1}${BOLD}[3]${RESET}  Stockage Android"
    echo -e "  ${C1}${BOLD}[4]${RESET}  Alias & raccourcis"
    echo -e "  ${C1}${BOLD}[5]${RESET}  Supprimer les animes"
    echo -e "  ${C1}${BOLD}[6]${RESET}  Désinstaller"
    nl; sep
    echo -e "  ${DIM}[0]  Quitter${RESET}"
    sep; nl; printf "  Choix : "; read -r choice; nl

    case "$choice" in
        1) choose_version; fetch "$CHOSEN_URL" "$SCRIPT"; pause ;;
        2) install_packages; nl; choose_version; fetch "$CHOSEN_URL" "$SCRIPT"; nl
           setup_storage; nl; setup_alias
           nl; ok "Installation terminée  ${DIM}—  lance Co-Chan avec :  anime${RESET}"; pause ;;
        3) setup_storage;  pause ;;
        4) setup_alias;    pause ;;
        5) delete_animes;  pause ;;
        6) uninstall;      pause ;;
        0|q|"") nl; info "À bientôt !"; nl; exit 0 ;;
        *) warn "Choix invalide"; sleep 0.5 ;;
    esac
done
