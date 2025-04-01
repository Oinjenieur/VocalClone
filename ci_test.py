#!/usr/bin/env python
"""
Script de test minimal pour le CI.
Ce script vérifie que la structure du projet est correcte et que les fichiers essentiels existent.
"""

import os
import sys

def check_file_exists(path):
    """Vérifie si un fichier existe"""
    if not os.path.exists(path):
        print(f"ERREUR: Le fichier {path} n'existe pas")
        return False
    return True

def check_dir_exists(path):
    """Vérifie si un répertoire existe"""
    if not os.path.isdir(path):
        print(f"ERREUR: Le répertoire {path} n'existe pas")
        return False
    return True

def main():
    """Fonction principale"""
    print("Vérification de la structure du projet VocalClone...")
    
    # Répertoires essentiels
    essential_dirs = [
        "src",
        "src/core",
        "src/gui",
        "src/utils",
        "resources"
    ]
    
    # Fichiers essentiels
    essential_files = [
        "src/main.py",
        "requirements.txt",
        "README.md",
        "LICENSE"
    ]
    
    # Vérifier les répertoires
    all_dirs_exist = all(check_dir_exists(d) for d in essential_dirs)
    
    # Vérifier les fichiers
    all_files_exist = all(check_file_exists(f) for f in essential_files)
    
    if all_dirs_exist and all_files_exist:
        print("Test réussi ! La structure du projet est correcte.")
        return 0
    else:
        print("Test échoué. Certains fichiers ou répertoires essentiels sont manquants.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 