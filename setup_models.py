import os
import subprocess
import sys
from pathlib import Path
import logging
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelInstaller:
    def __init__(self):
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)
        
        self.model_configs = {
            "openvoice_v2": {
                "repo": "https://github.com/myshell-ai/OpenVoice.git",
                "checkpoint_url": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip",
                "requirements": ["torch", "numpy", "soundfile", "librosa"]
            },
            "valle_x": {
                "repo": "https://github.com/microsoft/vall-e-x.git",
                "checkpoint_url": "https://huggingface.co/microsoft/vall-e-x/resolve/main/vall-e-x.pt",
                "requirements": ["torch", "transformers", "accelerate"]
            },
            "styletts2": {
                "repo": "https://github.com/yl4579/StyleTTS2.git",
                "checkpoint_url": "https://huggingface.co/yl4579/StyleTTS2/resolve/main/styletts2.pt",
                "requirements": ["torch", "numpy", "librosa"]
            },
            "bark": {
                "repo": "https://github.com/suno-ai/bark.git",
                "checkpoint_url": "https://huggingface.co/suno-ai/bark/resolve/main/bark.pt",
                "requirements": ["torch", "transformers", "accelerate"]
            },
            "coqui_tts": {
                "repo": "https://github.com/coqui-ai/TTS.git",
                "checkpoint_url": "https://huggingface.co/coqui-ai/TTS/resolve/main/tts_model.pt",
                "requirements": ["torch", "numpy", "soundfile"]
            },
            "spark_tts": {
                "repo": "https://github.com/Spark-TTS/Spark-TTS.git",
                "checkpoint_url": "https://huggingface.co/Spark-TTS/Spark-TTS/resolve/main/spark_tts.pt",
                "requirements": ["torch", "numpy", "soundfile"]
            },
            "suno_v4": {
                "repo": "https://github.com/suno-ai/bark.git",
                "checkpoint_url": "https://huggingface.co/suno/bark-v4/resolve/main/model.pt",
                "requirements": ["torch", "transformers", "accelerate"]
            }
        }

    def install_dependencies(self, requirements: List[str]):
        """Installe les dépendances requises"""
        for req in requirements:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", req])
                logger.info(f"Dépendance installée: {req}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Erreur lors de l'installation de {req}: {e}")
                raise

    def clone_repository(self, repo_url: str, model_name: str):
        """Clone le dépôt du modèle"""
        model_dir = self.models_dir / model_name
        if not model_dir.exists():
            try:
                subprocess.check_call(["git", "clone", repo_url, str(model_dir)])
                logger.info(f"Dépôt cloné: {model_name}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Erreur lors du clonage de {model_name}: {e}")
                raise

    def download_checkpoint(self, url: str, model_name: str):
        """Télécharge le checkpoint du modèle"""
        checkpoint_dir = self.models_dir / model_name / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)
        
        checkpoint_path = checkpoint_dir / f"{model_name}.pt"
        if not checkpoint_path.exists():
            try:
                subprocess.check_call(["wget", "-O", str(checkpoint_path), url])
                logger.info(f"Checkpoint téléchargé: {model_name}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Erreur lors du téléchargement du checkpoint de {model_name}: {e}")
                raise

    def setup_model(self, model_name: str, config: Dict):
        """Configure un modèle spécifique"""
        logger.info(f"Configuration de {model_name}...")
        
        # Installation des dépendances
        self.install_dependencies(config["requirements"])
        
        # Clonage du dépôt
        self.clone_repository(config["repo"], model_name)
        
        # Téléchargement du checkpoint
        self.download_checkpoint(config["checkpoint_url"], model_name)
        
        logger.info(f"Configuration terminée pour {model_name}")

    def setup_all_models(self):
        """Configure tous les modèles"""
        for model_name, config in self.model_configs.items():
            try:
                self.setup_model(model_name, config)
            except Exception as e:
                logger.error(f"Erreur lors de la configuration de {model_name}: {e}")
                continue

def main():
    installer = ModelInstaller()
    installer.setup_all_models()

if __name__ == "__main__":
    main() 