@echo off
title Mise en place ..
setlocal enabledelayedexpansion

:: Fonction pour vérifier l'installation de Python
call :check_python

:: Vérifier si pip est installé
call :check_pip

:: Vérifier si youtube-dl est installé et sa version
call :check_youtube_dl

:: Télécharger le fichier .py depuis l'URL GitHub
call :download_file

:: Supprimer le fichier .bat après l'exécution
echo [INFO] Suppression du fichier batch...
del "%~f0"

:: Terminer le script
pause
exit /b

:: ----------------------------------------
:: Fonction pour vérifier l'installation de Python
:check_python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installé.
    echo [INFO] Téléchargez et installez Python depuis https://www.python.org/downloads/
    pause
    exit /b
)
goto :eof

:: Fonction pour vérifier si pip est installé
:check_pip
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Pip n'est pas installé.
    echo [INFO] Installation de pip...
    python -m ensurepip
    python -m pip install --upgrade pip
)
goto :eof

:: Fonction pour vérifier si youtube-dl est installé et sa version
:check_youtube_dl
for /f "delims=" %%v in ('python -m youtube_dl --version 2^>nul') do set YDL_VERSION=%%v

if not defined YDL_VERSION (
    echo [ERREUR] youtube-dl n'est pas installé.
    echo [INFO] Installation de youtube-dl...
    python -m pip install requests
    python -m pip install youtube-dl
    set YDL_VERSION=2021.12.17
) else (
    echo [INFO] youtube-dl installé : version %YDL_VERSION%
)

:: Vérifier la version correcte de youtube-dl
if not "%YDL_VERSION%"=="2021.12.17" (
    echo [ERREUR] Version incorrecte de youtube-dl : %YDL_VERSION%
    echo [INFO] Mise à jour vers la version 2021.12.17...
    python -m pip install --force-reinstall youtube-dl==2021.12.17
    echo [OK] Mise à jour effectuée !
) else (
    echo [OK] La version de youtube-dl est correcte.
)
goto :eof

:: Fonction pour télécharger le fichier
:download_file
echo [INFO] Téléchargement du fichier .py depuis l'URL GitHub...
set URL=https://raw.githubusercontent.com/les-developpeur/anime-soma/refs/heads/main/Anime-dowload.py
set FILE_NAME=anime-dowload.py

curl -o %FILE_NAME% %URL%

:: Vérifier si le fichier a bien été téléchargé
if exist %FILE_NAME% (
    echo [OK] Le fichier %FILE_NAME% a été téléchargé avec succès.
    msg %username% %FILE_NAME% a ete mis en place avec succes.
) else (
    echo [ERREUR] Le téléchargement a échoué.
    pause
    exit /b
)
goto :eof
