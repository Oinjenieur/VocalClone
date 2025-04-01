import os
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        self.config_dir = Path.home() / '.voice_cloning'
        self.config_file = self.config_dir / 'config.json'
        self.config_dir.mkdir(exist_ok=True)
        self.tokens = {}
        self.load_config()
        
    def load_config(self):
        """Charge la configuration depuis le fichier"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    self.tokens = json.load(f)
                logger.info("Configuration chargée avec succès")
            else:
                logger.info("Aucune configuration existante trouvée")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
            
    def save_config(self):
        """Sauvegarde la configuration dans le fichier"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.tokens, f, indent=4)
            logger.info("Configuration sauvegardée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration: {e}")
            
    def set_token(self, service: str, token: str):
        """Définit un token pour un service"""
        self.tokens[service] = token
        self.save_config()
        
    def get_token(self, service: str) -> str:
        """Récupère un token pour un service"""
        return self.tokens.get(service)
        
    def remove_token(self, service: str):
        """Supprime un token pour un service"""
        if service in self.tokens:
            del self.tokens[service]
            self.save_config()

# Instance globale de configuration
config = Config() 