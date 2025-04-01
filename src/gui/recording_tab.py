"""
Module pour l'enregistrement vocal et la manipulation audio.

Ce module fournit une interface pour enregistrer, visualiser et manipuler
des données audio, avec intégration de la détection de volume, waveform,
et importation/exportation de fichiers audio.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QSlider, QPushButton, QComboBox, QFileDialog,
                              QGroupBox, QSplitter, QProgressBar, QSizePolicy,
                              QCheckBox, QMessageBox, QDialog, QLineEdit, QMainWindow,
                              QDialogButtonBox, QScrollArea)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QByteArray, QBuffer, QIODevice, QRect, QPoint, QMetaObject, QThread
from PySide6.QtGui import (QPainter, QPen, QColor, QLinearGradient, QPainterPath, 
                          QBrush, QPolygon)

import pyaudio
import wave
import numpy as np
import os
import time
import librosa
from scipy.io import wavfile
import sounddevice as sd
import soundfile as sf
import threading

# Importer le gestionnaire de modèles
from core.voice_cloning import model_manager

try:
    from PySide6.QtCore import Q_ARG
except ImportError:
    # Définir Q_ARG manuellement si non disponible
    def Q_ARG(type_name, value):
        return type_name, value


class WaveformVisualizer(QWidget):
    """Widget pour visualiser la forme d'onde audio"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.audio_data = np.zeros(1000)  # Données audio vides par défaut
        self.playback_position = 0  # Position actuelle de lecture
        self.setStyleSheet("background-color: #1a1a1a;")
        
        # Paramètres visuels améliorés
        self.gradient_start = QColor(30, 100, 255)  # Bleu clair
        self.gradient_end = QColor(64, 200, 255)    # Bleu-cyan
        self.playback_color = QColor(255, 80, 80)   # Rouge-orange
        self.grid_color = QColor(50, 50, 50, 120)
        
        # Données pour l'animation
        self.animation_offset = 0
        
        # Cache pour optimisation
        self.cached_width = -1
        self.cached_height = -1
        self.cached_points = None
        self.data_version = 0  # Compteur de version des données
        
        # Mutex pour éviter les problèmes de concurrence
        self.data_lock = threading.RLock()
        
        # Timer pour l'animation créé directement ici
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(50)  # 20 FPS
        
    def set_audio_data(self, data):
        """Définit les données audio à visualiser"""
        if data is None or len(data) == 0:
            return
            
        # Acquérir le verrou avant de modifier les données
        with self.data_lock:
            # Normaliser les données si elles ne le sont pas déjà
            if np.max(np.abs(data)) > 2.0:  # Probablement pas normalisé
                data = data.astype(np.float32) / 32768.0
                
            # Copier les données pour éviter les problèmes de référence
            self.audio_data = data.copy()
            self.data_version += 1  # Invalider le cache
            self.cached_width = -1  # Forcer la mise à jour du cache
            
        # Forcer un rafraîchissement
        self.update()
        
    def set_playback_position(self, position):
        """Définit la position actuelle de lecture"""
        # Acquérir le verrou avant de modifier la position
        with self.data_lock:
            self.playback_position = max(0.0, min(1.0, position))  # Limiter entre 0 et 1
            
        # Forcer un rafraîchissement
        QTimer.singleShot(0, self.update)
        
    def resizeEvent(self, event):
        """Gère le redimensionnement du widget"""
        super().resizeEvent(event)
        
        # Acquérir le verrou avant de modifier le cache
        with self.data_lock:
            # Invalider le cache lors du redimensionnement
            self.cached_width = -1
            
    def _prepare_waveform_points(self, width, height):
        """Prépare les points de forme d'onde (mise en cache pour optimisation)"""
        # Acquérir le verrou avant d'accéder au cache
        with self.data_lock:
            # Vérifier si on peut utiliser le cache
            if (width == self.cached_width and height == self.cached_height and 
                self.cached_points is not None):
                return self.cached_points
                
            # Vérifier que les données audio sont valides
            if len(self.audio_data) < 2:
                # Données insuffisantes, créer une ligne horizontale au centre
                center_y = height // 2
                points_top = [QPoint(i, center_y) for i in range(width)]
                points_bottom = [QPoint(i, center_y) for i in range(width-1, -1, -1)]
                all_points = points_top + points_bottom
                return all_points
                
            # Calculer le pas pour échantillonner les données
            step = max(1, len(self.audio_data) // width)
            center_y = height // 2
            
            # Points pour le chemin supérieur
            points_top = []
            for i in range(width):
                idx = min(int(i * step), len(self.audio_data) - 1)
                value = self.audio_data[idx]
                y = center_y - int(value * (height / 2 - 8))
                points_top.append(QPoint(i, y))
                
            # Points pour le chemin inférieur (miroir)
            points_bottom = []
            for i in range(width-1, -1, -1):
                idx = min(int(i * step), len(self.audio_data) - 1)
                value = self.audio_data[idx]
                y = center_y + int(value * (height / 2 - 8))
                points_bottom.append(QPoint(i, y))
                
            # Mettre en cache les résultats
            all_points = points_top + points_bottom
            self.cached_width = width
            self.cached_height = height
            self.cached_points = all_points
            
            return all_points

    def closeEvent(self, event):
        """Nettoyage lors de la fermeture du widget"""
        if self.update_timer and self.update_timer.isActive():
            self.update_timer.stop()
        super().closeEvent(event)
        
    def paintEvent(self, event):
        """Dessine la forme d'onde audio"""
        # Acquérir le verrou avant d'accéder aux données
        try:
            with self.data_lock:
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing)
                
                width = self.width()
                height = self.height()
                
                # Dessiner le fond
                background = QLinearGradient(0, 0, 0, height)
                background.setColorAt(0, QColor(22, 22, 26))
                background.setColorAt(1, QColor(16, 16, 20))
                painter.fillRect(0, 0, width, height, background)
                
                # Dessiner une grille discrète
                painter.setPen(QPen(self.grid_color, 1, Qt.DotLine))
                
                # Lignes horizontales
                for i in range(1, 4):
                    y = height * (i / 4)
                    painter.drawLine(0, y, width, y)
                    
                # Lignes verticales (moins fréquentes pour optimisation)
                for i in range(1, 5):
                    x = width * (i / 5)
                    painter.drawLine(x, 0, x, height)
                
                # Ligne centrale
                painter.setPen(QPen(QColor(70, 70, 80), 1))
                painter.drawLine(0, height // 2, width, height // 2)
                
                # Calculer les points de la forme d'onde (avec mise en cache)
                waveform_points = self._prepare_waveform_points(width, height)
                
                # Créer le chemin complet
                path = QPainterPath()
                path.addPolygon(QPolygon(waveform_points))
                
                # Définir le dégradé avec animation
                self.animation_offset = (self.animation_offset + 1) % 360
                gradient = QLinearGradient(0, 0, width, 0)
                angle = self.animation_offset / 360 * 6.28
                color1 = QColor(self.gradient_start)
                color2 = QColor(self.gradient_end)
                
                brightness = 0.8 + 0.2 * np.sin(angle)
                color1.setAlphaF(0.7 * brightness)
                color2.setAlphaF(0.7 * brightness)
                
                gradient.setColorAt(0, color1)
                gradient.setColorAt(1, color2)
                
                # Remplir la forme d'onde
                painter.fillPath(path, gradient)
                
                # Dessiner le contour avec une ligne plus fine pour optimisation
                painter.setPen(QPen(QColor(120, 180, 255, 150), 1.0))
                painter.drawPath(path)
                
                # Dessiner la position de lecture si > 0
                if self.playback_position > 0.001:  # Éviter les valeurs trop proches de zéro
                    position_x = int(self.playback_position * width)
                    
                    # Ligne animée
                    playback_pen = QPen(self.playback_color, 2)
                    painter.setPen(playback_pen)
                    painter.drawLine(position_x, 0, position_x, height)
                    
                    # Indicateur de position
                    indicator_size = 8
                    indicator_rect = QRect(position_x - indicator_size/2, 0, indicator_size, indicator_size)
                    painter.setBrush(QBrush(self.playback_color))
                    painter.drawEllipse(indicator_rect)
                    
                    # Texte de progression
                    progress_text = f"{int(self.playback_position * 100)}%"
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
                    painter.setPen(QPen(QColor(255, 255, 255, 220)))
                    painter.drawText(position_x + 8, indicator_size * 2, progress_text)
        except Exception as e:
            print(f"Erreur lors du dessin de la waveform: {e}")
        finally:
            # S'assurer que le peintre est correctement terminé
            if 'painter' in locals() and painter.isActive():
                painter.end()
                
    def __del__(self):
        """Destructeur pour nettoyer les ressources"""
        try:
            if hasattr(self, 'update_timer'):
                self.update_timer = None
        except Exception as e:
            print(f"Erreur lors du nettoyage du WaveformVisualizer: {e}")


class VUMeter(QWidget):
    """Widget pour afficher un VU-mètre"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(40, 120)
        self.level = 0.0           # Niveau actuel (0.0 - 1.0)
        self.peak = 0.0            # Niveau de pic (0.0 - 1.0)
        self.smoothed_level = 0.0  # Niveau lissé pour une animation plus fluide
        
        # Timer pour la décroissance du pic (créé sur le thread principal)
        self.peak_hold_timer = QTimer()
        self.peak_hold_timer.timeout.connect(self._decay_peak)
        self.peak_hold_timer.start(800)  # Décroissance du pic après 800ms
        
        # Timer pour la mise à jour visuelle
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(33)  # ~30 FPS
        
    def set_level(self, level):
        """Définit le niveau actuel (0.0 - 1.0)"""
        level = min(1.0, max(0.0, level))
        self.level = level
        
        # Lissage pour une animation plus fluide
        self.smoothed_level = self.smoothed_level * 0.7 + level * 0.3
        
        if level > self.peak:
            self.peak = level
            
        # Utiliser QTimer.singleShot pour déclencher l'update de manière thread-safe
        QTimer.singleShot(0, self.update)
        
    def _decay_peak(self):
        """Fait décroître le niveau de pic progressivement"""
        self.peak = max(0.0, self.peak - 0.05)
        QTimer.singleShot(0, self.update)
        
    def closeEvent(self, event):
        """Nettoyage lors de la fermeture du widget"""
        if hasattr(self, 'peak_hold_timer') and self.peak_hold_timer:
            if self.peak_hold_timer.isActive():
                self.peak_hold_timer.stop()
                
        if hasattr(self, 'update_timer') and self.update_timer:
            if self.update_timer.isActive():
                self.update_timer.stop()
                
        super().closeEvent(event)
        
    def __del__(self):
        """Destructeur pour nettoyer les ressources"""
        try:
            if hasattr(self, 'peak_hold_timer'):
                self.peak_hold_timer = None
            if hasattr(self, 'update_timer'):
                self.update_timer = None
        except Exception as e:
            print(f"Erreur lors du nettoyage du VUMeter: {e}")

    def paintEvent(self, event):
        """Dessine le VU-mètre"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            width = self.width()
            height = self.height()
            
            # Dessiner le fond avec dégradé
            background = QLinearGradient(0, 0, 0, height)
            background.setColorAt(0, QColor(22, 22, 26))
            background.setColorAt(1, QColor(16, 16, 20))
            painter.fillRect(0, 0, width, height, background)
            
            # Calculer les dimensions du mètre
            meter_width = width - 8
            meter_height = height - 8
            
            # Dessiner le cadre avec effet 3D
            frame_gradient = QLinearGradient(0, 0, width, height)
            frame_gradient.setColorAt(0, QColor(50, 50, 60))
            frame_gradient.setColorAt(1, QColor(35, 35, 45))
            
            painter.setPen(QPen(QColor(70, 70, 80), 1))
            painter.setBrush(QBrush(frame_gradient))
            painter.drawRoundedRect(2, 2, meter_width + 2, meter_height + 2, 4, 4)
            
            # Zone intérieure
            painter.fillRect(4, 4, meter_width - 2, meter_height - 2, QColor(20, 20, 25))
            
            # Dessiner les marques de graduations
            painter.setPen(QPen(QColor(80, 80, 100, 100), 1))
            
            # Points de référence de niveau (dB)
            db_points = [0.0, 0.12, 0.25, 0.37, 0.5, 0.63, 0.75, 0.88, 1.0]
            
            for level_point in db_points:
                y_pos = int(4 + (meter_height - 4) - level_point * (meter_height - 8))
                painter.drawLine(5, y_pos, meter_width, y_pos)
            
            # Dessiner le niveau actuel avec dégradé
            if self.smoothed_level > 0:
                level_height = int(self.smoothed_level * (meter_height - 8))
                
                # Dégradé de couleur en fonction du niveau
                gradient = QLinearGradient(0, height, 0, 0)
                gradient.setColorAt(0.0, QColor(0, 210, 0))    # Vert en bas
                gradient.setColorAt(0.65, QColor(220, 220, 0))  # Jaune au milieu
                gradient.setColorAt(0.8, QColor(240, 130, 0))  # Orange
                gradient.setColorAt(1.0, QColor(255, 30, 30))   # Rouge en haut
                
                # Rectangle avec coins arrondis pour le niveau
                level_rect = QRect(5, height - 4 - level_height, meter_width - 4, level_height)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(gradient))
                painter.drawRoundedRect(level_rect, 2, 2)
                
                # Effet de brillance
                highlight = QLinearGradient(0, 0, width, 0)
                highlight.setColorAt(0.0, QColor(255, 255, 255, 80))
                highlight.setColorAt(0.5, QColor(255, 255, 255, 40))
                highlight.setColorAt(1.0, QColor(255, 255, 255, 10))
                
                painter.setBrush(QBrush(highlight))
                painter.drawRoundedRect(level_rect, 2, 2)
            
            # Dessiner le niveau de pic avec effet de lueur
            if self.peak > 0:
                peak_y = height - 4 - int(self.peak * (meter_height - 8))
                
                # Déterminer la couleur du pic en fonction du niveau
                if self.peak > 0.8:
                    peak_color = QColor(255, 60, 60)  # Rouge
                elif self.peak > 0.65:
                    peak_color = QColor(255, 160, 0)  # Orange
                else:
                    peak_color = QColor(220, 220, 0)  # Jaune
                    
                # Ligne de pic avec effet de lueur
                glow_pen = QPen(peak_color, 2)
                painter.setPen(glow_pen)
                painter.drawLine(4, peak_y, width - 4, peak_y)
                
                # Point indicateur sur la ligne de pic
                painter.setBrush(QBrush(peak_color))
                painter.drawEllipse(width - 8, peak_y - 2, 4, 4)
                
                # Afficher la valeur en dB pour les niveaux élevés
                if self.peak > 0.5:
                    # Convertir valeur linéaire en dB approximatif
                    db_value = int(20 * np.log10(self.peak) + 3)  # +3 pour compenser
                    db_text = f"{db_value} dB"
                    
                    font = painter.font()
                    font.setPointSize(7)
                    painter.setFont(font)
                    
                    text_width = painter.fontMetrics().horizontalAdvance(db_text)
                    text_x = (width - text_width) / 2
                    
                    # Fond de texte semi-transparent
                    text_rect = QRect(int(text_x) - 2, peak_y - 14, text_width + 4, 12)
                    painter.fillRect(text_rect, QColor(0, 0, 0, 150))
                    
                    # Texte
                    painter.setPen(QPen(peak_color.lighter(130)))
                    painter.drawText(int(text_x), peak_y - 4, db_text)
        except Exception as e:
            print(f"Erreur lors du dessin du VU-mètre: {e}")
        finally:
            if 'painter' in locals() and painter.isActive():
                painter.end()


