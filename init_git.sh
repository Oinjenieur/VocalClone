#!/bin/bash

echo "Initialisation d'un nouveau dépôt Git pour VocalClone..."

# Supprimer l'ancien répertoire .git si existant
if [ -d ".git" ]; then
    echo "Suppression de l'ancien dépôt Git..."
    rm -rf .git
fi

# Initialiser un nouveau dépôt
echo "Initialisation d'un nouveau dépôt Git..."
git init

# Configurer les informations de l'utilisateur si non définies
if ! git config --get user.name > /dev/null 2>&1; then
    echo -n "Entrez votre nom pour Git: "
    read GIT_NAME
    git config user.name "$GIT_NAME"
fi

if ! git config --get user.email > /dev/null 2>&1; then
    echo -n "Entrez votre email pour Git: "
    read GIT_EMAIL
    git config user.email "$GIT_EMAIL"
fi

# Ajouter tous les fichiers
echo "Ajout des fichiers au dépôt..."
git add .

# Premier commit
echo "Création du premier commit..."
git commit -m "Initial commit pour VocalClone"

echo ""
echo "===================================================="
echo "Dépôt Git initialisé avec succès !"
echo ""
echo "Étapes suivantes :"
echo "1. Exécutez les commandes suivantes pour le lier :"
echo "   git remote add origin https://github.com/Oinjenieur/VocalClone.git"
echo "   git push -u origin main"
echo "===================================================="
echo "" 