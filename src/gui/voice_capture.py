import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtCore import QObject, Signal
import os

class VoiceCapture(QObject):
    """Classe pour gérer la capture audio"""
    
    # Définition des signaux
    recording_started = Signal()
    recording_stopped = Signal()
    playback_started = Signal()
    playback_stopped = Signal()
    level_updated = Signal(float)
    devices_updated = Signal(list, list)
    error_occurred = Signal(str)
    waveform_updated = Signal(object)  # Signal pour mettre à jour la forme d'onde
    playback_position_updated = Signal(float)  # Signal pour la position de lecture (0.0-1.0)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_recording = False
        self.is_playing = False
        self.audio_data = []
        self.stream = None
        self.current_level = 0
        
        # Paramètres audio standard pour SSL 2+
        self.sample_rate = 48000  # SSL 2+ supporte 44.1kHz, 48kHz, 96kHz
        self.channels = 1  # Mono
        self.dtype = 'float32'
        
        # Contrôles de volume et vitesse
        self.input_volume = 1.0
        self.output_volume = 1.0
        self.playback_speed = 1.0  # Vitesse normale par défaut (corrigé de 0.5)
        
        self.playback_position = 0
        self.playback_stream = None
        self.temp_file = "temp_recording.wav"
        self.input_device = None
        self.output_device = None
        
        try:
            self._check_audio_devices()
        except Exception as e:
            print(f"⚠ Erreur d'initialisation : {e}")
            self.error_occurred.emit(str(e))
            
    def set_input_volume(self, volume):
        """Définit le volume d'entrée (0.0 à 2.0) - Affecte l'acquisition audio"""
        try:
            self.input_volume = volume
            
            # Essayer d'appliquer le volume au système si possible
            if hasattr(sd, 'set_input_gain'):
                sd.set_input_gain(volume)
                
            print(f"🔊 Volume d'entrée réglé à {volume:.2f}")
            
            # Mise à jour immédiate si on est en enregistrement
            if self.is_recording and self.stream:
                try:
                    if hasattr(self.stream, 'gain'):
                        self.stream.gain = volume
                except Exception as e:
                    print(f"⚠️ Impossible d'appliquer le gain au stream d'enregistrement : {e}")
                    
        except Exception as e:
            print(f"⚠️ Erreur lors du réglage du volume d'entrée : {e}")
        
    def set_output_volume(self, volume):
        """Définit le volume de sortie (0.0 à 2.0) - Affecte le playback global"""
        try:
            self.output_volume = volume
            
            # Essayer d'appliquer le volume au système si possible
            if hasattr(sd, 'set_output_gain'):
                sd.set_output_gain(volume)
                
            print(f"🔊 Volume de sortie réglé à {volume:.2f}")
                
            # Si on est en lecture, appliquer immédiatement
            if self.is_playing and hasattr(sd, 'set_stream_volume'):
                try:
                    sd.set_stream_volume(volume)
                except Exception as e:
                    print(f"⚠️ Impossible d'appliquer le volume au stream de lecture : {e}")
                    
        except Exception as e:
            print(f"⚠️ Erreur lors du réglage du volume de sortie : {e}")
    
    def get_audio_devices(self):
        """Retourne les listes des périphériques d'entrée et de sortie"""
        try:
            print("\n🎧 Périphériques audio disponibles :")
            devices = sd.query_devices()
            input_devices = []
            output_devices = []
            
            # Trouver le périphérique par défaut
            default_input = sd.query_devices(kind='input')
            default_output = sd.query_devices(kind='output')
            
            for idx, device in enumerate(devices):
                # Périphériques d'entrée
                if device['max_input_channels'] > 0:
                    is_default = (device['name'] == default_input['name'])
                    is_ssl = 'SSL 2+' in device['name']
                    device_name = f"{device['name']} {'(Défaut)' if is_default else ''} {'(SSL 2+)' if is_ssl else ''}"
                    input_devices.append({
                        'index': idx,
                        'name': device_name,
                        'channels': device['max_input_channels'],
                        'is_ssl': is_ssl,
                        'is_default': is_default,
                        'sample_rate': device.get('default_samplerate', 44100)
                    })
                    print(f"🎤 [{idx}] {device_name}")
                    
                # Périphériques de sortie
                if device['max_output_channels'] > 0:
                    is_default = (device['name'] == default_output['name'])
                    is_ssl = 'SSL 2+' in device['name']
                    device_name = f"{device['name']} {'(Défaut)' if is_default else ''} {'(SSL 2+)' if is_ssl else ''}"
                    output_devices.append({
                        'index': idx,
                        'name': device_name,
                        'channels': device['max_output_channels'],
                        'is_ssl': is_ssl,
                        'is_default': is_default,
                        'sample_rate': device.get('default_samplerate', 44100)
                    })
                    print(f"🔊 [{idx}] {device_name}")
            
            # Trier les périphériques, SSL 2+ first, puis par défaut
            input_devices.sort(key=lambda x: (-x['is_ssl'], -x['is_default']))
            output_devices.sort(key=lambda x: (-x['is_ssl'], -x['is_default']))
                    
            return input_devices, output_devices
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des périphériques : {e}")
            return [], []
            
    def set_input_device(self, device_index):
        """Définit le périphérique d'entrée"""
        try:
            if self.is_recording:
                self.stop_recording()
                
            # Vérifier si le périphérique est valide
            device_info = sd.query_devices(device_index)
            if device_info['max_input_channels'] == 0:
                raise ValueError(f"Le périphérique {device_info['name']} ne supporte pas l'entrée audio")
                
            self.input_device = device_index
            print(f"✓ Périphérique d'entrée changé : [{device_index}] {device_info['name']}")
            
            # Mettre à jour le sample rate et les canaux
            if 'default_samplerate' in device_info:
                self.sample_rate = int(device_info['default_samplerate'])
                print(f"✓ Sample rate ajusté à {self.sample_rate} Hz")
                
            # Tester le périphérique
            sd.check_input_settings(
                device=self.input_device,
                channels=1,
                dtype=np.float32,
                samplerate=self.sample_rate
            )
            
        except Exception as e:
            print(f"Erreur lors du changement du périphérique d'entrée : {e}")
            raise
            
    def set_output_device(self, device_index):
        """Définit le périphérique de sortie"""
        try:
            if self.is_playing:
                self.stop_playback()
                
            # Vérifier si le périphérique est valide
            device_info = sd.query_devices(device_index)
            if device_info['max_output_channels'] == 0:
                raise ValueError(f"Le périphérique {device_info['name']} ne supporte pas la sortie audio")
                
            self.output_device = device_index
            print(f"✓ Périphérique de sortie changé : [{device_index}] {device_info['name']}")
            
        except Exception as e:
            print(f"Erreur lors du changement du périphérique de sortie : {e}")
            raise
            
    def _check_audio_devices(self):
        """Vérifie les périphériques audio disponibles"""
        try:
            print("\n🔍 Recherche des périphériques audio...")
            input_devices, output_devices = self.get_audio_devices()
            
            if not input_devices:
                raise RuntimeError("Aucun périphérique d'entrée trouvé")
            if not output_devices:
                raise RuntimeError("Aucun périphérique de sortie trouvé")
                
            # Trouver les périphériques par défaut
            default_input = None
            default_output = None
            
            # Chercher d'abord SSL 2+
            for device in input_devices:
                if device['is_ssl']:
                    default_input = device['index']
                    # Vérifier les formats supportés
                    device_info = sd.query_devices(default_input)
                    print(f"\n📊 Formats supportés pour SSL 2+ :")
                    print(f"Sample rates : {device_info['default_samplerate']} Hz")
                    print(f"Channels : {device_info['max_input_channels']}")
                    # Ajuster le sample rate si nécessaire
                    if device_info['default_samplerate'] != self.sample_rate:
                        print(f"⚠ Ajustement du sample rate à {device_info['default_samplerate']} Hz")
                        self.sample_rate = device_info['default_samplerate']
                    break
                    
            for device in output_devices:
                if device['is_ssl']:
                    default_output = device['index']
                    break
                    
            # Si pas de SSL 2+, chercher les périphériques par défaut
            if default_input is None:
                for device in input_devices:
                    if '(Défaut)' in device['name']:
                        default_input = device['index']
                        break
                        
            if default_output is None:
                for device in output_devices:
                    if '(Défaut)' in device['name']:
                        default_output = device['index']
                        break
                        
            # Si toujours pas trouvé, utiliser le premier
            self.input_device = default_input if default_input is not None else input_devices[0]['index']
            self.output_device = default_output if default_output is not None else output_devices[0]['index']
            
            print(f"\n✓ Périphérique d'entrée sélectionné : [{self.input_device}]")
            print(f"✓ Périphérique de sortie sélectionné : [{self.output_device}]")
            
            # Émettre les listes de périphériques
            self.devices_updated.emit(input_devices, output_devices)
            print("\n✅ Configuration audio validée")
            
        except Exception as e:
            print(f"\n⚠ Erreur de configuration audio : {e}")
            raise
            
    def start_recording(self, max_duration=60):
        """Démarre l'enregistrement avec une durée maximale en secondes"""
        try:
            if self.is_recording:
                print("⚠ Déjà en cours d'enregistrement")
                return False
                
            if self.is_playing:
                self.stop_playback()
                
            # Réinitialiser les données audio
            self.audio_data = []
            self._update_waveform()  # Mettre à jour la forme d'onde (vide)
            
            # Configuration du stream d'entrée
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._audio_callback,
                device=self.input_device
            )
            
            self.is_recording = True
            self.stream.start()
            self.recording_started.emit()
            print("✓ Enregistrement démarré")
            return True
            
        except Exception as e:
            error_msg = f"Erreur lors du démarrage de l'enregistrement : {e}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
            return False
            
    def _audio_callback(self, indata, frames, time, status):
        """Fonction de rappel pour l'enregistrement audio"""
        if status:
            print(f"⚠ Statut : {status}")
            
        # Appliquer le volume d'entrée si différent de 1.0
        if self.input_volume != 1.0:
            adjusted_data = indata.copy() * self.input_volume
        else:
            adjusted_data = indata
            
        # Calculer le niveau RMS pour le VU-mètre
        rms = np.sqrt(np.mean(adjusted_data**2))
        self.current_level = rms
        self.level_updated.emit(float(rms))
        
        # Ajouter les données audio à notre tableau
        self.audio_data.extend(adjusted_data.flatten())
        
        # Mettre à jour la forme d'onde périodiquement (tous les 5 blocs)
        if len(self.audio_data) % (frames * 5) < frames:
            self._update_waveform()
        
    def stop_recording(self):
        """Arrête l'enregistrement"""
        try:
            if not self.is_recording:
                print("✓ Pas d'enregistrement en cours")
                return
                
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                
            self.is_recording = False
            
            # Normaliser l'audio si nécessaire
            if len(self.audio_data) > 0:
                self.audio_data = np.array(self.audio_data)
                
                # Normaliser l'audio entre -1 et 1 pour un volume optimal
                max_val = np.max(np.abs(self.audio_data))
                if max_val > 0:
                    self.audio_data = self.audio_data / max_val
                    
                print(f"✓ Enregistrement terminé : {len(self.audio_data)} échantillons")
                
                # Mettre à jour la forme d'onde avec l'audio complet normalisé
                self._update_waveform()
            else:
                print("⚠ Aucune donnée audio enregistrée")
                
            self.recording_stopped.emit()
                
        except Exception as e:
            error_msg = f"Erreur lors de l'arrêt de l'enregistrement : {e}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
        
    def get_current_level(self):
        """Retourne le niveau audio actuel"""
        return float(self.current_level) if hasattr(self, 'current_level') else 0.0
        
    def set_playback_speed(self, speed):
        """Définit la vitesse de lecture (0.5 à 2.0) - Affecte uniquement le playback"""
        try:
            # Limiter la vitesse entre 0.5 et 2.0
            self.playback_speed = max(0.5, min(2.0, speed))
            print(f"🔊 Vitesse de lecture réglée à {self.playback_speed:.2f}x")
                
            # Si on est en lecture, il faut redémarrer avec la nouvelle vitesse
            if self.is_playing:
                self.stop_playback()
                self.play_recording()
                    
        except Exception as e:
            print(f"⚠️ Erreur lors du réglage de la vitesse de lecture : {e}")
            
    def play_recording(self):
        """Joue l'enregistrement audio"""
        try:
            # Vérifier que nous avons des données audio valides
            if not hasattr(self, 'audio_data') or not isinstance(self.audio_data, list) or len(self.audio_data) == 0:
                print("⚠ Aucun enregistrement disponible à lire")
                self.error_occurred.emit("Aucun enregistrement à lire")
                return False
            
            # Si déjà en lecture, arrêter
            if self.is_playing:
                self.stop_playback()
            
            # Convertir les données en tableau NumPy si nécessaire
            audio_array = np.array(self.audio_data, dtype=np.float32)
            
            print(f"▶️ Lecture audio: {len(audio_array)} échantillons à {self.sample_rate} Hz")
            print(f"   Volume: {self.output_volume:.2f}, Vitesse: {self.playback_speed:.2f}")
            
            # Appliquer le volume
            if self.output_volume != 1.0:
                audio_array = audio_array * self.output_volume
            
            # Sauvegarder une copie des données pour la lecture
            self.playback_data = audio_array
            self.playback_position = 0
            
            # Créer et démarrer le stream de sortie
            self.output_stream = sd.OutputStream(
                samplerate=int(self.sample_rate * self.playback_speed),
                channels=1,
                callback=self._playback_callback,
                device=self.output_device
            )
            self.output_stream.start()
            
            # Mettre à jour l'état
            self.is_playing = True
            
            # Émettre le signal de début de lecture
            self.playback_started.emit()
            
            return True
        except Exception as e:
            error_msg = f"Erreur lors de la lecture: {e}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            return False
            
    def stop_playback(self):
        """Arrête la lecture de l'enregistrement"""
        try:
            if self.is_playing:
                # Arrêter le stream de sortie
                if hasattr(self, 'output_stream') and self.output_stream:
                    self.output_stream.stop()
                    self.output_stream.close()
                    delattr(self, 'output_stream')
                    
                # Réinitialiser l'état
                self.is_playing = False
                self.playback_position = 0
                
                # Émettre le signal
                self.playback_stopped.emit()
                
            return True
        except Exception as e:
            print(f"Erreur lors de l'arrêt de la lecture: {e}")
            self.error_occurred.emit(str(e))
            return False
            
    def toggle_playback(self):
        """Bascule entre lecture et pause"""
        if self.is_playing:
            self.stop_playback()
        else:
            self.play_recording()
            
    def re_record(self):
        """Réinitialise et démarre un nouvel enregistrement"""
        self.stop_playback()
        self.audio_data = []
        if os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except Exception as e:
                print(f"Erreur lors de la suppression du fichier temporaire : {e}")
        self.start_recording()
        
    def save_recording(self, filename):
        """Sauvegarde l'enregistrement dans un fichier"""
        try:
            # Vérifier que nous avons des données audio valides
            if not hasattr(self, 'audio_data') or not isinstance(self.audio_data, list) or len(self.audio_data) == 0:
                print("⚠ Pas de données audio à sauvegarder")
                self.error_occurred.emit("Aucun enregistrement à sauvegarder")
                return False
            
            # Convertir en array numpy
            audio_array = np.array(self.audio_data, dtype=np.float32)
            
            # S'assurer que le sample rate est un entier
            sample_rate = int(self.sample_rate)
            
            # Normaliser l'audio entre -1 et 1
            max_value = np.max(np.abs(audio_array))
            if max_value > 0:
                audio_array = audio_array / max_value
            
            # Vérifier si le répertoire existe
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            
            # Sauvegarder en format WAV
            sf.write(
                file=filename,
                data=audio_array,
                samplerate=sample_rate,
                subtype='FLOAT'
            )
            print(f"✅ Enregistrement sauvegardé : {filename} ({len(audio_array)} échantillons à {sample_rate} Hz)")
            return True
            
        except Exception as e:
            error_msg = f"❌ Erreur lors de la sauvegarde : {e}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
            return False
            
    def get_audio_data(self):
        """Retourne les données audio enregistrées"""
        return np.array(self.audio_data) if self.audio_data else np.array([])

    def _update_waveform(self):
        """Met à jour la forme d'onde (pour le signal)"""
        self.waveform_updated.emit(np.array(self.audio_data))

    def seek_to_position(self, position):
        """Déplace la lecture à une position spécifique (0.0-1.0)"""
        if not self.audio_data or len(self.audio_data) == 0:
            return False
            
        # Valider la position
        position = max(0.0, min(1.0, position))
        
        # Calculer la position en échantillons
        new_position = int(position * len(self.audio_data))
        
        # Mettre à jour la position
        self.playback_position = new_position
        
        # Émettre la nouvelle position
        self.playback_position_updated.emit(position)
        
        print(f"⏩ Position de lecture changée: {position:.2f}")
        return True 

    def _playback_callback(self, outdata, frames, time, status):
        """Callback pour la lecture audio"""
        if status:
            print(f"⚠️ Statut de lecture: {status}")
        
        if not hasattr(self, 'playback_data') or len(self.playback_data) == 0:
            print("Fin de la lecture (aucune donnée)")
            raise sd.CallbackStop
        
        # Calculer l'index de fin pour cette trame
        end_idx = min(self.playback_position + frames, len(self.playback_data))
        current_frame_count = end_idx - self.playback_position
        
        # Si on atteint la fin, remplir le reste avec des zéros
        if current_frame_count < frames:
            outdata[:current_frame_count, 0] = self.playback_data[self.playback_position:end_idx]
            outdata[current_frame_count:, 0] = 0
            raise sd.CallbackStop
        else:
            outdata[:, 0] = self.playback_data[self.playback_position:end_idx]
        
        # Mettre à jour la position et envoyer le signal
        position_percent = self.playback_position / len(self.playback_data)
        self.playback_position_updated.emit(position_percent)
        
        # Avancer la position
        self.playback_position += frames
        
        # Si on atteint la fin, arrêter
        if self.playback_position >= len(self.playback_data):
            raise sd.CallbackStop 