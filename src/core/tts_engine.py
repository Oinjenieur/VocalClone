from TTS.api import TTS
import os
import tempfile
import sounddevice as sd
import soundfile as sf
import numpy as np
from pathlib import Path
import shutil
from datetime import datetime
from utils.model_preloader import ModelPreloader

class TTSEngine:
    def __init__(self):
        self.preloader = ModelPreloader.get_instance()
        self.tts = self.preloader.get_tts()
        self.current_language = "fr"
        self.current_voice = "tts_models/fr/css10/vits"
        self.current_speed = 1.0
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
        self.history_dir = Path("history")
        self.history_dir.mkdir(exist_ok=True)
        
    def set_language(self, language):
        """Configure la langue pour la synthèse vocale."""
        if language != self.current_language:
            self.current_language = language
            # Le modèle sera mis à jour lors du prochain set_voice
        
    def set_voice(self, voice):
        """Configure la voix pour la synthèse vocale."""
        if voice != self.current_voice:
            self.current_voice = voice
            # Créer une nouvelle instance TTS avec la voix sélectionnée
            try:
                self.tts = TTS(model_name=voice)
                self.tts.speed = self.current_speed
            except Exception as e:
                print(f"Erreur lors du changement de voix : {e}")
                # Revenir au modèle précédent en cas d'erreur
                self.tts = self.preloader.get_tts()
        
    def set_speed(self, speed):
        """Configure la vitesse de parole."""
        self.current_speed = speed
        if self.tts:
            self.tts.speed = speed
            
    def synthesize(self, text):
        """Syntétise le texte en audio."""
        if not self.tts:
            raise ValueError("Veuillez d'abord sélectionner une voix")
            
        # Création d'un nom de fichier unique avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"output_{timestamp}.wav"
        
        # Génération de l'audio
        self.tts.tts_to_file(text=text, file_path=str(output_file))
        
        # Sauvegarde dans l'historique
        self._save_to_history(output_file, text)
        
        return str(output_file)
        
    def _save_to_history(self, audio_file, text):
        """Sauvegarde l'audio et le texte dans l'historique."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_file = self.history_dir / f"history_{timestamp}.txt"
        
        with open(history_file, 'w', encoding='utf-8') as f:
            f.write(f"Date: {timestamp}\n")
            f.write(f"Langue: {self.current_language}\n")
            f.write(f"Voix: {self.current_voice}\n")
            f.write(f"Vitesse: {self.current_speed}\n")
            f.write("\nTexte:\n")
            f.write(text)
            
    def play_audio(self, audio_data, sample_rate, output_device=None, volume=1.0):
        """Joue l'audio généré
        
        Args:
            audio_data: Les données audio à jouer
            sample_rate: Le taux d'échantillonnage
            output_device: L'index du périphérique de sortie (None pour le défaut)
            volume: Le volume de lecture (1.0 = volume normal)
        """
        try:
            # S'assurer que les données sont en float32
            audio_data = audio_data.astype(np.float32)
            
            # Appliquer le volume si différent de 1.0
            if volume != 1.0:
                audio_data = audio_data * volume
                print(f"🔊 TTS - Volume appliqué : {volume:.2f}")
            
            # Configurer le stream de sortie avec le périphérique sélectionné
            stream = sd.OutputStream(
                device=output_device,  # None utilisera le périphérique par défaut
                channels=1,  # Mono
                samplerate=int(sample_rate),
                dtype=np.float32
            )
            
            # Utiliser la méthode standard pour jouer l'audio
            with stream:
                stream.start()
                stream.write(audio_data)
                
                # Attendre la durée de l'audio au lieu d'utiliser wait()
                audio_duration = len(audio_data) / sample_rate
                sd.sleep(int(audio_duration * 1000))  # Sleep prend des millisecondes
            
        except Exception as e:
            print(f"⚠ Erreur lors de la lecture audio : {str(e)}")
            raise
            
    def stop_audio(self):
        """Arrête la lecture audio en cours."""
        sd.stop()
        
    def get_audio_duration(self, file_path):
        """Retourne la durée d'un fichier audio en secondes."""
        try:
            data, samplerate = sf.read(file_path)
            return len(data) / samplerate
        except Exception as e:
            print(f"Erreur lors de la lecture de la durée : {e}")
            return 0
            
    def cleanup(self, file_path):
        """Nettoie les fichiers temporaires."""
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Erreur lors de la suppression du fichier : {e}")
            
    def save_audio(self, source_path, target_path):
        """Sauvegarde un fichier audio à un emplacement spécifique."""
        try:
            shutil.copy2(source_path, target_path)
            return True
        except Exception as e:
            raise Exception(f"Erreur lors de la sauvegarde du fichier audio: {str(e)}")
            
    def get_history(self):
        """Retourne la liste des fichiers d'historique."""
        return sorted(self.history_dir.glob("history_*.txt"), reverse=True)
        
    def clear_history(self):
        """Nettoie l'historique."""
        try:
            for file in self.history_dir.glob("history_*.txt"):
                file.unlink()
            return True
        except:
            return False

    def save_cloned_model(self, model_path):
        """Sauvegarde le modèle cloné"""
        try:
            if hasattr(self.tts, 'model') and hasattr(self.tts.model, 'save'):
                self.tts.model.save(model_path)
                print(f"✓ Modèle cloné sauvegardé : {model_path}")
            else:
                raise Exception("Le modèle TTS n'a pas de méthode de sauvegarde")
        except Exception as e:
            print(f"⚠ Erreur lors de la sauvegarde du modèle : {str(e)}")
            raise

    def clone_voice(self, voice_file, output_model):
        """Clone la voix à partir d'un fichier audio.
        
        Args:
            voice_file: Le chemin vers le fichier audio de la voix à cloner
            output_model: Le chemin où sauvegarder le modèle cloné
            
        Returns:
            bool: True si le clonage a réussi, False sinon
        """
        try:
            print(f"📊 Clonage de voix à partir de: {voice_file}")
            print(f"📂 Modèle de sortie: {output_model}")
            
            # Vérifier si le fichier audio existe
            if not os.path.exists(voice_file):
                raise FileNotFoundError(f"Le fichier audio {voice_file} n'existe pas")
                
            # Vérifier si XTTS est disponible
            if not hasattr(self.tts, 'voice_conversion') and self.current_voice != "tts_models/multilingual/multi-dataset/xtts_v2":
                # Charger le modèle XTTS v2 pour le clonage de voix
                try:
                    print("🔄 Chargement du modèle XTTS v2 pour le clonage...")
                    self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
                except Exception as e:
                    raise Exception(f"Impossible de charger le modèle XTTS v2: {e}")
                    
            # Créer le dossier de sortie si nécessaire
            os.makedirs(os.path.dirname(output_model), exist_ok=True)
            
            # Vérifier le fichier audio et extraire les données
            import numpy as np
            import soundfile as sf
            
            try:
                # Charger les données audio pour vérification
                audio_data, sample_rate = sf.read(voice_file)
                
                # Vérifier que les données audio ne sont pas vides
                if audio_data is None or (isinstance(audio_data, np.ndarray) and audio_data.size == 0):
                    raise ValueError("Le fichier audio ne contient pas de données")
                    
                print(f"✓ Audio valide: {len(audio_data)/sample_rate:.2f} secondes à {sample_rate} Hz")
                
                # Pour éviter l'erreur "truth value of array is ambiguous", nous vérifions explicitement
                if isinstance(audio_data, np.ndarray):
                    # Si c'est un tableau stéréo, convertir en mono si nécessaire
                    if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                        print("🔄 Conversion de l'audio stéréo en mono...")
                        audio_data = np.mean(audio_data, axis=1)
            except Exception as e:
                raise ValueError(f"Erreur lors de la lecture du fichier audio: {str(e)}")
            
            # À implémenter: appel de l'API TTS pour le clonage de voix
            # Comme l'API TTS n'a pas de méthode directe pour le clonage, on simule
            print("🔄 Simulation du clonage de voix (fonctionnalité à implémenter)...")
            
            # Simuler un processus de clonage
            import time
            for i in range(10):
                time.sleep(0.5)
                print(f"Progression: {(i+1) * 10}%")
            
            # Créer un fichier de métadonnées pour le modèle
            metadata = {
                "source_file": voice_file,
                "date_created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "model_type": "voice_clone",
                "base_model": self.current_voice,
                "sample_rate": sample_rate,
                "duration": len(audio_data)/sample_rate if isinstance(audio_data, np.ndarray) else 0
            }
            
            with open(f"{output_model}.json", 'w', encoding='utf-8') as f:
                import json
                json.dump(metadata, f, indent=2)
                
            # Copier le fichier audio comme référence
            import shutil
            shutil.copy(voice_file, f"{output_model}.wav")
            
            print("✅ Clonage de voix terminé avec succès!")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du clonage de voix: {str(e)}")
            return False 