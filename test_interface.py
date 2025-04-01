#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Ajouter le chemin du projet
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'src'))

from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def main():
    print("Démarrage de l'application Vocal Clone...")
    
    # Créer l'application Qt
    app = QApplication(sys.argv)
    
    # Créer et afficher la fenêtre principale
    print("Création de la fenêtre principale...")
    window = MainWindow()
    
    # Afficher la fenêtre
    print("Affichage de la fenêtre...")
    window.show()
    
    # Forcer le traitement des événements pour s'assurer que l'interface est affichée
    app.processEvents()
    
    print("Interface active! Fermez la fenêtre pour quitter.")
    
    # Lancer la boucle d'événements Qt
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 