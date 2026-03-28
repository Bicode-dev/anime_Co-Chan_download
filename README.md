<div align="center">

```
 ██████╗ ██████╗       ██████╗██╗  ██╗ █████╗ ███╗   ██╗
██╔════╝██╔═══██╗    ██╔════╝██║  ██║██╔══██╗████╗  ██║
██║     ██║   ██║    ██║     ███████║███████║██╔██╗ ██║
██║     ██║   ██║    ██║     ██╔══██║██╔══██║██║╚██╗██║
╚██████╗╚██████╔╝    ╚██████╗██║  ██║██║  ██║██║ ╚████║
 ╚═════╝ ╚═════╝      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
```

### Téléchargeur Anime VF & VOSTFR — Multi-Serveurs

[![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Plateforme](https://img.shields.io/badge/Plateforme-Windows%20|%20Android-green?style=for-the-badge&logo=windows)](https://github.com/Bicode-dev/anime_Co-Chan_download)
[![Licence](https://img.shields.io/badge/Licence-CC%20BY--NC--ND%204.0-orange?style=for-the-badge)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
[![Discord](https://img.shields.io/badge/Discord-Rejoindre-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/cG6qSTSeUA)
[![Télécharger](https://img.shields.io/badge/Télécharger-Co--Chan.exe-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Bicode-dev/anime_Co-Chan_download/releases/download/Co-Chan_(%E2%97%8F'%E2%97%A1'%E2%97%8F)/Co-Chan.exe)

> *« Les droits humains compteront toujours plus que les droits d'auteur. »*
> — Bicode-dev, 2026

**Co-Chan** est un téléchargeur d'animes rapide, portable et open-source.
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
# Cloner le dépôt
git clone https://github.com/Bicode-dev/anime_Co-Chan_download

# Lancer directement
python Co-chan.py
```

### 📱 Android (Termux)

```bash
bash Co-chan_download_termux.sh
```

---

## 🚀 Utilisation

L'interface s'ouvre directement en double-cliquant sur le `.exe` ou le `.py`.
La ligne de commande est **optionnelle** :

```bash
# Télécharger One Piece en VF
python Co-chan.py "one piece" vf

# Télécharger Naruto Shippuden en VOSTFR
python Co-chan.py "naruto shippuden" vostfr

# Afficher l'aide
python Co-chan.py --help
```

| Commande | Description |
|----------|-------------|
| `python Co-chan.py "nom" vf` | Téléchargement en Voix Françaises |
| `python Co-chan.py "nom" vostfr` | Téléchargement en Sous-titres Français |
| `python Co-chan.py --help` | Afficher toutes les options disponibles |

---

## ✨ Fonctionnalités

| | Fonctionnalité | Détail |
|--|----------------|--------|
| ⚡ | **Vitesse maximale** | Téléchargement direct sans limitation de bande passante |
| 🌐 | **Multi-serveurs** | Sibnet, Vidmoly & Sendvid — sélection automatique |
| 🇫🇷 | **VF & VOSTFR** | Choix instantané de la version audio/sous-titres |
| 🔁 | **Reprise automatique** | Reprend là où il s'est arrêté si interrompu |
| 📦 | **Portable** | Aucune installation — double-clic et c'est parti |
| 📱 | **Multi-plateforme** | Windows & Android (Termux) |
| 🔓 | **Open Source** | Code 100% visible sur GitHub |
| 🆓 | **Gratuit** | Actuellement gratuit *(susceptible de devenir payant)* |

---

## 🌐 Serveurs supportés

Co-Chan interroge ces serveurs dans l'ordre et choisit automatiquement le plus rapide :

| Serveur | Type | Statut |
|---------|------|--------|
| **Sibnet** | Serveur russe haute vitesse | 🟢 Actif |
| **Vidmoly** | Serveur international stable | 🟢 Actif |
| **Sendvid** | Serveur de secours fiable | 🟢 Actif |

> En cas de problème lié aux droits d'auteur, adressez-vous directement à l'hébergeur concerné.

---

## 🔢 Démarrage en 4 étapes

```
01 — TÉLÉCHARGEZ   →   Récupérez Co-Chan.exe depuis GitHub
02 — LANCEZ        →   Double-cliquez, aucune installation requise
03 — RECHERCHEZ    →   Entrez le nom + la version  (ex: "one piece vf")
04 — PROFITEZ      →   Les épisodes arrivent directement dans le dossier
```

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

Oui ! Un script d'installation Termux est disponible dans le dépôt GitHub. L'interface bascule automatiquement sur un menu adapté à la saisie mobile.
</details>

<details>
<summary><b>Comment le serveur est-il sélectionné ?</b></summary>

Co-Chan teste Sibnet, Vidmoly et Sendvid dans l'ordre, puis choisit automatiquement le premier qui répond le plus vite. Aucune configuration manuelle nécessaire.
</details>

<details>
<summary><b>Que faire si un épisode n'est pas disponible ?</b></summary>

Si aucun serveur ne dispose de l'épisode, Co-Chan vous l'indique clairement. La disponibilité dépend des hébergeurs tiers, sur lesquels nous n'avons aucun contrôle.
</details>

---

## 🎬 Scène de ménage — L'histoire derrière Co-Chan

> *Quelque part dans un serveur Discord à 2h du matin...*
> *Il avait tout codé seul. Puis un jour, quelqu'un a tout rework. Et maintenant, il veut récupérer ce qui lui appartient.*

---

```
┌─────────────────────────────────────────────────────────────┐
│  🌸  CO-CHAN — BEHIND THE SCENES                            │
└─────────────────────────────────────────────────────────────┘
```

<img src="https://avatars.githubusercontent.com/u/66554006?v=4" width="40" style="border-radius:50%;vertical-align:middle;"> **[@lesjeuxmathis](https://github.com/lesjeuxmathis)** *(créateur — pose son café, l'air nostalgique)*

> « J'ai créé Co-Chan from scratch. Seul. L'ancien script c'était le mien,
> dans ma tête, dans mes mains. Simple, direct, brutal — mais il marchait. »

---

<img src="https://avatars.githubusercontent.com/u/140495864?v=4" width="40" style="border-radius:50%;vertical-align:middle;"> **[@Colmax06](https://github.com/Colmax06)** *(contributeur — se retourne depuis son écran)*

> « Tu m'as laissé le rework complet. J'ai tout refactorisé, structuré,
> rendu propre. T'as continué de patcher par-dessus après. »

---

<img src="https://avatars.githubusercontent.com/u/66554006?v=4" width="40" style="border-radius:50%;vertical-align:middle;"> **[@lesjeuxmathis](https://github.com/lesjeuxmathis)** — *acquiesce lentement*

> « Ouais. Et j'ai continué à maintenir le nouveau, les patches,
> les corrections... Mais l'ancien script, lui, il dort quelque part.
> Et cette fois je veux le ressortir. **Seul. Avec la main totale dessus.** »

---

<img src="https://avatars.githubusercontent.com/u/140495864?v=4" width="40" style="border-radius:50%;vertical-align:middle;"> **[@Colmax06](https://github.com/Colmax06)** — *lève un sourcil*

> « Donc t'aurais deux versions en parallèle ? »

---

<img src="https://avatars.githubusercontent.com/u/66554006?v=4" width="40" style="border-radius:50%;vertical-align:middle;"> **[@lesjeuxmathis](https://github.com/lesjeuxmathis)** — *sourire*

> « Exactement. Le nouveau pour les gens qui veulent du propre.
> L'ancien pour ceux qui veulent l'original — **tel que je l'ai voulu dès le début.** »

---

<img src="https://avatars.githubusercontent.com/u/140495864?v=4" width="40" style="border-radius:50%;vertical-align:middle;"> **[@Colmax06](https://github.com/Colmax06)** — *pause... hoche la tête*

> « Honnêtement ? C'est pas con. »

---

```
  [ Fin de la scène ]
  [ L'old script va bientôt ressortir. Cette fois, sous le contrôle total de son créateur. ]
```

> 📜 **Histoire du projet :**
> Co-Chan a été **créé** par [@lesjeuxmathis](https://github.com/lesjeuxmathis).
> Le code a été **reworké** par [@Colmax06](https://github.com/Colmax06).
> Les **patches** du nouveau code ont été assurés par [@lesjeuxmathis](https://github.com/lesjeuxmathis).
> L'**old script** revient bientôt — cette fois entre les mains de son auteur original.

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