class AudioRecorder(QWidget):
    """Widget principal pour l'enregistrement audio"""
    
    recording_changed = Signal(bool)  # Signal émis quand l'état d'enregistrement change
    playback_changed = Signal(bool)   # Signal émis quand l'état de lecture change
    voice_cloned = Signal(str)        # Signal émis quand une voix est clonée avec succès
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration de base
        self.audio_data = None  # Données audio enregistrées
        self.sample_rate = 44100  # Taux d'échantillonnage par défaut
        self.is_recording = False
        self.is_playing = False
        self.record_thread = None
        self.play_thread = None
        self.audio = pyaudio.PyAudio()
        self.current_file_path = None  # Chemin du fichier actuel
        self.input_level = 0.0  # Niveau d'entrée audio
        
        # Taille de chunk pour l'enregistrement
        self.record_chunk_size = 1024  # Taille par défaut
        
        # Configuration de l'interface
        self.setup_ui()
        
        # Initialiser les périphériques audio
        self._update_audio_devices()
        
        # Timer pour mettre à jour l'interface
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start(50)  # 20 FPS
        
    def setup_ui(self):
        """Initialise l'interface utilisateur"""
        main_layout = QVBoxLayout(self)
        
        # Sélection des périphériques audio
        devices_group = QGroupBox("Périphériques Audio")
        devices_layout = QVBoxLayout(devices_group)
        
        # Entrée audio
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Entrée:"))
        self.input_combo = QComboBox()
        input_layout.addWidget(self.input_combo)
        devices_layout.addLayout(input_layout)
        
        # Sortie audio
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Sortie:"))
        self.output_combo = QComboBox()
        output_layout.addWidget(self.output_combo)
        devices_layout.addLayout(output_layout)
        
        # Bouton de rafraîchissement
        refresh_button = QPushButton("Rafraîchir")
        refresh_button.clicked.connect(self._update_audio_devices)
        devices_layout.addWidget(refresh_button)
        
        main_layout.addWidget(devices_group)
        
        # Visualisation centrale (forme d'onde)
        self.waveform = WaveformVisualizer()
        main_layout.addWidget(self.waveform, 1)  # Stretch factor 1
        
        # Affichage de la durée d'enregistrement
        duration_layout = QHBoxLayout()
        self.duration_label = QLabel("Durée: 00:00")
        self.duration_label.setAlignment(Qt.AlignCenter)
        duration_layout.addWidget(self.duration_label)
        main_layout.addLayout(duration_layout)
        
        # Contrôles de volume et de vitesse
        controls_group = QGroupBox("Contrôles")
        controls_group_layout = QHBoxLayout(controls_group)
        
        # VU-mètre d'entrée
        self.vu_meter_input = VUMeter()
        controls_group_layout.addWidget(self.vu_meter_input)
        
        # Fader de volume d'entrée
        input_vol_layout = QVBoxLayout()
        input_vol_layout.addWidget(QLabel("Entrée"))
        self.input_volume = QSlider(Qt.Vertical)
        self.input_volume.setRange(0, 100)
        self.input_volume.setValue(100)
        input_vol_layout.addWidget(self.input_volume)
        controls_group_layout.addLayout(input_vol_layout)
        
        # Fader de volume de sortie
        output_vol_layout = QVBoxLayout()
        output_vol_layout.addWidget(QLabel("Sortie"))
        self.output_volume = QSlider(Qt.Vertical)
        self.output_volume.setRange(0, 100)
        self.output_volume.setValue(80)
        output_vol_layout.addWidget(self.output_volume)
        controls_group_layout.addLayout(output_vol_layout)
        
        # Fader de vitesse de lecture
        speed_layout = QVBoxLayout()
        speed_layout.addWidget(QLabel("Vitesse"))
        self.playback_speed = QSlider(Qt.Vertical)
        self.playback_speed.setRange(50, 150)
        self.playback_speed.setValue(100)  # 100% = vitesse normale
        self.playback_speed.setTickPosition(QSlider.TicksRight)
        self.playback_speed.setTickInterval(10)
        speed_layout.addWidget(self.playback_speed)
        
        # Affichage de la valeur de vitesse
        self.speed_label = QLabel("1.0x")
        self.speed_label.setAlignment(Qt.AlignCenter)
        speed_layout.addWidget(self.speed_label)
        
        # Connecter le changement de valeur
        self.playback_speed.valueChanged.connect(self._update_speed_label)
        
        controls_group_layout.addLayout(speed_layout)
        
        main_layout.addWidget(controls_group)
        
        # Barre de contrôle
        controls_layout = QHBoxLayout()
        
        # Contrôles de transport
        self.record_button = QPushButton("⏺")
        self.record_button.setStyleSheet("font-size: 24px; min-width: 40px; min-height: 40px; color: red;")
        self.record_button.clicked.connect(self.toggle_recording)
        controls_layout.addWidget(self.record_button)
        
        self.play_button = QPushButton("▶")
        self.play_button.setStyleSheet("font-size: 24px; min-width: 40px; min-height: 40px;")
        self.play_button.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_button)
        
        self.stop_button = QPushButton("⏹")
        self.stop_button.setStyleSheet("font-size: 24px; min-width: 40px; min-height: 40px;")
        self.stop_button.clicked.connect(self.stop)
        controls_layout.addWidget(self.stop_button)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        controls_layout.addWidget(self.progress_bar, 1)  # Stretch factor 1
        
        main_layout.addLayout(controls_layout)
        
        # Boutons pour l'importation/exportation et le clonage de voix
        actions_layout = QHBoxLayout()
        
        self.import_button = QPushButton("Importer Audio")
        self.import_button.clicked.connect(self.import_audio)
        actions_layout.addWidget(self.import_button)
        
        self.export_button = QPushButton("Exporter Audio")
        self.export_button.clicked.connect(self.export_audio)
        actions_layout.addWidget(self.export_button)
        
        self.save_button = QPushButton("Sauvegarder")
        self.save_button.clicked.connect(self.save_audio)
        actions_layout.addWidget(self.save_button)
        
        self.clone_button = QPushButton("Cloner Voix")
        self.clone_button.clicked.connect(self.show_clone_dialog)
        actions_layout.addWidget(self.clone_button)
        
        main_layout.addLayout(actions_layout)
        
    def _update_audio_devices(self):
        """Met à jour la liste des périphériques audio"""
        # Sauvegarder les sélections actuelles
        current_input = self.input_combo.currentText()
        current_output = self.output_combo.currentText()
        
        # Effacer les combobox
        self.input_combo.clear()
        self.output_combo.clear()
        
        # Ajouter les périphériques d'entrée
        input_devices = []
        output_devices = []
        
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            device_name = device_info["name"]
            
            # Périphériques d'entrée
            if device_info["maxInputChannels"] > 0:
                self.input_combo.addItem(device_name, userData=i)
                input_devices.append(device_name)
                
            # Périphériques de sortie
            if device_info["maxOutputChannels"] > 0:
                self.output_combo.addItem(device_name, userData=i)
                output_devices.append(device_name)
                
        # Restaurer les sélections précédentes si possible
        if current_input in input_devices:
            self.input_combo.setCurrentText(current_input)
            
        if current_output in output_devices:
            self.output_combo.setCurrentText(current_output)
            
    def _update_ui(self):
        """Met à jour l'interface utilisateur"""
        # Optimisation: limiter la fréquence de mise à jour de l'interface
        now = time.time()
        if hasattr(self, '_last_ui_update') and now - self._last_ui_update < 0.03:  # Max ~33fps
            return
        self._last_ui_update = now
            
        # Mettre à jour le VU-mètre en fonction de l'activité
        if self.is_recording and hasattr(self, 'input_level'):
            # Pendant l'enregistrement, afficher le niveau d'entrée en temps réel
            self.vu_meter_input.set_level(self.input_level)
            
            # S'assurer que le bouton d'enregistrement est en mode "arrêt"
            if self.record_button.text() != "⏹":
                self.record_button.setText("⏹")
                
            # Mettre à jour la progression
            if hasattr(self, 'recorded_frames') and self.recorded_frames:
                # Mettre à jour la barre de progression à 100% pendant l'enregistrement
                # pour indiquer que l'enregistrement est actif
                if self.progress_bar.value() < 100:
                    self.progress_bar.setValue(100)
            
        elif self.is_playing and self.audio_data is not None:
            # Pendant la lecture, simuler le VU-mètre à partir des données audio
            if hasattr(self, 'playback_position'):
                # Calculer l'index de position
                position = int(self.playback_position * len(self.audio_data))
                
                # Optimisation: éviter les calculs si la position est invalide
                if 0 < position < len(self.audio_data) - 1024:
                    # Calculer le niveau de façon optimisée
                    window_size = min(1024, len(self.audio_data) - position)
                    window = self.audio_data[position:position+window_size]
                    
                    # Précalculer les valeurs absolues
                    abs_window = np.abs(window)
                    rms_level = np.sqrt(np.mean(np.square(abs_window)))
                    peak_level = np.max(abs_window)
                    
                    # Mélange pondéré
                    level = 0.6 * rms_level + 0.4 * peak_level
                    
                    # Appliquer le gain de sortie
                    output_gain = self.output_volume.value() / 100.0
                    self.vu_meter_input.set_level(level * output_gain)
                
                # S'assurer que le bouton de lecture est en mode "pause"
                if self.play_button.text() != "⏸":
                    self.play_button.setText("⏸")
                    
        else:
            # En mode inactif, décroissance naturelle
            self.vu_meter_input.set_level(0)
            
            # S'assurer que les boutons sont dans le bon état
            if self.is_recording and self.record_button.text() != "⏹":
                self.record_button.setText("⏹")
            elif not self.is_recording and self.record_button.text() != "⏺":
                self.record_button.setText("⏺")
                
            if self.is_playing and self.play_button.text() != "⏸":
                self.play_button.setText("⏸")
            elif not self.is_playing and self.play_button.text() != "▶":
                self.play_button.setText("▶")
                
        # Mettre à jour la barre de progression pendant la lecture
        if self.is_playing and hasattr(self, 'playback_position'):
            # Calcul du pourcentage de progression
            progress = int(self.playback_position * 100)
            
            # Mettre à jour la barre de progression si la valeur a changé
            if self.progress_bar.value() != progress:
                self.progress_bar.setValue(progress)
                # Forcer la mise à jour de la waveform si ce n'est pas fait ailleurs
                if progress % 10 == 0:  # Tous les 10%
                    self.waveform.set_playback_position(self.playback_position)
                
        # Vérifier si la waveform a besoin d'être mise à jour
        if self.audio_data is not None and not hasattr(self, '_last_waveform_update'):
            self._last_waveform_update = True
            self.waveform.set_audio_data(self.audio_data)
        
    def toggle_recording(self):
        """Démarre ou arrête l'enregistrement"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
            
    def start_recording(self):
        """Démarre l'enregistrement audio"""
        if self.is_recording:
            return

        # Réinitialiser les données d'enregistrement
        self.audio_stream = None
        self.recorded_frames = []
        self.is_recording = True
        self.recording_changed.emit(True)
        
        # Mettre à jour l'interface utilisateur
        self.record_button.setText("⏹")
        self.progress_bar.setValue(0)
        self.waveform.set_audio_data(np.zeros(1000))  # Réinitialiser la waveform
        self.waveform.set_playback_position(0)
        self.vu_meter_input.set_level(0)  # Réinitialiser le VU-mètre
        self.duration_label.setText("Durée: 00:00")  # Réinitialiser la durée
        
        # Mettre à jour l'interface utilisateur immédiatement
        self._update_ui()
        
        # Vérifier le périphérique d'entrée
        device_index = self.input_combo.currentData()
        if device_index is None:
            QMessageBox.warning(self, "Erreur", "Aucun périphérique d'entrée sélectionné")
            self.stop_recording()
            return
        
        # Démarrer le thread d'enregistrement
        self.recording_thread = threading.Thread(
            target=self._recording_thread,
            args=(device_index,),
            daemon=True
        )
        self.recording_thread.start()

    def _recording_thread(self, device_index):
        """Thread d'enregistrement audio"""
        try:
            # Configurer le flux audio
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                device=device_index,
                channels=1,
                callback=self._audio_callback,
                blocksize=self.record_chunk_size
            )
            
            # Démarrer l'enregistrement
            with self.audio_stream:
                # Boucle d'enregistrement - le callback fait le travail
                while self.is_recording and self.audio_stream.active:
                    # Attendre un peu pour éviter de surcharger le CPU
                    time.sleep(0.01)
        except Exception as e:
            print(f"Erreur d'enregistrement: {e}")
            # Utiliser invokeMethod pour accéder à l'UI thread-safe
            # Ne pas utiliser Q_ARG mais plutôt QTimer
            QTimer.singleShot(0, lambda error=str(e): self._show_recording_error(error))
        finally:
            # S'assurer que le statut est correct
            if self.is_recording:
                # Utiliser QTimer au lieu de invokeMethod
                QTimer.singleShot(0, self.stop_recording)
                
    def _show_recording_error(self, error_message):
        """Affiche un message d'erreur (appelé depuis le thread principal)"""
        QMessageBox.warning(self, "Erreur d'enregistrement", f"Une erreur s'est produite: {error_message}")
            
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback appelé par le flux audio pour chaque bloc de données"""
        if status:
            print(f"Status: {status}")
            
        # Ajouter les données au buffer
        if indata is not None and len(indata) > 0:
            self.recorded_frames.append(indata.copy())
            
            # Calculer le niveau audio pour le VU-mètre
            audio_abs = np.abs(indata)
            # Éviter la mise en garde np.mean sur un tableau vide
            if len(audio_abs) > 0:
                rms_level = np.sqrt(np.mean(np.square(audio_abs))) / 32768.0
                peak_level = np.max(audio_abs) / 32768.0
                
                # Combinaison pondérée pour un affichage plus naturel
                level = 0.7 * rms_level + 0.3 * peak_level
                self.input_level = min(1.0, level * 1.5)  # Amplifier légèrement pour meilleure visibilité
                
                # Mettre à jour le VU-mètre de façon thread-safe
                QTimer.singleShot(0, lambda lvl=self.input_level: self.vu_meter_input.set_level(lvl))
                
                # Mettre à jour la waveform tous les 2 blocs
                if len(self.recorded_frames) % 2 == 0:
                    # Récupérer toutes les données enregistrées jusqu'à présent
                    all_data = np.concatenate(self.recorded_frames)
                    # Limiter à 10 secondes max pour l'affichage en temps réel
                    display_data = all_data[-int(self.sample_rate * 10):]
                    
                    # Mettre à jour la waveform dans le thread principal
                    self._update_waveform_with_data(display_data)
                    
                    # Calculer la durée et mettre à jour l'étiquette
                    duration = len(all_data) / self.sample_rate
                    duration_str = f"{int(duration // 60):02d}:{int(duration % 60):02d}"
                    QTimer.singleShot(0, lambda d=duration_str: self.duration_label.setText(f"Durée: {d}"))
            
        # Mettre à jour l'interface dans le thread principal
        QTimer.singleShot(0, self._update_ui)
    
    def _update_waveform_with_data(self, data):
        """Met à jour la waveform avec les données (thread-safe)"""
        # Créer une copie locale des données
        data_copy = data.copy().flatten()
        
        # Mettre à jour la waveform de façon thread-safe
        try:
            # Utiliser QTimer.singleShot qui est thread-safe
            if self.waveform:
                QTimer.singleShot(0, lambda: self.waveform.set_audio_data(data_copy))
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la waveform: {e}")
            
    def stop_recording(self):
        """Arrête l'enregistrement audio"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.recording_changed.emit(False)
        
        # Fermer le flux d'enregistrement
        if self.audio_stream:
            self.audio_stream.close()
            self.audio_stream = None
            
        # Mettre à jour l'interface utilisateur
        self.record_button.setText("⏺")
        
        # S'il y a des données enregistrées, les convertir en tableau numpy
        if self.recorded_frames and len(self.recorded_frames) > 0:
            try:
                # Concaténer tous les frames enregistrés
                self.audio_data = np.concatenate(self.recorded_frames).flatten()
                
                # Mettre à jour la waveform
                QTimer.singleShot(0, lambda: self.waveform.set_audio_data(self.audio_data))
                QTimer.singleShot(0, lambda: self.waveform.set_playback_position(0))
                
                # Activer les boutons
                self.play_button.setEnabled(True)
                self.save_button.setEnabled(True)
                self.clone_button.setEnabled(True)
                self.export_button.setEnabled(True)
                
                # Calculer la durée
                duration = len(self.audio_data) / self.sample_rate
                duration_str = f"{int(duration // 60):02d}:{int(duration % 60):02d}"
                self.duration_label.setText(f"Durée: {duration_str}")
                
            except Exception as e:
                print(f"Erreur lors de la finalisation de l'enregistrement: {e}")
                QMessageBox.warning(self, "Erreur", 
                                 f"Impossible de traiter l'audio enregistré: {e}")
                
        # Réinitialiser les buffers
        self.recorded_frames = []
        
    def toggle_playback(self):
        """Démarre ou pause la lecture audio"""
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()
            
    def start_playback(self):
        """Démarre la lecture de l'audio enregistré"""
        if self.is_playing or self.audio_data is None:
            return
            
        # Arrêter l'enregistrement s'il est en cours
        if self.is_recording:
            self.stop_recording()
            
        # Initialiser les variables de lecture
        self.is_playing = True
        self.playback_position = 0
        self.playback_changed.emit(True)
            
        # Mettre à jour l'interface
        self.play_button.setText("⏸")
        self.progress_bar.setValue(0)
        
        # Préparer les données audio pour la lecture
        # Appliquer le gain de sortie
        output_gain = self.output_volume.value() / 100.0
        
        # Faire une copie pour éviter de modifier les données originales
        audio_for_playback = self.audio_data.copy() * output_gain
        
        # Mettre à jour la waveform
        self.waveform.set_audio_data(self.audio_data)  # Utiliser les données originales pour affichage
        self.waveform.set_playback_position(0)
        
        # Récupérer la vitesse de lecture
        playback_speed = self.playback_speed.value() / 100.0  # 0.5 à 1.5
        
        # Appliquer le changement de vitesse si nécessaire
        resampled_data = audio_for_playback
        
        # Utiliser le resampling uniquement si la vitesse n'est pas 1.0
        if abs(playback_speed - 1.0) > 0.01:
            try:
                import librosa
                # Resampling avec librosa pour un résultat de haute qualité
                resampled_data = librosa.effects.time_stretch(audio_for_playback, rate=1.0/playback_speed)
            except Exception as e:
                print(f"Erreur lors du resampling: {e}")
                # En cas d'erreur, utiliser les données originales
                resampled_data = audio_for_playback
        
        # Convertir en float32 pour la compatibilité avec sounddevice
        playback_data = resampled_data.astype(np.float32)
        
        # Calculer le nombre total de chunks pour le suivi de la progression
        chunk_size = 1024
        self.playback_total_chunks = (len(playback_data) + chunk_size - 1) // chunk_size
        
        # Lancer le thread de lecture
        self.playback_thread = threading.Thread(
            target=self._playback_thread,
            args=(playback_data, chunk_size, playback_speed),
            daemon=True
        )
        self.playback_thread.start()
        
        # Mettre à jour l'interface utilisateur
        QMetaObject.invokeMethod(self, "_update_ui", Qt.QueuedConnection)

    def _playback_thread(self, audio_data, chunk_size, playback_speed):
        """Thread de lecture audio optimisé"""
        try:
            # Ouvrir le stream de sortie
            with sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=None,
                blocksize=chunk_size
            ) as stream:
                # Variables pour suivre la progression
                position = 0
                update_counter = 0
                
                # Lecture par chunks pour plus de réactivité
                while self.is_playing and position < len(audio_data):
                    # Vérifier si on est en pause
                    if hasattr(self, 'is_paused') and self.is_paused:
                        time.sleep(0.1)
                        continue
                    
                    # Calculer la taille du chunk actuel (dernier chunk peut être plus petit)
                    current_chunk_size = min(chunk_size, len(audio_data) - position)
                    
                    # Extraire les données audio pour ce chunk
                    chunk = audio_data[position:position+current_chunk_size]
                    
                    # Écrire dans le stream audio
                    stream.write(chunk)
                    
                    # Mettre à jour la position
                    position += current_chunk_size
                    
                    # Calculer la position relative pour l'affichage
                    chunk_index = position // chunk_size
                    self.playback_position = chunk_index / self.playback_total_chunks
                    
                    # Mettre à jour la waveform et l'interface utilisateur périodiquement
                    update_counter += 1
                    if update_counter >= 5:  # Tous les 5 chunks
                        update_counter = 0
                        
                        # Utiliser QTimer.singleShot au lieu de invokeMethod
                        current_pos = self.playback_position
                        QTimer.singleShot(0, lambda pos=current_pos: self._update_playback_ui(pos))
                
                # Finaliser la lecture
                if self.is_playing:
                    # Si on a atteint la fin, marquer comme terminé
                    QTimer.singleShot(0, self._finish_playback)
                    
        except Exception as e:
            print(f"Erreur de lecture: {e}")
            # Gérer l'erreur dans le thread principal avec QTimer.singleShot
            error_msg = str(e)
            QTimer.singleShot(0, lambda msg=error_msg: self._show_playback_error(msg))
        finally:
            # S'assurer que les flags sont réinitialisés même en cas d'erreur
            if self.is_playing:
                QTimer.singleShot(0, self._finish_playback)
                
    def _show_playback_error(self, error_message):
        """Affiche un message d'erreur de lecture (thread-safe)"""
        QMessageBox.warning(self, "Erreur de lecture", f"Une erreur s'est produite: {error_message}")

    def _update_playback_ui(self, position):
        """Met à jour l'interface utilisateur pendant la lecture (thread-safe)"""
        # Mettre à jour la position de lecture
        self.playback_position = position
        
        # Mettre à jour la waveform
        self.waveform.set_playback_position(position)
        
        # Mettre à jour la barre de progression
        progress = int(position * 100)
        self.progress_bar.setValue(progress)
        
        # Assurer que le bouton de lecture est bien en pause
        if self.play_button.text() != "⏸":
            self.play_button.setText("⏸")

    def _finish_playback(self):
        """Finalise la lecture audio (thread-safe)"""
        # Réinitialiser les flags
        self.is_playing = False
        self.playback_changed.emit(False)
        
        # Réinitialiser l'interface
        self.play_button.setText("▶")
        self.progress_bar.setValue(0)
        
        # Réinitialiser la position de lecture
        self.playback_position = 0
        self.waveform.set_playback_position(0)
        
        # Mettre à jour l'UI
        self._update_ui()
        
    def pause_playback(self):
        """Met en pause la lecture audio"""
        if not self.is_playing:
            return
            
        self.is_playing = False
        
        # Attendre la fin du thread de lecture
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1.0)
            self.play_thread = None
            
        # Mettre à jour l'interface - passer en icône lecture
        self.play_button.setText("▶")
        self.playback_changed.emit(False)
        
    def stop(self):
        """Arrête l'enregistrement et la lecture"""
        if self.is_recording:
            self.stop_recording()
            
        if self.is_playing:
            self.pause_playback()
            
        # Réinitialiser la position de lecture
        self.playback_position = 0
        self.progress_bar.setValue(0)
        self.waveform.set_playback_position(0)
        
    def save_audio(self):
        """Sauvegarde l'audio actuel"""
        if self.audio_data is None:
            QMessageBox.warning(self, "Avertissement", "Aucune donnée audio à sauvegarder")
            return
            
        # Si un fichier est déjà ouvert, le sauvegarder directement
        if self.current_file_path:
            self._save_to_file(self.current_file_path)
        else:
            # Sinon, demander un nouveau chemin
            self.export_audio()
            
    def _save_to_file(self, file_path):
        """Sauvegarde les données audio vers un fichier spécifique"""
        try:
            # Exporter en fonction de l'extension
            ext = os.path.splitext(file_path)[1].lower()
            
            # Appliquer le gain de sortie
            output_gain = self.output_volume.value() / 100.0
            export_data = self.audio_data * output_gain
            
            if ext == '.wav':
                # Convertir en int16 pour WAV
                export_data_int = (export_data * 32767).astype(np.int16)
                wavfile.write(file_path, self.sample_rate, export_data_int)
            else:
                # Utiliser soundfile pour les autres formats
                sf.write(file_path, export_data, self.sample_rate)
                
            # Mettre à jour le chemin du fichier actuel
            self.current_file_path = file_path
            
            QMessageBox.information(self, "Sauvegarde réussie", 
                                  f"Audio sauvegardé avec succès vers:\n{file_path}")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Erreur de sauvegarde", 
                               f"Impossible de sauvegarder l'audio:\n{str(e)}")

    def import_audio(self):
        """Importe un fichier audio"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importer un fichier audio", "",
            "Fichiers audio (*.wav *.mp3 *.flac *.ogg);;Tous les fichiers (*.*)"
        )
        
        if not file_path:
            return
            
        try:
            # Charger le fichier audio
            audio_data, sample_rate = librosa.load(file_path, sr=None, mono=True)
            
            # Mettre à jour les données audio
            self.audio_data = audio_data
            self.sample_rate = sample_rate
            self.waveform.set_audio_data(audio_data)
            
            # Mettre à jour le chemin du fichier actuel
            self.current_file_path = file_path
            
            # Réinitialiser l'interface
            self.stop()
            
            QMessageBox.information(self, "Importation réussie", 
                                  f"Fichier audio importé avec succès:\n{os.path.basename(file_path)}")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Erreur d'importation", 
                               f"Impossible d'importer le fichier audio:\n{str(e)}")
                               
    def export_audio(self):
        """Exporte les données audio vers un fichier"""
        if self.audio_data is None:
            QMessageBox.warning(self, "Avertissement", "Aucune donnée audio à exporter")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter l'audio", "audio_export.wav",
            "Fichiers WAV (*.wav);;Fichiers MP3 (*.mp3);;Fichiers FLAC (*.flac)"
        )
        
        if not file_path:
            return
            
        self._save_to_file(file_path)
        
    def show_clone_dialog(self):
        """Affiche la boîte de dialogue pour cloner une voix"""
        if self.audio_data is None:
            QMessageBox.warning(self, "Avertissement", "Aucune donnée audio à cloner")
            return
            
        # Créer et afficher la boîte de dialogue de clonage
        dialog = CloneVoiceDialog(self)
        if dialog.exec():
            # Le clonage a réussi, on a un nouvel ID de modèle
            if dialog.cloned_model_id:
                self.voice_cloned.emit(dialog.cloned_model_id)

    def _update_speed_label(self, value):
        """Met à jour l'étiquette de vitesse"""
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.1f}x")

    def __del__(self):
        """Destructeur pour éviter les erreurs"""
        # Nettoyer toutes les ressources de façon sécurisée
        try:
            if hasattr(self, 'update_timer'):
                self.update_timer = None
                
            if hasattr(self, 'audio_stream') and self.audio_stream:
                self.audio_stream = None
                
            if hasattr(self, 'audio') and self.audio:
                try:
                    self.audio.terminate()
                except:
                    pass
                self.audio = None
        except Exception as e:
            print(f"Erreur lors du nettoyage de l'AudioRecorder: {e}")


