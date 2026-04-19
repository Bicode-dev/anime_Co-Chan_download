<div align="center">

```
 ██████╗ ██████╗       ██████╗██╗  ██╗ █████╗ ███╗   ██╗
██╔════╝██╔═══██╗    ██╔════╝██║  ██║██╔══██╗████╗  ██║
██║     ██║   ██║    ██║     ███████║███████║██╔██╗ ██║
██║     ██║   ██║    ██║     ██╔══██║██╔══██║██║╚██╗██║
╚██████╗╚██████╔╝    ╚██████╗██║  ██║██║  ██║██║ ╚████║
 ╚═════╝ ╚═════╝      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
```

### Téléchargeur Anime VF & VOSTFR — Interface TUI Multi-Serveurs

[![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Plateforme](https://img.shields.io/badge/Plateforme-Windows%20|%20Linux%20|%20macOS%20|%20Android-green?style=for-the-badge)](https://github.com/Bicode-dev/anime_Co-Chan_download)
[![Licence](https://img.shields.io/badge/Licence-CC%20BY--NC--ND%204.0-orange?style=for-the-badge)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
[![Discord](https://img.shields.io/badge/Discord-Rejoindre-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/cG6qSTSeUA)
[![Télécharger](https://img.shields.io/badge/Télécharger-Co--Chan.exe-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Bicode-dev/anime_Co-Chan_download/releases/download/Co-Chan_(%E2%97%8F'%E2%97%A1'%E2%97%8F)/Co-Chan.exe)

> *« Les droits humains compteront toujours plus que les droits d'auteur. »*
> — Bicode-dev, 2026

**Co-Chan** est un téléchargeur d'animes rapide, portable et open-source doté d'une interface TUI (Terminal UI) complète.
Il extrait directement les épisodes depuis plusieurs serveurs d'hébergement (Sibnet, Vidmoly, Sendvid…) et sélectionne automatiquement le meilleur disponible.

🇫🇷 **Français uniquement** — VF (Voix Françaises) et VOSTFR (Sous-titres Français)

</div>

---

## 📥 Installation

### 🖥️ Windows

**Option 1 — Exécutable (recommandé)**

Téléchargez directement `Co-Chan.exe` et double-cliquez dessus. Aucune installation, aucune dépendance.

[![Télécharger Co-Chan.exe](https://img.shields.io/badge/⬇%20Télécharger%20Co--Chan.exe-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Bicode-dev/anime_Co-Chan_download/releases/download/Co-Chan_(%E2%97%8F'%E2%97%A1'%E2%97%8F)/Co-Chan.exe)

**Option 2 — Script Python**
```bash
git clone https://github.com/Bicode-dev/anime_Co-Chan_download
python Co-chan.py
```

### 🐧 Linux / 🍎 macOS

```bash
git clone https://github.com/Bicode-dev/anime_Co-Chan_download
python3 Co-chan.py
```

Les dépendances (`textual`, `yt-dlp`, `requests`, `rich`) s'installent automatiquement au premier lancement. `ffmpeg` est également téléchargé automatiquement si absent.

### 📱 Android (Termux)

```bash
bash Co-install.sh
```

---

## 🚀 Utilisation

Co-Chan s'utilise entièrement via son interface TUI — aucune ligne de commande nécessaire.

**Lancez le script ou l'exécutable**, puis naviguez avec les touches :

| Touche | Action |
|--------|--------|
| `↑` `↓` | Naviguer dans les menus |
| `Entrée` | Valider |
| `Échap` | Retour |

---

## 🔢 Démarrage en 4 étapes

```
01 — TÉLÉCHARGEZ   →   Récupérez Co-Chan.exe depuis GitHub
02 — LANCEZ        →   Double-cliquez, aucune installation requise
03 — RECHERCHEZ    →   Tapez le nom de l'anime dans l'interface
04 — PROFITEZ      →   Les épisodes arrivent directement dans le dossier
```

---

## ✨ Fonctionnalités

| | Fonctionnalité | Détail |
|--|----------------|--------|
| ⚡ | **Vitesse maximale** | Téléchargement direct sans limitation de bande passante |
| 🖥️ | **Interface TUI** | Navigation clavier fluide, menus interactifs |
| 🌐 | **Multi-serveurs** | Sibnet, Vidmoly & Sendvid — sélection automatique |
| 🇫🇷 | **VF & VOSTFR** | Choix instantané de la version audio/sous-titres |
| 🔁 | **Reprise automatique** | Reprend là où il s'est arrêté si interrompu |
| 📦 | **Portable** | Aucune installation — double-clic et c'est parti |
| 🔧 | **ffmpeg auto** | Téléchargé et configuré automatiquement si absent |
| ⚙️ | **Config persistante** | Dossier de téléchargement et qualité mémorisés |
| 📱 | **Multi-plateforme** | Windows, Linux, macOS & Android (Termux) |
| 🔓 | **Open Source** | Code 100% visible sur GitHub |
| 🆓 | **Gratuit** | Actuellement gratuit *(susceptible de devenir payant)* |

---

## 🌐 Serveurs supportés

Co-Chan interroge ces serveurs et choisit automatiquement le meilleur disponible :

| Serveur | Type | Statut |
|---------|------|--------|
| **Sibnet** | Serveur russe haute vitesse | 🟢 Actif |
| **Vidmoly** | Serveur international stable | 🟢 Actif |
| **Sendvid** | Serveur de secours fiable | 🟢 Actif |

> En cas de problème lié aux droits d'auteur, adressez-vous directement à l'hébergeur concerné.

---

## ❓ FAQ

<details>
<summary><b>Est-ce légal ?</b></summary>

Co-Chan télécharge uniquement des fichiers déjà publics sur des serveurs tiers. L'usage reste sous votre responsabilité.
</details>

<details>
<summary><b>Windows Defender bloque le fichier ?</b></summary>

Co-Chan ne devrait jamais déclencher Windows Defender. Si une alerte apparaît, **ne lancez pas le fichier** et signalez-le immédiatement sur le Discord.
</details>

<details>
<summary><b>Une version Android est-elle disponible ?</b></summary>

Oui ! Un script d'installation Termux est disponible dans le dépôt GitHub. L'interface s'adapte automatiquement à Termux.
</details>

<details>
<summary><b>Comment le serveur est-il sélectionné ?</b></summary>

Co-Chan teste Sibnet, Vidmoly et Sendvid en parallèle et choisit automatiquement le plus rapide. Aucune configuration manuelle nécessaire.
</details>

<details>
<summary><b>Que faire si un épisode n'est pas disponible ?</b></summary>

Si aucun serveur ne dispose de l'épisode, Co-Chan vous l'indique clairement. La disponibilité dépend des hébergeurs tiers, sur lesquels nous n'avons aucun contrôle.
</details>

<details>
<summary><b>ffmpeg est-il nécessaire ?</b></summary>

Non — Co-Chan le télécharge et le configure automatiquement si ffmpeg n'est pas présent sur votre système.
</details>

---

> 📜 **Histoire du projet :**
> Co-Chan a été **créé** par [@lesjeuxmathis](https://github.com/lesjeuxmathis).
> Le code a été un peu reworké par [@Colmax06](https://github.com/Colmax06).
> Les **patches et la maintenance** du nouveau code ont été assurés par [@lesjeuxmathis](https://github.com/lesjeuxmathis).

---

## 💬 Support

[![Discord](https://img.shields.io/badge/Rejoindre%20le%20serveur-Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/cG6qSTSeUA)

Support instantané · Mises à jour · Communauté active

---

## ⚖️ Licence & DMCA

Ce logiciel est protégé par la licence **[CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/)**.
Toute utilisation commerciale, modification ou redistribution est **strictement interdite**.

> **DMCA** — Si vous estimez qu'un contenu accessible via ce logiciel porte atteinte à vos droits, contactez directement la plateforme hébergeant ce contenu. Toute demande doit être adressée aux services d'hébergement concernés.

---

<div align="center">

<img src="https://github.com/user-attachments/assets/1aa3b128-1344-4a8d-8959-ccef45922c1a" width="20"> **Co-Chan** · Par [Bicode_DEV](https://github.com/Bicode-dev) · 2026

[🌐 Site Web](https://bicode-dev.github.io/Co-Chan-Anime-Downloader-web/) · [📦 Releases](https://github.com/Bicode-dev/anime_Co-Chan_download/releases) · [💬 Discord](https://discord.gg/cG6qSTSeUA)

</div>
