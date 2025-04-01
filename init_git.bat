@echo off
echo Initialisation d'un nouveau dépôt Git pour VocalClone...

REM Supprimer l'ancien répertoire .git si existant
if exist .git (
    echo Suppression de l'ancien dépôt Git...
    rmdir /s /q .git
)

REM Initialiser un nouveau dépôt
echo Initialisation d'un nouveau dépôt Git...
git init

REM Configurer les informations de l'utilisateur si non définies
git config --get user.name >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set /p GIT_NAME="Entrez votre nom pour Git: "
    git config user.name "%GIT_NAME%"
)

git config --get user.email >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set /p GIT_EMAIL="Entrez votre email pour Git: "
    git config user.email "%GIT_EMAIL%"
)

REM Ajouter tous les fichiers
echo Ajout des fichiers au dépôt...
git add .

REM Premier commit
echo Création du premier commit...
git commit -m "Initial commit pour VocalClone"

echo.
echo ====================================================
echo Dépôt Git initialisé avec succès !
echo.
echo Étapes suivantes :
echo 1. Exécutez les commandes suivantes pour le lier :
echo    git remote add origin https://github.com/Oinjenieur/VocalClone.git
echo    git push -u origin main
echo ====================================================
echo. 