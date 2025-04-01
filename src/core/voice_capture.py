import sounddevice as sd
import soundfile as sf
import numpy as np
import torch
from pathlib import Path
import queue
import threading
from datetime import datetime
from TTS.tts.utils.speakers import SpeakerManager
from TTS.utils.synthesizer import Synthesizer
import rtmidi
import json
import os

class VoiceCapture:
    def __init__(self):
        self.recording = False
        self.monitoring = False
        self.audio_queue = queue.Queue()
        self.monitor_queue = queue.Queue()
        self.sample_rate = 44100  # SSL 2+ supporte 44.1kHz
        self.channels = 1  # Mono pour la capture vocale
        self.device_info = None
        try:
            self.midi_in = rtmidi.MidiIn()
            print("✅ Interface MIDI initialisée avec succès")
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation MIDI: {e}")
            self.midi_in = None
        self.midi_notes = []
        self.midi_activity = False
        self.midi_ports = []
        self.current_midi_port = None
        self.setup_audio_device()
        self.setup_midi()
        
    def setup_audio_device(self):
        """Configure le périphérique audio SSL 2+."""
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if "SSL 2+" in device["name"]:
                self.device_info = device
                print(f"SSL 2+ trouvé : {device['name']}")
                sd.default.device = i
                break
        if not self.device_info:
            print("SSL 2+ non trouvé, utilisation du périphérique par défaut")
            
    def setup_midi(self):
        """Configure l'entrée MIDI."""
        if not self.midi_in:
            return
            
        try:
            self.midi_ports = self.midi_in.get_ports()
            if self.midi_ports:
                print(f"✅ Ports MIDI détectés: {len(self.midi_ports)}")
                self.select_midi_port(0)
            else:
                print("ℹ️ Aucun port MIDI détecté")
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation des ports MIDI: {e}")
            
    def get_midi_ports(self):
        """Retourne la liste des ports MIDI disponibles."""
        if not self.midi_in:
            return []
        try:
            # Rafraîchir la liste des ports
            self.midi_ports = self.midi_in.get_ports()
            return self.midi_ports
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des ports MIDI: {e}")
            return []
        
    def select_midi_port(self, port_index):
        """Sélectionne un port MIDI."""
        if not self.midi_in:
            return False
            
        try:
            if self.current_midi_port is not None:
                try:
                    self.midi_in.close_port()
                    print(f"✅ Port MIDI précédent fermé")
                except Exception as e:
                    print(f"⚠️ Erreur lors de la fermeture du port précédent: {e}")
            
            if port_index < 0 or port_index >= len(self.midi_ports):
                print(f"❌ Index de port MIDI invalide: {port_index}")
                return False
                
            port_name = self.midi_ports[port_index]
            print(f"🎹 Ouverture du port MIDI: {port_name}")
            self.midi_in.open_port(port_index)
            self.midi_in.set_callback(self._midi_callback)
            self.current_midi_port = port_index
            print(f"✅ Port MIDI ouvert: {port_name}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la sélection du port MIDI: {e}")
            return False
            
    def _midi_callback(self, message, _):
        """Callback pour les messages MIDI."""
        try:
            if not message or len(message[0]) < 3:
                return
                
            status_byte = message[0][0] & 0xF0  # Type de message (4 bits de poids fort)
            
            if status_byte == 0x90:  # Note On
                note = message[0][1]
                velocity = message[0][2]
                if velocity > 0:
                    print(f"🎵 Note On: {note} (vélocité: {velocity})")
                    self.midi_notes.append(note)
                    self.midi_activity = True
                else:
                    # Une vélocité de 0 est équivalente à Note Off
                    print(f"🎵 Note Off (vélocité 0): {note}")
                    if note in self.midi_notes:
                        self.midi_notes.remove(note)
            elif status_byte == 0x80:  # Note Off
                note = message[0][1]
                print(f"🎵 Note Off: {note}")
                if note in self.midi_notes:
                    self.midi_notes.remove(note)
        except Exception as e:
            print(f"❌ Erreur dans le callback MIDI: {e}")
            
    def start_monitoring(self):
        """Démarre le monitoring audio."""
        if self.monitoring:
            return
            
        self.monitoring = True
        
        def audio_callback(indata, frames, time, status):
            if status:
                print(status)
            self.monitor_queue.put(indata.copy())
            if self.recording:
                self.audio_queue.put(indata.copy())
                
        try:
            self.stream = sd.InputStream(
                callback=audio_callback,
                channels=self.channels,
                samplerate=self.sample_rate
            )
            self.stream.start()
        except Exception as e:
            print(f"Erreur lors du démarrage du monitoring : {e}")
            self.monitoring = False
            
    def stop_monitoring(self):
        """Arrête le monitoring audio."""
        if self.monitoring:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.monitoring = False
            
    def get_audio_level(self):
        """Retourne les dernières données audio pour le monitoring."""
        try:
            return self.monitor_queue.get_nowait()
        except queue.Empty:
            return None
            
    def start_recording(self):
        """Démarre l'enregistrement audio."""
        if not self.monitoring:
            self.start_monitoring()
        
        # Réinitialiser les données audio
        self.audio_data = []
        
        print("✓ Enregistrement démarré")
        self.recording = True
        self.recording_started.emit()
        
    def stop_recording(self):
        """Arrête l'enregistrement audio."""
        if not self.recording:
            return None
        
        self.recording = False
        
        # S'assurer que les données audio existent et ne sont pas vides
        if hasattr(self, 'audio_data') and self.audio_data:
            # Convertir en liste si c'est un tableau NumPy
            if isinstance(self.audio_data, np.ndarray):
                self.audio_data = self.audio_data.tolist()
            
            # Vérifier que nous avons bien des données
            if len(self.audio_data) > 0:
                print(f"✓ Enregistrement terminé : {len(self.audio_data)} échantillons")
                self.recording_stopped.emit()
                self._update_waveform()
                return True
        
        print("⚠ Pas de données audio enregistrées")
        self.recording_stopped.emit()
        return False
        
    def is_recording(self):
        """Retourne l'état de l'enregistrement."""
        return self.recording
        
    def is_midi_active(self):
        """Retourne True si une activité MIDI a été détectée."""
        was_active = self.midi_activity
        self.midi_activity = False  # Réinitialise l'état
        return was_active
        
    def cleanup(self):
        """Nettoie les ressources."""
        self.stop_monitoring()
        if self.midi_in:
            self.midi_in.close_port()
            self.midi_in.delete()
            
    def save_recording(self, output_dir="recordings"):
        """Sauvegarde l'enregistrement."""
        Path(output_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(output_dir) / f"recording_{timestamp}.wav"
        
        recorded_data = []
        while not self.audio_queue.empty():
            recorded_data.append(self.audio_queue.get())
            
        if recorded_data:
            audio_data = np.concatenate(recorded_data)
            sf.write(str(output_file), audio_data, self.sample_rate)
            print(f"Enregistrement sauvegardé : {output_file}")
            return str(output_file)
        return None
        
    def clone_voice(self, audio_file, tts_engine, output_dir="cloned_models"):
        """Clone une voix à partir d'un enregistrement."""
        try:
            print(f"🎙️ Clonage de voix à partir de: {audio_file}")
            
            # Vérifier que le fichier audio existe
            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Le fichier audio {audio_file} n'existe pas")
            
            # Vérifier le contenu du fichier audio
            try:
                audio_data, sample_rate = sf.read(audio_file)
                
                # Vérifier que les données audio ne sont pas vides
                if audio_data is None or (isinstance(audio_data, np.ndarray) and audio_data.size == 0):
                    raise ValueError("Le fichier audio ne contient pas de données")
                
                # Pour éviter l'erreur "truth value of array is ambiguous"
                if isinstance(audio_data, np.ndarray):
                    duration = len(audio_data) / sample_rate
                    print(f"✓ Audio valide: {duration:.2f} secondes à {sample_rate} Hz")
                    
                    # Si c'est un tableau stéréo, convertir en mono si nécessaire
                    if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                        print("🔄 Conversion de l'audio stéréo en mono...")
                        audio_data = np.mean(audio_data, axis=1)
            except Exception as e:
                raise ValueError(f"Erreur lors de la lecture du fichier audio: {str(e)}")
            
            # Création du répertoire pour les modèles clonés
            model_dir = Path(output_dir)
            model_dir.mkdir(exist_ok=True)
            
            # Extraction des caractéristiques de la voix (simulation)
            print("🔄 Extraction des caractéristiques vocales...")
            
            # Simuler une extraction d'embedding
            embedding = np.random.rand(1, 256)  # Simuler un embedding de dimension 256
            
            # Sauvegarde du modèle cloné
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = model_dir / f"cloned_voice_{timestamp}"
            os.makedirs(model_path, exist_ok=True)
            
            # Sauvegarder l'embedding (simulation)
            np.save(os.path.join(model_path, "speaker_embedding.npy"), embedding)
            
            # Création d'un fichier de configuration
            config = {
                "original_audio": audio_file,
                "date_created": timestamp,
                "sample_rate": sample_rate,
                "duration": float(duration),
                "channels": 1 if len(audio_data.shape) == 1 else audio_data.shape[1]
            }
            
            with open(os.path.join(model_path, "config.json"), "w") as f:
                json.dump(config, f, indent=4)
            
            print(f"✅ Modèle cloné sauvegardé dans: {model_path}")
            return str(model_path)
        
        except Exception as e:
            print(f"❌ Erreur lors du clonage de la voix: {e}")
            return None
            
    def apply_midi_to_speech(self, text, tts_engine, midi_notes):
        """Applique les notes MIDI à la synthèse vocale."""
        try:
            # Conversion des notes MIDI en fréquences
            frequencies = [440 * (2 ** ((n - 69) / 12)) for n in midi_notes]
            
            # Synthèse avec modulation de la hauteur
            audio = tts_engine.tts(text, pitch_modulation=frequencies)
            
            return audio
        except Exception as e:
            print(f"Erreur lors de l'application MIDI : {e}")
            return None 