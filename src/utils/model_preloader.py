import os
import torch
from TTS.api import TTS
from tqdm import tqdm
import threading
import queue

class ModelPreloader:
    _instance = None
    _models_loaded = False
    _progress_queue = queue.Queue()
    
    MODELS_TO_LOAD = {
        'principal': "tts_models/fr/css10/vits",  # Modèle principal léger
        'secondaires': [
            "tts_models/multilingual/multi-dataset/xtts_v2",
            "tts_models/en/ljspeech/tacotron2-DDC"
        ]
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelPreloader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._models_loaded:
            self.tts = None
            self._load_progress = 0
            self._models_loaded = True

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ModelPreloader()
        return cls._instance

    def get_tts(self):
        """Retourne l'instance TTS principale"""
        return self.tts

    def preload_models(self):
        """Précharge le modèle principal rapidement et les autres en arrière-plan"""
        print("\nInitialisation de Vocal Clone...")
        
        # Nettoyer la mémoire GPU si disponible
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("✓ GPU détecté - CUDA activé")
        
        try:
            # Charger d'abord le modèle principal rapidement
            print("Chargement du modèle principal...")
            self.tts = TTS(model_name=self.MODELS_TO_LOAD['principal'])
            print(f"✓ Modèle principal chargé : {self.MODELS_TO_LOAD['principal']}")
            
            # Lancer le chargement des modèles secondaires en arrière-plan
            thread = threading.Thread(target=self._background_load)
            thread.daemon = True  # Le thread s'arrêtera avec le programme principal
            thread.start()
            
            return self.tts
            
        except Exception as e:
            print(f"⚠ Erreur lors du préchargement : {str(e)}")
            raise

    def _background_load(self):
        """Charge les modèles secondaires en arrière-plan"""
        try:
            for model in self.MODELS_TO_LOAD['secondaires']:
                print(f"Chargement en arrière-plan : {model}")
                TTS(model_name=model)
                print(f"✓ Modèle chargé : {model}")
                
        except Exception as e:
            print(f"⚠ Erreur de chargement en arrière-plan : {str(e)}")

    def get_load_progress(self):
        """Retourne la progression du chargement"""
        try:
            return self._progress_queue.get_nowait()
        except queue.Empty:
            return None 