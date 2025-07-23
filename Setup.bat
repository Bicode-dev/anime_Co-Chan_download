@echo off
title Mise en place ..
setlocal enabledelayedexpansion
set "newname=Mise_a_jour.bat"

:: Verifier l'installation de Python
call :check_python

:: Verifier si pip est installe
call :check_pip

:: Verifier si yt-dlp et autres modules sont installes
call :check_python_packages

:: Telecharger le fichier .py depuis l'URL GitHub
call :download_file

echo [INFO] Adaptation du fichier batch...
ren "%~f0" "%newname%"

:: Terminer le script
pause
exit /b

:: ----------------------------------------
:: Fonction pour verifier l'installation de Python
:check_python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe.
    echo [INFO] Telechargez et installez Python depuis https://www.python.org/downloads/
    pause
    exit /b
)
goto :eof

:: Fonction pour verifier si pip est installe
:check_pip
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Pip n'est pas installe.
    echo [INFO] Installation de pip...
    python -m ensurepip
    python -m pip install --upgrade pip
)
goto :eof

:: Fonction pour verifier et installer les packages Python (NON MODIFIeE)
:check_python_packages
set PACKAGES=yt-dlp requests beautifulsoup4 numpy tkinter

for %%p in (%PACKAGES%) do (
    python -c "import %%p" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [INFO] Installation de %%p...
        pip install yt-dlp
        pip install requests 
        pip install beautifulsoup4 
        pip install numpy
        pip install tkinter
    ) else (
        echo [INFO] Le package %%p est deja installe.
        pip install yt-dlp
        pip install requests 
        pip install beautifulsoup4 
        pip install numpy
        pip install tkinter
    )
)
goto :eof

:: Fonction pour telecharger les fichiers depuis GitHub
:download_file
pip install -U yt-dlp
cls
echo [INFO] Telechargement des fichiers depuis GitHub...

:: Definition des URLs
set URL_SCRIPT=https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/Anime-dowload.py
set FILE_SCRIPT=anime-dowload.py
set URL_GUI=https://raw.githubusercontent.com/Bicode-dev/anime_Co-Chan_download/refs/heads/main/gui_windows.pyw
set FILE_GUI=gui_windows-30%%-moin-rapide-mais-plus-beau.pyw

:: Telecharger les fichiers
curl -o %FILE_SCRIPT% %URL_SCRIPT%
curl -o %FILE_GUI% %URL_GUI%

:: Attendre un instant pour s'assurer du telechargement
timeout /t 2 /nobreak >nul

:: Verifier si les fichiers ont bien ete telecharges
if exist %FILE_SCRIPT% (
    echo [OK] Le fichier %FILE_SCRIPT% a ete telecharge avec succes.
) else (
    echo [ERREUR] echec du telechargement de %FILE_SCRIPT%.
    pause
    exit /b
)

if exist %FILE_GUI% (
    echo [OK] Le fichier %FILE_GUI% a ete telecharge avec succes.
) else (
    echo [ERREUR] echec du telechargement de %FILE_GUI%.
    pause
    exit /b
)

:: Notification a l'utilisateur
msg %username% "Les fichiers ont ete telecharges avec succes."

goto :eof