class CloneVoiceDialog(QDialog):
    """Boîte de dialogue pour configurer le clonage de voix"""
    
    voice_cloned = Signal(str)  # Signal émis quand une voix est clonée avec succès
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Cloner une voix")
        self.setMinimumSize(450, 500)
        
        # Résultat du clonage
        self.cloned_model_id = None
        
        # Récupérer l'enregistreur parent
        self.recorder = parent
        
        # Configurer l'interface
        self.setup_ui()
        
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Introduction explicative
        intro_label = QLabel(
            "Créez un modèle vocal à partir de votre enregistrement.\n"
            "Ce modèle pourra être utilisé pour la synthèse vocale."
        )
        intro_label.setWordWrap(True)
        intro_label.setStyleSheet("font-style: italic; color: #666;")
        layout.addWidget(intro_label)
        
        # Nom de la voix
        name_group = QGroupBox("Nom de la voix")
        name_layout = QVBoxLayout(name_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Entrez un nom pour cette voix...")
        name_layout.addWidget(self.name_edit)
        
        layout.addWidget(name_group)
        
        # Modèle à utiliser
        model_group = QGroupBox("Moteur de clonage")
        model_layout = QVBoxLayout(model_group)
        
        # Ajouter une explication sur les moteurs
        engine_info = QLabel(
            "Chaque moteur a ses avantages :\n"
            "• OpenVoice V2 : Équilibre entre qualité et vitesse\n"
            "• Bark : Excellente qualité mais plus lent\n"
            "• Coqui TTS : Optimal pour les systèmes limités"
        )
        engine_info.setWordWrap(True)
        engine_info.setStyleSheet("font-size: 11px; color: #666;")
        model_layout.addWidget(engine_info)
        
        self.model_combo = QComboBox()
        
        # Ajouter les moteurs de clonage disponibles
        self.model_combo.addItem("OpenVoice V2", "openvoice_v2")
        self.model_combo.addItem("Bark", "bark")
        self.model_combo.addItem("Coqui TTS", "coqui_tts")
        
        # Description du moteur sélectionné
        self.engine_description = QLabel("")
        self.engine_description.setWordWrap(True)
        self.engine_description.setStyleSheet("font-style: italic; font-size: 11px;")
        
        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.engine_description)
        
        layout.addWidget(model_group)
        
        # Options avancées (collapsible)
        self.advanced_group = QGroupBox("Options avancées")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        advanced_layout = QVBoxLayout(self.advanced_group)
        
        # Qualité de clonage
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Qualité:"))
        
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 3)
        self.quality_slider.setValue(2)
        self.quality_slider.setTickPosition(QSlider.TicksBelow)
        self.quality_slider.setTickInterval(1)
        self.quality_slider.setFixedWidth(200)
        quality_layout.addWidget(self.quality_slider)
        
        quality_labels = QHBoxLayout()
        quality_labels.addWidget(QLabel("Rapide"))
        quality_labels.addStretch()
        quality_labels.addWidget(QLabel("Équilibré"))
        quality_labels.addStretch()
        quality_labels.addWidget(QLabel("Haute qualité"))
        
        advanced_layout.addLayout(quality_layout)
        advanced_layout.addLayout(quality_labels)
        
        # Prétraitement audio
        self.preprocess_check = QCheckBox("Prétraiter l'audio (normalisation, suppression des silences)")
        self.preprocess_check.setChecked(True)
        advanced_layout.addWidget(self.preprocess_check)
        
        # Formation multilingue renforcée
        self.multilingual_check = QCheckBox("Formation multilingue renforcée (plus lent)")
        self.multilingual_check.setChecked(False)
        advanced_layout.addWidget(self.multilingual_check)
        
        # Conseils pour de meilleurs résultats 
        tips_label = QLabel(
            "<b>Conseils pour de meilleurs résultats :</b><br>"
            "• Utilisez un audio de 10-30 secondes minimum<br>"
            "• Assurez-vous que l'audio est clair et sans bruit<br>"
            "• Parlez de manière naturelle avec une diction claire<br>"
            "• Évitez les pauses trop longues entre les phrases"
        )
        tips_label.setWordWrap(True)
        tips_label.setStyleSheet("font-size: 11px; background-color: #f0f0f0; padding: 8px;")
        advanced_layout.addWidget(tips_label)
        
        layout.addWidget(self.advanced_group)
        
        # Langues supportées
        languages_group = QGroupBox("Langues supportées")
        languages_layout = QVBoxLayout(languages_group)
        
        # Langues disponibles
        all_languages = {
            "fr": "Français",
            "en": "Anglais",
            "es": "Espagnol",
            "de": "Allemand",
            "it": "Italien",
            "zh": "Chinois",
            "ja": "Japonais",
            "pt": "Portugais",
            "ru": "Russe",
            "nl": "Néerlandais",
            "ar": "Arabe"
        }
        
        # Sélection rapide de langues
        quick_lang_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Tout sélectionner")
        self.select_all_btn.setFixedWidth(120)
        self.select_all_btn.clicked.connect(lambda: self.toggle_all_languages(True))
        quick_lang_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("Tout désélectionner")
        self.deselect_all_btn.setFixedWidth(120)
        self.deselect_all_btn.clicked.connect(lambda: self.toggle_all_languages(False))
        quick_lang_layout.addWidget(self.deselect_all_btn)
        
        languages_layout.addLayout(quick_lang_layout)
        
        # Scroll area pour les langues
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(150)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Créer les cases à cocher pour chaque langue
        self.language_checkboxes = {}
        for lang_code, lang_name in all_languages.items():
            checkbox = QCheckBox(lang_name)
            checkbox.setObjectName(lang_code)  # Stocker le code de langue dans l'attribut objectName
            scroll_layout.addWidget(checkbox)
            self.language_checkboxes[lang_code] = checkbox
        
        scroll_area.setWidget(scroll_widget)
        languages_layout.addWidget(scroll_area)
            
        # Mettre à jour les langues disponibles lorsque le modèle change
        self.model_combo.currentIndexChanged.connect(self.update_available_languages)
        self.model_combo.currentIndexChanged.connect(self.update_engine_description)
        
        layout.addWidget(languages_group)
        
        # Information sur la durée et estimation du temps
        self.duration_label = QLabel()
        self.duration_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.duration_label)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Message de progression
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
        # Boutons de contrôle
        buttons_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        self.clone_button = QPushButton("Cloner la voix")
        self.clone_button.clicked.connect(self.clone_voice)
        self.clone_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        buttons_layout.addWidget(self.clone_button)
        
        layout.addLayout(buttons_layout)
        
        # Initialiser les langues disponibles et l'affichage de la durée
        self.update_available_languages()
        self.update_engine_description()
        self.update_duration_info()
        
    def update_engine_description(self):
        """Met à jour la description du moteur sélectionné"""
        engine_id = self.model_combo.currentData()
        
        descriptions = {
            "openvoice_v2": "Crée une voix qui préserve bien le timbre et l'accent. "
                           "Bon équilibre entre vitesse et qualité.",
            "bark": "Produit des voix très naturelles avec une bonne expressivité. "
                   "Plus lent mais avec des résultats de haute qualité.",
            "coqui_tts": "Optimisé pour les systèmes limités. "
                        "Rapide et léger, idéal pour les phrases courtes."
        }
        
        self.engine_description.setText(descriptions.get(engine_id, ""))
        
    def update_duration_info(self):
        """Met à jour les informations de durée de l'audio"""
        if hasattr(self.recorder, 'audio_data') and self.recorder.audio_data is not None:
            duration = len(self.recorder.audio_data) / self.recorder.sample_rate
            
            # Estimer le temps de clonage en fonction du moteur sélectionné
            engine = self.model_combo.currentData()
            quality = self.quality_slider.value()
            
            base_times = {
                "openvoice_v2": 60,  # secondes
                "bark": 180,
                "coqui_tts": 45
            }
            
            # Ajuster en fonction de la qualité
            quality_multiplier = {1: 0.7, 2: 1.0, 3: 1.5}
            
            # Calculer l'estimation du temps
            est_time = base_times.get(engine, 60) * quality_multiplier.get(quality, 1.0)
            
            # Ajuster en fonction de la durée de l'audio
            est_time = est_time * (1 + (duration / 30))  # Plus l'audio est long, plus ça prend du temps
            
            # Afficher la durée et l'estimation
            self.duration_label.setText(
                f"Durée de l'audio: {int(duration // 60)}m {int(duration % 60)}s\n"
                f"Temps estimé: {int(est_time // 60)}m {int(est_time % 60)}s"
            )
        else:
            self.duration_label.setText("Durée de l'audio: 0s")
        
    def toggle_all_languages(self, state):
        """Sélectionne ou désélectionne toutes les langues disponibles"""
        for checkbox in self.language_checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(state)
        
    def update_available_languages(self):
        """Met à jour les langues disponibles en fonction du modèle sélectionné"""
        # Récupérer le modèle sélectionné
        engine_id = self.model_combo.currentData()
        
        if engine_id:
            # Récupérer les langues supportées par ce moteur
            engine_info = model_manager.get_model_info(engine_id)
            supported_languages = engine_info.get("languages", [])
            
            # Mettre à jour les cases à cocher
            for lang_code, checkbox in self.language_checkboxes.items():
                checkbox.setEnabled(lang_code in supported_languages)
                checkbox.setChecked(lang_code in supported_languages)
                
            # Mettre à jour l'estimation du temps
            self.update_duration_info()
                
    def clone_voice(self):
        """Traite le clonage de voix après validation"""
        # Vérifier si un nom a été entré
        voice_name = self.name_edit.text().strip()
        if not voice_name:
            QMessageBox.warning(self, "Nom manquant", "Veuillez entrer un nom pour cette voix")
            return
            
        # Récupérer le moteur sélectionné
        engine_id = self.model_combo.currentData()
        if not engine_id:
            QMessageBox.warning(self, "Moteur manquant", "Veuillez sélectionner un moteur")
            return
            
        # Récupérer les langues sélectionnées
        selected_languages = []
        for lang_code, checkbox in self.language_checkboxes.items():
            if checkbox.isChecked() and checkbox.isEnabled():
                selected_languages.append(lang_code)
                
        if not selected_languages:
            QMessageBox.warning(self, "Langues manquantes", "Veuillez sélectionner au moins une langue")
            return
            
        # Configurer la barre de progression
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Préparation du clonage...")
        self.progress_label.setVisible(True)
        
        # Désactiver les boutons pendant le traitement
        self.cancel_button.setEnabled(False)
        self.clone_button.setEnabled(False)
        
        # Préparer les paramètres
        params = {
            "voice_name": voice_name,
            "engine": engine_id,
            "languages": selected_languages,
            "sample_rate": self.recorder.sample_rate,
            "quality": self.quality_slider.value(),
            "preprocess": self.preprocess_check.isChecked(),
            "enhanced_multilingual": self.multilingual_check.isChecked()
        }
        
        # Créer une instance QThread pour gérer le clonage en arrière-plan
        self.clone_thread = QThread()
        self.clone_worker = CloneWorker(self.recorder.audio_data, params)
        self.clone_worker.moveToThread(self.clone_thread)
        
        # Connecter les signaux
        self.clone_thread.started.connect(self.clone_worker.run)
        self.clone_worker.progress.connect(self.update_progress)
        self.clone_worker.finished.connect(self.on_clone_finished)
        self.clone_worker.error.connect(self.on_clone_error)
        self.clone_worker.finished.connect(self.clone_thread.quit)
        self.clone_worker.finished.connect(self.clone_worker.deleteLater)
        self.clone_thread.finished.connect(self.clone_thread.deleteLater)
        
        # Démarrer le thread
        self.clone_thread.start()

    def update_progress(self, value, message):
        """Met à jour la barre de progression"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        
    def on_clone_finished(self, model_id):
        """Appelé lorsque le clonage est terminé avec succès"""
        self.progress_bar.setValue(100)
        self.progress_label.setText("Clonage terminé avec succès!")
        
        # Stocker l'ID du modèle cloné
        self.cloned_model_id = model_id
        
        # Réactiver les boutons
        self.cancel_button.setEnabled(True)
        self.clone_button.setEnabled(True)
        
        # Émettre le signal avec l'ID du modèle
        self.voice_cloned.emit(model_id)
        
        # Fermer la boîte de dialogue
        self.accept()
        
    def on_clone_error(self, error_message):
        """Appelé lorsqu'une erreur se produit pendant le clonage"""
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Erreur: " + error_message)
        self.progress_label.setStyleSheet("color: red;")
        
        # Réactiver les boutons
        self.cancel_button.setEnabled(True)
        self.clone_button.setEnabled(True)
        
