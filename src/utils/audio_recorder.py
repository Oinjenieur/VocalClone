import sounddevice as sd
import numpy as np
import soundfile as sf
import queue
import threading
import time

class AudioRecorder:
    def __init__(self, sample_rate=22050, channels=1, dtype=np.float32):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.audio_queue = queue.Queue()
        self.level_queue = queue.Queue()
        self.is_recording = False
        self.audio_data = []
        self.start_time = None
        
    def audio_callback(self, indata, frames, time, status):
        """Callback pour recevoir les données audio"""
        if status:
            print(f"Status: {status}")
        self.audio_queue.put(indata.copy())
        
        # Calculer le niveau audio pour le vu-mètre
        level = np.abs(indata).mean()
        try:
            self.level_queue.put_nowait(level)
        except queue.Full:
            pass
        
    def start_recording(self):
        """Démarre l'enregistrement audio"""
        self.audio_data = []
        self.is_recording = True
        self.start_time = time.time()
        
        # Configurer et démarrer le flux audio
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self.audio_callback
        )
        self.stream.start()
        
    def stop_recording(self):
        """Arrête l'enregistrement et retourne l'audio"""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        self.stream.stop()
        self.stream.close()
        
        # Récupérer toutes les données de la queue
        while not self.audio_queue.empty():
            self.audio_data.append(self.audio_queue.get())
            
        # Convertir en array numpy
        if self.audio_data:
            audio_array = np.concatenate(self.audio_data, axis=0)
            
            # Sauvegarder temporairement
            temp_file = "temp_recording.wav"
            sf.write(temp_file, audio_array, self.sample_rate)
            
            return temp_file
        return None
        
    def get_current_level(self):
        """Retourne le niveau audio actuel pour le vu-mètre"""
        if not self.is_recording:
            return 0.0
            
        try:
            return self.level_queue.get_nowait()
        except queue.Empty:
            return 0.0
            
    def get_duration(self):
        """Retourne la durée de l'enregistrement en cours"""
        if not self.is_recording or self.start_time is None:
            return 0.0
        return time.time() - self.start_time
        
    def get_recording_quality(self):
        """Retourne une estimation de la qualité de l'enregistrement"""
        if not self.is_recording:
            return 0.0
            
        try:
            level = self.get_current_level()
            # Une valeur entre 0 et 1 basée sur le niveau audio
            # Trop bas (< 0.1) ou trop haut (> 0.9) indique une mauvaise qualité
            if level < 0.1:
                quality = level * 10  # Augmentation linéaire jusqu'à 0.1
            elif level > 0.9:
                quality = 1.0 - (level - 0.9) * 10  # Diminution linéaire après 0.9
            else:
                quality = 1.0  # Niveau optimal entre 0.1 et 0.9
                
            return max(0.0, min(1.0, quality))
        except:
            return 0.0 