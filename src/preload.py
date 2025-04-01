import sys
import os
from utils.model_preloader import ModelPreloader

def preload():
    print("Préchargement des modèles TTS...")
    preloader = ModelPreloader.get_instance()
    preloader.preload_models()
    print("Préchargement terminé !")

if __name__ == "__main__":
    preload() 