# Worker pour le clonage de voix en arrière-plan
from PySide6.QtCore import QObject, Signal

class CloneWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, audio_data, params):
        super().__init__()
        self.audio_data = audio_data
        self.params = params
        
    def run(self):
        """Exécute le processus de clonage dans un thread séparé"""
        try:
            # Utiliser la méthode clone_voice du gestionnaire de modèles
            voice_name = self.params["voice_name"]
            engine = self.params["engine"]
            languages = self.params["languages"]
            sample_rate = self.params.get("sample_rate", 44100)
            
            # Fonction de callback pour reporter la progression
            def progress_callback(value, message):
                self.progress.emit(value, message)
            
            # Cloner la voix
            model_id = model_manager.clone_voice(
                self.audio_data, 
                sample_rate, 
                voice_name, 
                engine, 
                languages, 
                progress_callback
            )
            
            # Signaler que le clonage est terminé
            self.progress.emit(100, "Clonage terminé!")
            self.finished.emit(model_id)
            
        except Exception as e:
            self.error.emit(str(e))


class RecordingTab(QWidget):
    """Onglet principal pour l'enregistrement vocal"""
    
    voice_cloned = Signal(str)  # Signal émis quand une voix est clonée avec succès
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration de l'interface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Titre
        title_label = QLabel("Enregistrement Vocal")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Widget d'enregistrement
        self.recorder = AudioRecorder()
        self.recorder.voice_cloned.connect(self._on_voice_cloned)
        layout.addWidget(self.recorder)
        
    def _on_voice_cloned(self, model_id):
        """Gère le signal émis quand une voix est clonée"""
        # Propager le signal vers l'application principale
        self.voice_cloned.emit(model_id)

def safe_cleanup(obj, timer_attrs):
    """Utilitaire pour nettoyer les timers en toute sécurité"""
    for attr in timer_attrs:
        if hasattr(obj, attr):
            try:
                timer = getattr(obj, attr)
                if timer:
                    # Ne pas vérifier isActive() car ça peut causer des erreurs
                    try:
                        setattr(obj, attr, None)
                    except:
                        pass
            except Exception as e:
                print(f"Erreur lors du nettoyage de {attr}: {e}")
                setattr(obj, attr, None) 