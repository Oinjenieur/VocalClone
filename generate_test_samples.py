import os
import numpy as np
import soundfile as sf
from pathlib import Path
import logging
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestSampleGenerator:
    def __init__(self, output_dir: str = "test_audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Configuration des échantillons de test
        self.test_configs = {
            "reference": {
                "duration": 20,  # secondes
                "sample_rate": 22050,
                "frequency": 440,  # La4
                "amplitude": 0.5
            },
            "short": {
                "duration": 5,
                "sample_rate": 22050,
                "frequency": 440,
                "amplitude": 0.5
            },
            "long": {
                "duration": 30,
                "sample_rate": 22050,
                "frequency": 440,
                "amplitude": 0.5
            }
        }

    def generate_sine_wave(self, duration: float, sample_rate: int, frequency: float, amplitude: float) -> np.ndarray:
        """Génère une onde sinusoïdale"""
        t = np.linspace(0, duration, int(sample_rate * duration))
        return amplitude * np.sin(2 * np.pi * frequency * t)

    def add_noise(self, signal: np.ndarray, noise_level: float = 0.01) -> np.ndarray:
        """Ajoute du bruit gaussien au signal"""
        noise = np.random.normal(0, noise_level, len(signal))
        return signal + noise

    def generate_sample(self, name: str, config: Dict):
        """Génère un échantillon audio"""
        # Génération du signal de base
        signal = self.generate_sine_wave(
            config["duration"],
            config["sample_rate"],
            config["frequency"],
            config["amplitude"]
        )
        
        # Ajout de bruit
        signal = self.add_noise(signal)
        
        # Sauvegarde du fichier
        output_path = self.output_dir / f"{name}.wav"
        sf.write(output_path, signal, config["sample_rate"])
        logger.info(f"Échantillon généré: {output_path}")

    def generate_all_samples(self):
        """Génère tous les échantillons de test"""
        for name, config in self.test_configs.items():
            try:
                self.generate_sample(name, config)
            except Exception as e:
                logger.error(f"Erreur lors de la génération de l'échantillon {name}: {e}")

def main():
    generator = TestSampleGenerator()
    generator.generate_all_samples()

if __name__ == "__main__":
    main() 