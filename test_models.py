import os
import time
import torch
import numpy as np
from pathlib import Path
import soundfile as sf
from typing import Dict, List, Tuple
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoiceCloningTester:
    def __init__(self, test_audio_dir: str = "test_audio"):
        self.test_audio_dir = Path(test_audio_dir)
        self.test_audio_dir.mkdir(exist_ok=True)
        self.results = {}
        
    def test_openvoice_v2(self, reference_audio: str, text: str, language: str) -> Tuple[float, float]:
        """Test OpenVoice V2"""
        try:
            start_time = time.time()
            
            # Import des dépendances nécessaires
            from openvoice import OpenVoice
            import torchaudio
            
            # Chargement du modèle
            model = OpenVoice()
            model.load_model()
            
            # Chargement de l'audio de référence
            ref_audio, sr = torchaudio.load(reference_audio)
            if sr != 16000:
                ref_audio = torchaudio.functional.resample(ref_audio, sr, 16000)
            
            # Génération de la voix clonée
            output_audio = model.clone_voice(ref_audio, text, language)
            
            # Calcul de la similarité
            similarity = model.compute_similarity(ref_audio, output_audio)
            
            inference_time = time.time() - start_time
            return similarity, inference_time
            
        except Exception as e:
            logger.error(f"Erreur lors du test OpenVoice V2: {e}")
            return 0.0, 0.0

    def test_valle_x(self, reference_audio: str, text: str, language: str) -> Tuple[float, float]:
        """Test VALL-E X"""
        try:
            start_time = time.time()
            
            # Import des dépendances nécessaires
            from valle_x import ValleX
            import torchaudio
            
            # Chargement du modèle
            model = ValleX()
            model.load_model()
            
            # Chargement de l'audio de référence
            ref_audio, sr = torchaudio.load(reference_audio)
            if sr != 16000:
                ref_audio = torchaudio.functional.resample(ref_audio, sr, 16000)
            
            # Génération de la voix clonée
            output_audio = model.clone_voice(ref_audio, text, language)
            
            # Calcul de la similarité
            similarity = model.compute_similarity(ref_audio, output_audio)
            
            inference_time = time.time() - start_time
            return similarity, inference_time
            
        except Exception as e:
            logger.error(f"Erreur lors du test VALL-E X: {e}")
            return 0.0, 0.0

    def test_styletts2(self, reference_audio: str, text: str, language: str) -> Tuple[float, float]:
        """Test StyleTTS2"""
        try:
            start_time = time.time()
            
            # Import des dépendances nécessaires
            from styletts2 import StyleTTS2
            import torchaudio
            
            # Chargement du modèle
            model = StyleTTS2()
            model.load_model()
            
            # Chargement de l'audio de référence
            ref_audio, sr = torchaudio.load(reference_audio)
            if sr != 22050:
                ref_audio = torchaudio.functional.resample(ref_audio, sr, 22050)
            
            # Génération de la voix clonée
            output_audio = model.clone_voice(ref_audio, text)
            
            # Calcul de la similarité
            similarity = model.compute_similarity(ref_audio, output_audio)
            
            inference_time = time.time() - start_time
            return similarity, inference_time
            
        except Exception as e:
            logger.error(f"Erreur lors du test StyleTTS2: {e}")
            return 0.0, 0.0

    def test_bark(self, reference_audio: str, text: str, language: str) -> Tuple[float, float]:
        """Test Bark"""
        try:
            start_time = time.time()
            
            # Import des dépendances nécessaires
            from bark import Bark
            import torchaudio
            
            # Chargement du modèle
            model = Bark()
            model.load_model()
            
            # Chargement de l'audio de référence
            ref_audio, sr = torchaudio.load(reference_audio)
            if sr != 24000:
                ref_audio = torchaudio.functional.resample(ref_audio, sr, 24000)
            
            # Génération de la voix clonée
            output_audio = model.clone_voice(ref_audio, text)
            
            # Calcul de la similarité
            similarity = model.compute_similarity(ref_audio, output_audio)
            
            inference_time = time.time() - start_time
            return similarity, inference_time
            
        except Exception as e:
            logger.error(f"Erreur lors du test Bark: {e}")
            return 0.0, 0.0

    def test_coqui_tts(self, reference_audio: str, text: str, language: str) -> Tuple[float, float]:
        """Test Coqui TTS"""
        try:
            start_time = time.time()
            
            # Import des dépendances nécessaires
            try:
                from TTS.api import TTS
                import torchaudio
                logger.info("Dépendances TTS chargées avec succès")
            except ImportError as e:
                logger.warning(f"TTS n'est pas installé ou n'est pas accessible: {e}")
                return 0.0, 0.0
            
            # Chargement du modèle
            try:
                model = TTS(model_name="tts_models/multilingual/multi-dataset/your_tts")
                logger.info("Modèle TTS chargé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors du chargement du modèle TTS: {e}")
                return 0.0, 0.0
            
            # Chargement de l'audio de référence
            try:
                ref_audio, sr = torchaudio.load(reference_audio)
                if sr != 22050:
                    ref_audio = torchaudio.functional.resample(ref_audio, sr, 22050)
                logger.info(f"Audio de référence chargé: {reference_audio}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement de l'audio de référence: {e}")
                return 0.0, 0.0
            
            # Génération de la voix clonée
            try:
                output_audio = model.tts_to_file(
                    text=text,
                    speaker_wav=reference_audio,
                    language=language,
                    file_path="temp_output.wav"
                )
                logger.info("Génération de la voix clonée réussie")
            except Exception as e:
                logger.error(f"Erreur lors de la génération de la voix: {e}")
                return 0.0, 0.0
            
            # Chargement de l'audio généré et calcul de la similarité
            try:
                output_audio, _ = torchaudio.load("temp_output.wav")
                similarity = torch.nn.functional.cosine_similarity(
                    ref_audio.mean(dim=1),
                    output_audio.mean(dim=1),
                    dim=0
                ).item()
                logger.info(f"Similarité calculée: {similarity:.4f}")
            except Exception as e:
                logger.error(f"Erreur lors du calcul de la similarité: {e}")
                return 0.0, 0.0
            
            inference_time = time.time() - start_time
            logger.info(f"Test TTS terminé en {inference_time:.2f} secondes")
            return similarity, inference_time
            
        except Exception as e:
            logger.error(f"Erreur inattendue lors du test Coqui TTS: {e}")
            return 0.0, 0.0

    def test_spark_tts(self, reference_audio: str, text: str, language: str) -> Tuple[float, float]:
        """Test Spark-TTS"""
        try:
            start_time = time.time()
            
            # Import des dépendances nécessaires
            from spark_tts import SparkTTS
            import torchaudio
            
            # Chargement du modèle
            model = SparkTTS()
            model.load_model()
            
            # Chargement de l'audio de référence
            ref_audio, sr = torchaudio.load(reference_audio)
            if sr != 16000:
                ref_audio = torchaudio.functional.resample(ref_audio, sr, 16000)
            
            # Génération de la voix clonée
            output_audio = model.clone_voice(ref_audio, text, language)
            
            # Calcul de la similarité
            similarity = model.compute_similarity(ref_audio, output_audio)
            
            inference_time = time.time() - start_time
            return similarity, inference_time
            
        except Exception as e:
            logger.error(f"Erreur lors du test Spark-TTS: {e}")
            return 0.0, 0.0

    def run_comprehensive_test(self, reference_audio: str, test_texts: Dict[str, str]):
        """Exécute des tests complets sur tous les modèles"""
        logger.info("Démarrage des tests complets...")
        
        for model_name, test_func in [
            ("OpenVoice V2", self.test_openvoice_v2),
            ("VALL-E X", self.test_valle_x),
            ("StyleTTS2", self.test_styletts2),
            ("Bark", self.test_bark),
            ("Coqui TTS", self.test_coqui_tts),
            ("Spark-TTS", self.test_spark_tts)
        ]:
            logger.info(f"Test de {model_name}...")
            model_results = {}
            
            for language, text in test_texts.items():
                if model_name in ["StyleTTS2", "Bark"] and language != "en":
                    continue
                    
                similarity, inference_time = test_func(reference_audio, text, language)
                model_results[language] = {
                    "similarity": similarity,
                    "inference_time": inference_time
                }
            
            self.results[model_name] = model_results

    def print_results(self):
        """Affiche les résultats des tests"""
        print("\nRésultats des tests de clonage vocal:")
        print("-" * 80)
        
        for model_name, results in self.results.items():
            print(f"\n{model_name}:")
            for language, metrics in results.items():
                print(f"  {language}:")
                print(f"    Similarité: {metrics['similarity']:.2%}")
                print(f"    Temps d'inférence: {metrics['inference_time']:.2f}s")

def main():
    # Création d'un dossier pour les tests
    test_dir = Path("test_results")
    test_dir.mkdir(exist_ok=True)
    
    # Configuration des tests
    tester = VoiceCloningTester()
    
    # Textes de test pour différentes langues
    test_texts = {
        "en": "Hello, this is a test of voice cloning technology.",
        "fr": "Bonjour, ceci est un test de technologie de clonage vocal.",
        "es": "Hola, esto es una prueba de tecnología de clonación de voz.",
        "zh": "你好，这是语音克隆技术的测试。",
        "ja": "こんにちは、これは音声クローン技術のテストです。",
        "ko": "안녕하세요, 이것은 음성 복제 기술 테스트입니다."
    }
    
    # Chemin vers l'audio de référence
    reference_audio = "test_audio/reference.wav"
    
    # Exécution des tests
    tester.run_comprehensive_test(reference_audio, test_texts)
    
    # Affichage des résultats
    tester.print_results()

if __name__ == "__main__":
    main() 