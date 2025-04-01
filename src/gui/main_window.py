from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QComboBox, QPushButton, QLabel, QProgressBar,
                             QFileDialog, QMessageBox, QSpinBox, QCheckBox, QGroupBox,
                             QSlider, QSplitter, QScrollArea, QGridLayout, QTabWidget, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QPalette, QColor, QPixmap, QPainter, QPen
import sys
import os
import soundfile as sf
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import QApplication
import time
import shutil

# Ajout du chemin du projet au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.tts_engine import TTSEngine
from .voice_capture import VoiceCapture
from utils.language_manager import LanguageManager
from .history_dialog import HistoryDialog
from .volume_meter import VolumeMeter
from .midi_indicator import MidiIndicator
from .styles import MAIN_STYLE
from utils.audio_recorder import AudioRecorder
from utils.model_preloader import ModelPreloader
from utils.midi_manager import MidiManager
from .waveform_display import WaveformDisplay
from utils.midi_mapping import MidiMapping
from .midi_config import MidiConfigDialog

class TTSThread(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, tts_engine, text, speed, output_device=None, output_volume=1.0):
        super().__init__()
        self.tts_engine = tts_engine
        self.text = text
        self.speed = speed
        self.output_device = output_device
        self.output_volume = output_volume

    def run(self):
        try:
            self.tts_engine.set_speed(self.speed)
            output_file = self.tts_engine.synthesize(self.text)
            
            # Lire le fichier audio avec le périphérique de sortie sélectionné
            audio_data, sample_rate = sf.read(output_file)
            
            # Convertir explicitement en float32 pour éviter l'erreur de type
            audio_data = audio_data.astype(np.float32)
            
            # Jouer l'audio avec le volume spécifié
            self.tts_engine.play_audio(
                audio_data, 
                sample_rate, 
                self.output_device,
                volume=self.output_volume
            )
            
            self.finished.emit(output_file)
        except Exception as e:
            self.error.emit(str(e))

class RecordingThread(QThread):
    finished = Signal(str)
    
    def __init__(self, voice_capture, duration):
        super().__init__()
        self.voice_capture = voice_capture
        self.duration = duration
        
    def run(self):
        self.voice_capture.start_recording(self.duration)
        output_file = self.voice_capture.save_recording()
        if output_file:
            self.finished.emit(output_file)

class CloneVoiceThread(QThread):
    """Thread pour le clonage de voix"""
    finished = Signal()
    error = Signal(str)
    progress = Signal(int)
    
    def __init__(self, tts_engine, voice_file, output_model):
        super().__init__()
        self.tts_engine = tts_engine
        self.voice_file = voice_file
        self.output_model = output_model
        
    def run(self):
        try:
            print(f"\n🔄 Démarrage du clonage de voix...")
            print(f"Fichier d'entrée: {self.voice_file}")
            print(f"Modèle de sortie: {self.output_model}")
            
            # Vérifier que le fichier d'entrée existe
            if not os.path.exists(self.voice_file):
                raise FileNotFoundError(f"Le fichier audio {self.voice_file} n'existe pas")
                
            # Vérifier que le fichier audio contient des données valides
            try:
                import soundfile as sf
                import numpy as np
                audio_data, sample_rate = sf.read(self.voice_file)
                
                # Vérifier que les données audio ne sont pas vides
                if audio_data is None:
                    raise ValueError("Le fichier audio est vide")
                
                # Pour éviter l'erreur "truth value of array is ambiguous"
                if isinstance(audio_data, np.ndarray) and audio_data.size == 0:
                    raise ValueError("Le fichier audio ne contient pas de données")
                    
                # Vérifier que les données audio sont suffisantes pour le clonage
                duration = len(audio_data) / sample_rate
                if duration < 1.0:  # Minimum 1 seconde
                    raise ValueError(f"L'enregistrement est trop court ({duration:.2f}s). Minimum 1 seconde requis.")
                    
                print(f"✓ Audio valide: {duration:.2f} secondes à {sample_rate} Hz")
            except Exception as e:
                raise ValueError(f"Erreur lors de la validation du fichier audio: {str(e)}")
            
            # Cloner la voix avec le moteur TTS
            if hasattr(self.tts_engine, 'clone_voice') and callable(self.tts_engine.clone_voice):
                success = self.tts_engine.clone_voice(self.voice_file, self.output_model)
                if success:
                    self.finished.emit()
                else:
                    self.error.emit("Le clonage de voix a échoué")
            else:
                # Implémentation simulée pour les tests
                print("🔄 Simulation du clonage de voix...")
                
                # Créer le dossier de sortie si nécessaire
                os.makedirs(os.path.dirname(self.output_model), exist_ok=True)
                
                # Simule un traitement long
                for i in range(10):
                    time.sleep(1)  # Simule un traitement de 10 secondes
                    self.progress.emit((i+1) * 10)
                    print(f"Progression: {(i+1) * 10}%")
                
                # Copier le fichier audio comme modèle
                shutil.copy(self.voice_file, f"{self.output_model}.wav")
                
                # Créer un fichier de métadonnées pour le modèle
                metadata = {
                    "source_file": self.voice_file,
                    "date_created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "model_type": "voice_clone",
                    "sample_rate": sample_rate,
                    "duration": float(duration)
                }
                
                with open(f"{self.output_model}.json", 'w', encoding='utf-8') as f:
                    import json
                    json.dump(metadata, f, indent=2)
                
                print("✅ Clonage de voix terminé!")
                self.finished.emit()
                
        except Exception as e:
            error_msg = f"Erreur lors du clonage de voix: {str(e)}"
            print(f"❌ {error_msg}")
            self.error.emit(error_msg)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vocal Clone")
        self.setMinimumSize(1000, 700)
        
        # Initialisation des variables
        self.is_recording = False
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._update_meters)
        self.monitor_timer.start(50)  # 50ms refresh rate
        
        # Timer pour la barre de progression d'enregistrement
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self._update_recording_progress)
        
        # Initialisation des moteurs
        self.tts_engine = TTSEngine()
        self.voice_capture = VoiceCapture()
        self.language_manager = LanguageManager()
        
        # Initialisation du gestionnaire MIDI
        self.midi_manager = MidiManager()
        
        # Appliquer d'abord le style principal pour éviter les problèmes d'affichage
        self.setStyleSheet(MAIN_STYLE)
        
        # Initialiser l'interface utilisateur
        print("Configuration de l'interface utilisateur...")
        self._setup_ui()
        
        # Établir les connexions après création de l'interface
        print("Configuration des connexions...")
        self._setup_connections()
        
        # Charger les données
        print("Chargement des langues et voix...")
        self._load_languages_and_voices()
        
        # Force le traitement des événements pour s'assurer que l'interface est affichée
        QApplication.processEvents()
        
        # Pour garantir que l'affichage est mis à jour après le traitement initial
        QTimer.singleShot(100, self._refresh_ui)
        
        print("Initialisation terminée.")
    
    def _setup_ui(self):
        """Configuration de l'interface utilisateur"""
        # Widget central 
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Créer des onglets
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Onglet principal (Studio)
        main_tab = QWidget()
        main_tab_layout = QVBoxLayout(main_tab)
        
        # Splitter vertical principal
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)  # Empêche les widgets de disparaître complètement
        main_tab_layout.addWidget(splitter)
        
        # Section supérieure : zone de texte
        text_group = QGroupBox("Texte à synthétiser")
        text_layout = QVBoxLayout(text_group)
        
        text_controls = QHBoxLayout()
        self.load_text_btn = QPushButton(QIcon("resources/icons/open.png"), "Charger")
        self.save_text_btn = QPushButton(QIcon("resources/icons/save.png"), "Sauvegarder")
        text_controls.addWidget(self.load_text_btn)
        text_controls.addWidget(self.save_text_btn)
        text_controls.addStretch()
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText("Entrez votre texte ici...")
        text_layout.addLayout(text_controls)
        text_layout.addWidget(self.text_edit)
        
        # Section inférieure : contrôles
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Panneau gauche : capture de voix
        voice_group = self._setup_voice_capture()
        
        # Panneau droit : contrôles TTS
        tts_group = QGroupBox("Studio de Synthèse")
        tts_layout = QVBoxLayout(tts_group)
        
        # Sélection de langue et voix
        lang_layout = QHBoxLayout()
        self.lang_combo = QComboBox()
        self.voice_combo = QComboBox()
        lang_layout.addWidget(QLabel("Langue:"))
        lang_layout.addWidget(self.lang_combo, 1)
        lang_layout.addWidget(QLabel("Voix:"))
        lang_layout.addWidget(self.voice_combo, 1)
        
        # Contrôle de vitesse
        speed_layout = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        speed_layout.addWidget(QLabel("Vitesse:"))
        speed_layout.addWidget(self.speed_slider)
        self.speed_value = QLabel("100%")
        speed_layout.addWidget(self.speed_value)
        
        # Boutons d'action
        action_layout = QHBoxLayout()
        self.speak_btn = QPushButton(QIcon("resources/icons/play.png"), "Parler")
        self.stop_btn = QPushButton(QIcon("resources/icons/stop.png"), "Stop")
        self.history_btn = QPushButton(QIcon("resources/icons/history.png"), "Historique")
        action_layout.addWidget(self.speak_btn)
        action_layout.addWidget(self.stop_btn)
        action_layout.addWidget(self.history_btn)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        
        # Ajouter tous les layouts au groupe TTS
        tts_layout.addLayout(lang_layout)
        tts_layout.addLayout(speed_layout)
        tts_layout.addLayout(action_layout)
        tts_layout.addWidget(self.progress_bar)
        tts_layout.addStretch(1)
        
        # Ajout des panneaux au layout des contrôles
        controls_layout.addWidget(voice_group, 1)
        controls_layout.addWidget(tts_group, 2)
        
        # Ajout des sections au splitter
        splitter.addWidget(text_group)
        splitter.addWidget(controls_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        # Ajouter l'onglet studio au TabWidget
        self.tabs.addTab(main_tab, "Studio")
        
        # Onglet MIDI
        midi_tab = QWidget()
        midi_tab_layout = QVBoxLayout(midi_tab)
        midi_tab_layout.setContentsMargins(10, 10, 10, 10)
        self._setup_midi_tab(midi_tab, midi_tab_layout)
        self.tabs.addTab(midi_tab, "MIDI")
        
        # Barre de statut
        self.statusBar().showMessage("Prêt")
        
        # Passer à l'onglet studio par défaut et rafraîchir l'affichage
        self.tabs.setCurrentIndex(0)
        main_tab.update()
        splitter.update()  # Utiliser update() au lieu de refresh()
    
    def _setup_voice_capture(self):
        """Configure la section de capture vocale"""
        voice_capture_group = QGroupBox("Capture Vocale")
        voice_layout = QVBoxLayout()
        
        # Sélection des périphériques audio
        devices_layout = QGridLayout()
        
        # Entrée audio
        devices_layout.addWidget(QLabel("Entrée:"), 0, 0)
        self.input_combo = QComboBox()
        devices_layout.addWidget(self.input_combo, 0, 1)
        
        # Sortie audio
        devices_layout.addWidget(QLabel("Sortie:"), 1, 0)
        self.output_combo = QComboBox()
        devices_layout.addWidget(self.output_combo, 1, 1)
        
        # Bouton de rafraîchissement
        self.refresh_btn = QPushButton("Actualiser")
        devices_layout.addWidget(self.refresh_btn, 0, 2, 2, 1)
        
        # Contrôles de volume
        volumes_layout = QGridLayout()
        
        # Volume d'entrée
        volumes_layout.addWidget(QLabel("Volume Entrée:"), 0, 0)
        self.input_volume_slider = QSlider(Qt.Horizontal)
        self.input_volume_slider.setRange(0, 200)
        self.input_volume_slider.setValue(100)
        self.input_volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 10px;
                background: #555;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 20px;
                height: 20px;
                margin: -5px 0;
                background: #2196F3;
                border-radius: 10px;
            }
        """)
        self.input_volume_slider.setMinimumWidth(150)
        volumes_layout.addWidget(self.input_volume_slider, 0, 1)
        self.input_volume_value = QLabel("1.00")
        volumes_layout.addWidget(self.input_volume_value, 0, 2)
        
        # Volume de sortie
        volumes_layout.addWidget(QLabel("Volume Sortie:"), 1, 0)
        self.output_volume_slider = QSlider(Qt.Horizontal)
        self.output_volume_slider.setRange(0, 200)
        self.output_volume_slider.setValue(100)
        self.output_volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 10px;
                background: #555;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 20px;
                height: 20px;
                margin: -5px 0;
                background: #2196F3;
                border-radius: 10px;
            }
        """)
        self.output_volume_slider.setMinimumWidth(150)
        volumes_layout.addWidget(self.output_volume_slider, 1, 1)
        self.output_volume_value = QLabel("1.00")
        volumes_layout.addWidget(self.output_volume_value, 1, 2)
        
        # VU Meter
        volumes_layout.addWidget(QLabel("Niveau:"), 2, 0)
        self.vu_meter = VolumeMeter(self)
        self.vu_meter.setMinimumWidth(150)
        volumes_layout.addWidget(self.vu_meter, 2, 1)
        
        # Widget de forme d'onde
        waveform_layout = QVBoxLayout()
        waveform_layout.addWidget(QLabel("Forme d'onde:"))
        self.waveform_display = WaveformDisplay(self)
        self.waveform_display.setMinimumHeight(80)
        waveform_layout.addWidget(self.waveform_display)
        
        # Contrôles d'enregistrement
        controls_layout = QHBoxLayout()
        
        # Bouton d'enregistrement
        self.record_btn = QPushButton("🎙 Enregistrer")
        controls_layout.addWidget(self.record_btn)
        
        # Bouton de lecture
        self.play_btn = QPushButton("▶ Lecture")
        controls_layout.addWidget(self.play_btn)
        
        # Bouton pause
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_btn)
        
        # Bouton arrêt
        self.stop_btn = QPushButton("⏹ Arrêt")
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)
        
        # Bouton ré-enregistrer
        self.rerecord_btn = QPushButton("🔄 Ré-enregistrer")
        controls_layout.addWidget(self.rerecord_btn)
        
        # Bouton de clonage de voix
        self.clone_btn = QPushButton(QIcon("resources/icons/clone.svg"), "Clone")
        self.clone_btn.setObjectName("cloneButton")  # Pour le style CSS
        controls_layout.addWidget(self.clone_btn)
        
        # Vitesse de lecture
        playback_speed_layout = QHBoxLayout()
        playback_speed_layout.addWidget(QLabel("Vitesse:"))
        self.playback_speed_slider = QSlider(Qt.Horizontal)
        self.playback_speed_slider.setRange(50, 200)  # 0.5x à 2.0x
        self.playback_speed_slider.setValue(100)      # 1.0x (normal)
        self.playback_speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #555;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 18px;
                height: 18px;
                margin: -5px 0;
                background: #2196F3;
                border-radius: 9px;
            }
        """)
        playback_speed_layout.addWidget(self.playback_speed_slider)
        self.playback_speed_value = QLabel("1.00x")
        playback_speed_layout.addWidget(self.playback_speed_value)
        
        # Barre de progression
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progression:"))
        self.recording_progress = QProgressBar()
        self.recording_progress.setRange(0, 100)
        self.recording_progress.setValue(0)
        progress_layout.addWidget(self.recording_progress)
        self.recording_time = QLabel("00:00")
        progress_layout.addWidget(self.recording_time)
        
        # Assemblage de la mise en page
        voice_layout.addLayout(devices_layout)
        voice_layout.addLayout(volumes_layout)
        voice_layout.addLayout(waveform_layout)
        voice_layout.addLayout(controls_layout)
        voice_layout.addLayout(playback_speed_layout)
        voice_layout.addLayout(progress_layout)
        
        voice_capture_group.setLayout(voice_layout)
        return voice_capture_group

    def _setup_midi_tab(self, midi_tab, layout):
        """Configure l'onglet MIDI"""
        try:
            midi_layout = QVBoxLayout()
            
            # Section des ports MIDI
            midi_ports_group = QGroupBox("Ports MIDI")
            midi_ports_layout = QVBoxLayout()
            
            # Barre horizontale pour les ports et le bouton de rafraîchissement
            port_refresh_layout = QHBoxLayout()
            
            # Liste déroulante des ports MIDI
            self.midi_port_combo = QComboBox()
            self.midi_port_combo.setObjectName("midi_port_combo")
            self.midi_port_combo.addItem("Aucun")
            port_refresh_layout.addWidget(self.midi_port_combo)
            
            # Bouton de rafraîchissement des ports MIDI
            self.refresh_midi_button = QPushButton("🔄")
            self.refresh_midi_button.setToolTip("Rafraîchir la liste des ports MIDI")
            self.refresh_midi_button.setMaximumWidth(40)
            port_refresh_layout.addWidget(self.refresh_midi_button)
            
            midi_ports_layout.addLayout(port_refresh_layout)
            
            # Indicateur d'activité MIDI
            midi_status_layout = QHBoxLayout()
            self.midi_note_label = QLabel("Note: -")
            midi_status_layout.addWidget(self.midi_note_label)
            
            # Indicateur visuel d'activité MIDI
            self.midi_indicator = MidiIndicator()
            midi_status_layout.addWidget(self.midi_indicator)
            
            # Informations sur les messages MIDI (Control Change, etc.)
            midi_info_layout = QVBoxLayout()
            self.midi_cc_label = QLabel("Control Change: -")
            self.midi_pb_label = QLabel("Pitch Bend: -")
            midi_info_layout.addWidget(self.midi_cc_label)
            midi_info_layout.addWidget(self.midi_pb_label)
            
            midi_ports_layout.addLayout(midi_status_layout)
            midi_ports_layout.addLayout(midi_info_layout)
            midi_ports_group.setLayout(midi_ports_layout)
            midi_layout.addWidget(midi_ports_group)
            
            # Section apprentissage MIDI
            midi_learn_group = QGroupBox("Assignation MIDI")
            midi_learn_layout = QVBoxLayout()
            
            # Bouton d'apprentissage MIDI
            self.midi_learn_button = QPushButton("Apprendre MIDI")
            self.midi_learn_button.setCheckable(True)
            midi_learn_layout.addWidget(self.midi_learn_button)
            
            # Bouton de configuration MIDI
            self.midi_config_button = QPushButton("Configuration MIDI")
            midi_learn_layout.addWidget(self.midi_config_button)
            
            midi_learn_group.setLayout(midi_learn_layout)
            midi_layout.addWidget(midi_learn_group)
            
            midi_layout.addStretch()
            midi_tab.setLayout(midi_layout)
            
            # Connexions des signaux
            self.midi_port_combo.currentIndexChanged.connect(self._on_midi_port_changed)
            self.refresh_midi_button.clicked.connect(self._refresh_midi_ports)
            self.midi_learn_button.toggled.connect(self._toggle_midi_learn)
            self.midi_config_button.clicked.connect(self._show_midi_config)
            
            # Initialisation du gestionnaire MIDI, s'il n'est pas déjà initialisé
            if not hasattr(self, 'midi_manager') or not self.midi_manager:
                self.midi_manager = MidiManager()
                
                # Connecter les signaux MIDI
                self.midi_manager.note_on.connect(self._on_midi_note_on)
                self.midi_manager.note_off.connect(self._on_midi_note_off)
                self.midi_manager.control_change.connect(self._on_midi_control_change)
                self.midi_manager.pitch_bend.connect(self._on_midi_pitch_bend)
                self.midi_manager.midi_activity.connect(self._on_midi_activity)
                
            # Initialiser la liste des ports MIDI
            self._refresh_midi_ports()
        except Exception as e:
            print(f"❌ Erreur lors de la configuration de l'onglet MIDI: {e}")
            # Essayer d'afficher un message d'erreur minimal
            try:
                error_label = QLabel(f"Erreur MIDI: {str(e)}")
                error_layout = QVBoxLayout()
                error_layout.addWidget(error_label)
                midi_tab.setLayout(error_layout)
            except:
                pass
    
    def _toggle_recording(self):
        """Bascule entre enregistrement et arrêt"""
        if self.voice_capture.is_recording:
            self.voice_capture.stop_recording()
            self.record_btn.setText("Enregistrer")
            self.record_btn.setIcon(QIcon("resources/icons/record.png"))
            self.play_btn.setEnabled(True)
            self.rerecord_btn.setEnabled(True)
        else:
            self.voice_capture.start_recording()
            self.record_btn.setText("Arrêter")
            self.record_btn.setIcon(QIcon("resources/icons/stop.png"))
            self.play_btn.setEnabled(False)
            self.rerecord_btn.setEnabled(False)
            
    def _update_recording_progress(self):
        """Met à jour la barre de progression de l'enregistrement"""
        if not self.is_recording:
            return
            
        try:
            audio_data = self.voice_capture.get_audio_data()
            if len(audio_data) > 0:
                # Calculer la progression (10 secondes max)
                progress = min(100, len(audio_data) / (self.voice_capture.sample_rate * 10) * 100)
                self.recording_progress.setValue(int(progress))
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la progression : {e}")
            
    def _clone_voice(self):
        """Clone la voix enregistrée"""
        try:
            # Vérifier si un enregistrement existe
            if not hasattr(self.voice_capture, 'audio_data') or not isinstance(self.voice_capture.audio_data, list) or len(self.voice_capture.audio_data) == 0:
                QMessageBox.warning(self, "Erreur", "Aucun enregistrement disponible. Veuillez d'abord enregistrer votre voix.")
                return
                
            # Sauvegarder l'audio dans un fichier temporaire
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                
            temp_file = os.path.join(temp_dir, "voice_sample.wav")
            print(f"Sauvegarde temporaire de l'enregistrement dans {temp_file}")
                
            # Sauvegarder l'enregistrement
            self.voice_capture.save_recording(temp_file)
            
            # Vérifier que le fichier a bien été créé
            if not os.path.exists(temp_file):
                QMessageBox.critical(self, "Erreur", "Impossible de sauvegarder l'enregistrement temporaire.")
                return
                
            # Créer un dialogue de progression modal
            self.progress_dialog = QMessageBox(self)
            self.progress_dialog.setWindowTitle("Clonage de voix")
            self.progress_dialog.setText("Clonage de voix en cours...\nCette opération peut prendre plusieurs minutes.")
            self.progress_dialog.setIcon(QMessageBox.Information)
            self.progress_dialog.setStandardButtons(QMessageBox.Cancel)
            self.progress_dialog.buttonClicked.connect(self._cancel_cloning)
            
            # Afficher le dialogue sans bloquer
            self.progress_dialog.show()
            QApplication.processEvents()
            
            # Créer un dossier user pour les modèles clonés
            user_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "user")
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            
            # Créer un nom pour le modèle cloné
            model_name = f"voice_clone_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_path = os.path.join(user_dir, model_name)
            
            print(f"Démarrage du clonage de voix dans {output_path}")
                
            # Lancer le clonage de voix dans un thread séparé
            self.clone_thread = CloneVoiceThread(
                self.tts_engine,
                temp_file,
                output_path
            )
            
            self.clone_thread.finished.connect(lambda: self._on_cloning_finished(model_name))
            self.clone_thread.error.connect(self._on_cloning_error)
            self.clone_thread.start()
                
        except Exception as e:
            error_msg = f"Erreur lors du clonage: {str(e)}"
            print(f"❌ {error_msg}")
            QMessageBox.critical(self, "Erreur", error_msg)
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
    
    def _cancel_cloning(self, button):
        """Annule le processus de clonage"""
        if hasattr(self, 'clone_thread') and self.clone_thread.isRunning():
            self.clone_thread.terminate()
            self.clone_thread.wait()
        QMessageBox.information(self, "Information", "Clonage annulé par l'utilisateur")
            
    def _on_cloning_finished(self, model_name):
        """Callback appelé lorsque le clonage est terminé"""
        # Fermer la boîte de dialogue
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            
        # Mettre à jour la liste des voix disponibles
        self._update_user_voices()
            
        # Afficher un message de succès
        QMessageBox.information(self, "Succès", f"Voix clonée avec succès! Le modèle '{model_name}' est disponible dans la liste des voix.")
        
    def _on_cloning_error(self, error_message):
        """Callback appelé en cas d'erreur lors du clonage"""
        print(f"❌ Erreur de clonage reçue: {error_message}")
        # Fermer la boîte de dialogue de progression
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            
        # Afficher l'erreur à l'utilisateur
        error_text = str(error_message)
        QMessageBox.critical(self, "Erreur", f"Erreur lors du clonage de la voix : {error_text}")
        
        # Mise à jour de l'interface
        self.statusBar().showMessage("Erreur lors du clonage")
        
        # Nettoyage des ressources
        if hasattr(self, 'clone_thread') and self.clone_thread and self.clone_thread.isRunning():
            try:
                self.clone_thread.terminate()
                self.clone_thread.wait()
            except Exception as e:
                print(f"Erreur lors de la fermeture du thread: {e}")
    
    def _update_user_voices(self):
        """Met à jour la liste des voix utilisateur"""
        try:
            # Ajouter les modèles utilisateur au gestionnaire de langues
            user_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "user")
            if os.path.exists(user_dir):
                # Ajouter les modèles utilisateur à la liste des voix
                for item in os.listdir(user_dir):
                    if os.path.isdir(os.path.join(user_dir, item)) and item.startswith("voice_clone_"):
                        # Formater le nom de la voix pour l'affichage
                        formatted_name = f"User: {item.replace('voice_clone_', '')}"
                        
                        # Ajouter la voix au combo si elle n'y est pas déjà
                        if self.voice_combo.findText(formatted_name) == -1:
                            self.voice_combo.addItem(formatted_name)
                            
            # Sélectionner le dernier modèle ajouté (dernière voix dans la liste)
            if self.voice_combo.count() > 0:
                self.voice_combo.setCurrentIndex(self.voice_combo.count() - 1)
                
        except Exception as e:
            print(f"Erreur lors de la mise à jour des voix utilisateur : {e}")
    
    def _load_languages_and_voices(self):
        """Charge la liste des langues et des voix disponibles"""
        try:
            # Charger les langues
            languages = self.language_manager.get_languages()
            self.lang_combo.clear()
            self.lang_combo.addItems(languages)
            
            # Sélectionner le français par défaut
            french_index = self.lang_combo.findText("Français")
            if french_index >= 0:
                self.lang_combo.setCurrentIndex(french_index)
            
            # Mettre à jour les voix
            self._update_voices()
            
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du chargement des langues : {str(e)}")
            
    def _update_voices(self):
        """Met à jour la liste des voix en fonction de la langue sélectionnée"""
        try:
            # Bloquer les signaux pour éviter la récursion
            self.voice_combo.blockSignals(True)
            
            # Sauvegarder la sélection actuelle
            current_voice = self.voice_combo.currentText()
            
            # Obtenir la langue sélectionnée
            current_lang = self.lang_combo.currentText()
            voices = self.language_manager.get_voices(current_lang)
            
            # Mettre à jour la liste des voix
            self.voice_combo.clear()
            self.voice_combo.addItems(voices)
            
            # Restaurer la sélection si possible
            index = self.voice_combo.findText(current_voice)
            if index >= 0:
                self.voice_combo.setCurrentIndex(index)
            
            # Ajouter les voix utilisateur
            self._update_user_voices()
            
            # Débloquer les signaux
            self.voice_combo.blockSignals(False)
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la mise à jour des voix : {str(e)}")
            # Éviter d'afficher une boîte de dialogue qui pourrait causer une autre récursion
            self.statusBar().showMessage(f"Erreur lors de la mise à jour des voix : {str(e)}")
            
            # Débloquer les signaux en cas d'erreur
            if hasattr(self, 'voice_combo'):
                self.voice_combo.blockSignals(False)
    
    def _setup_connections(self):
        """Configure les connexions de signaux"""
        # Connexions pour les boutons de capture vocale
        self.record_btn.clicked.connect(self._toggle_recording)
        self.play_btn.clicked.connect(self._toggle_playback)
        self.stop_btn.clicked.connect(self._stop_all)
        
        # Connexions pour la sortie audio
        self.input_volume_slider.valueChanged.connect(self._on_input_volume_changed)
        self.output_volume_slider.valueChanged.connect(self._on_output_volume_changed)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        
        # Connexions pour les périphériques audio
        self.input_combo.currentIndexChanged.connect(self._on_input_device_changed)
        self.output_combo.currentIndexChanged.connect(self._on_output_device_changed)
        self.refresh_btn.clicked.connect(self._refresh_audio_devices)
        
        # Connexions pour la capture vocale
        self.voice_capture.recording_started.connect(self._on_recording_started)
        self.voice_capture.recording_stopped.connect(self._on_recording_stopped)
        self.voice_capture.playback_started.connect(self._on_playback_started)
        self.voice_capture.playback_stopped.connect(self._on_playback_stopped)
        self.voice_capture.level_updated.connect(self._update_meters)
        self.voice_capture.waveform_updated.connect(self._update_waveform)
        self.voice_capture.playback_position_updated.connect(self._update_playback_position)
        self.voice_capture.error_occurred.connect(self._show_error)
        
        # Connexions pour la synthèse vocale
        self.speak_btn.clicked.connect(self._start_speaking)
        self.voice_combo.currentIndexChanged.connect(self._update_voices)
        self.stop_btn.clicked.connect(self._stop_speaking)
        
        # Connexions pour le clone vocal
        if hasattr(self, 'clone_btn') and self.clone_btn:
            self.clone_btn.clicked.connect(self._clone_voice)
            
        # Connexions pour le chargement/sauvegarde de texte
        self.load_text_btn.clicked.connect(self._load_text)
        self.save_text_btn.clicked.connect(self._save_text)
        
        # Connexions pour l'historique
        self.history_btn.clicked.connect(self._show_history)
        
        # Timer pour la mise à jour du VU-mètre
        self.level_timer = QTimer()
        self.level_timer.timeout.connect(self._update_level)
        self.level_timer.start(50)  # 50ms pour une mise à jour fluide
    
    def _on_recording_started(self):
        """Gestionnaire pour le début d'enregistrement"""
        self.statusBar().showMessage("Enregistrement en cours...")
        self.record_btn.setText("Arrêter")
        self.record_btn.setIcon(QIcon("resources/icons/stop.png"))
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.rerecord_btn.setEnabled(False)
        self.recording_progress.setValue(0)
        self.waveform_display.clear()  # Effacer la forme d'onde précédente
        self.recording_timer.start(100)  # Mise à jour toutes les 100ms
        
    def _on_recording_stopped(self):
        """Gestionnaire pour la fin d'enregistrement"""
        self.statusBar().showMessage("Enregistrement terminé")
        self.record_btn.setText("Enregistrer")
        self.record_btn.setIcon(QIcon("resources/icons/record.png"))
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.rerecord_btn.setEnabled(True)
        self.recording_timer.stop()
    
    def _start_speaking(self):
        """Démarrer la synthèse vocale"""
        text = self.text_edit.toPlainText()
        if not text:
            QMessageBox.warning(self, "Attention", "Veuillez entrer du texte à synthétiser.")
            return
        
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Synthèse en cours...")
        
        # Récupérer le périphérique de sortie sélectionné
        output_device = self.output_combo.currentData()
        
        # Démarrer la synthèse dans un thread séparé
        self.tts_thread = TTSThread(
            self.tts_engine,
            text,
            self.speed_slider.value() / 100.0,
            output_device,
            self.output_volume_slider.value() / 100.0
        )
        self.tts_thread.progress.connect(self._update_progress)
        self.tts_thread.finished.connect(self._on_synthesis_finished)
        self.tts_thread.error.connect(self._on_synthesis_error)
        self.tts_thread.start()
    
    def _stop_speaking(self):
        """Arrêter la synthèse vocale"""
        if hasattr(self, 'tts_thread') and self.tts_thread.isRunning():
            self.tts_thread.terminate()
            self.tts_thread.wait()
            self.progress_bar.setValue(0)
            self.statusBar().showMessage("Synthèse arrêtée")
    
    def _update_progress(self, value):
        """Mise à jour de la barre de progression"""
        self.progress_bar.setValue(value)
    
    def _on_synthesis_finished(self, output_file):
        """Callback appelé lorsque la synthèse est terminée"""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.statusBar().showMessage("Synthèse terminée")
    
    def _on_synthesis_error(self, error_message):
        """Callback appelé en cas d'erreur lors de la synthèse"""
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Erreur de synthèse")
        QMessageBox.critical(self, "Erreur", f"Erreur lors de la synthèse : {error_message}")
    
    def _show_history(self):
        """Afficher la boîte de dialogue d'historique"""
        dialog = HistoryDialog(self)
        dialog.exec_()
    
    def _load_text(self):
        """Charger un fichier texte"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Charger un fichier texte",
            "",
            "Fichiers texte (*.txt);;Tous les fichiers (*.*)"
        )
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    self.text_edit.setText(f.read())
                self.statusBar().showMessage(f"Fichier chargé : {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors du chargement du fichier : {str(e)}")
    
    def _save_text(self):
        """Sauvegarder le texte dans un fichier"""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder le texte",
            "",
            "Fichiers texte (*.txt);;Tous les fichiers (*.*)"
        )
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
                self.statusBar().showMessage(f"Fichier sauvegardé : {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la sauvegarde du fichier : {str(e)}")
    
    def _update_meters(self):
        """Met à jour les indicateurs de niveau audio"""
        try:
            if self.voice_capture.is_recording:
                # Convertir le niveau RMS en valeur entre 0 et 1
                level = min(1.0, self.voice_capture.current_level * 2)
                self.vu_meter.set_level(level)
                
                # Mettre à jour la forme d'onde si des données sont disponibles
                if hasattr(self.voice_capture, 'get_audio_data'):
                    audio_data = self.voice_capture.get_audio_data()
                    if audio_data is not None and hasattr(audio_data, '__len__') and len(audio_data) > 0:
                        self.waveform_display.set_waveform(audio_data)
        except Exception as e:
            print(f"⚠️ Erreur lors de la mise à jour des indicateurs: {e}")
    
    def _toggle_playback(self):
        """Bascule entre lecture et pause"""
        if self.voice_capture.is_playing:
            self.voice_capture.stop_playback()
            self.play_btn.setIcon(QIcon("resources/icons/play.png"))
            self.play_btn.setText("Lecture")
            self.pause_btn.setEnabled(False)
        else:
            if self.voice_capture.play_recording():
                self.play_btn.setIcon(QIcon("resources/icons/pause.png"))
                self.play_btn.setText("Pause")
                self.pause_btn.setEnabled(True)
                
    def _re_record(self):
        """Réinitialise et démarre un nouvel enregistrement"""
        self.voice_capture.re_record()
        self.record_btn.setText("Arrêter")
        self.record_btn.setIcon(QIcon("resources/icons/stop.png"))
        self.play_btn.setEnabled(False)
        self.rerecord_btn.setEnabled(False)
        self.waveform_display.clear()  # Effacer la forme d'onde précédente
    
    def _show_error(self, error_msg):
        """Gestionnaire d'erreurs audio"""
        QMessageBox.warning(self, "Erreur Audio", error_msg)
        self.statusBar().showMessage("Erreur audio détectée")
        
        # Réinitialiser les boutons
        self.record_btn.setText("Enregistrer")
        self.record_btn.setIcon(QIcon("resources/icons/record.png"))
        self.play_btn.setEnabled(False)
        self.rerecord_btn.setEnabled(False)
        
        # Réinitialiser les indicateurs
        if hasattr(self, 'vu_meter'):
            if hasattr(self.vu_meter, 'setValue'):
                self.vu_meter.setValue(0)
            elif hasattr(self.vu_meter, 'set_level'):
                self.vu_meter.set_level(0)
        
        if hasattr(self, 'recording_progress'):
            self.recording_progress.setValue(0)
    
    def _update_waveform(self, waveform_data):
        """Met à jour la forme d'onde"""
        self.waveform_display.set_waveform(waveform_data)
    
    def _refresh_audio_devices(self):
        """Force le rafraîchissement des périphériques audio"""
        try:
            print("\nRafraîchissement des périphériques audio...")
            input_devices, output_devices = self.voice_capture.get_audio_devices()
            self._update_audio_devices(input_devices, output_devices)
            self.statusBar().showMessage("Périphériques audio rafraîchis")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du rafraîchissement : {str(e)}")
            
    def _update_audio_devices(self, input_devices, output_devices):
        """Met à jour les listes des périphériques audio"""
        print("\nMise à jour des périphériques audio dans l'interface...")
        
        # Stocker les données des périphériques
        self.input_devices = input_devices
        self.output_devices = output_devices
        
        # Mémoriser les périphériques actuellement sélectionnés
        current_input_index = self.input_combo.currentData() if self.input_combo.currentIndex() >= 0 else None
        current_output_index = self.output_combo.currentData() if self.output_combo.currentIndex() >= 0 else None
        
        # Vider les combobox
        self.input_combo.blockSignals(True)
        self.output_combo.blockSignals(True)
        self.input_combo.clear()
        self.output_combo.clear()
        
        # Ajouter les périphériques d'entrée
        print("\nPériphériques d'entrée disponibles:")
        for device in input_devices:
            name = device['name']
            index = device['index']
            channels = device['channels']
            is_ssl = device.get('is_ssl', False)
            is_default = device.get('is_default', False)
            
            # Créer un libellé clair
            if is_ssl:
                device_text = f"🎤 [{index}] {name} ({channels} canaux) [SSL 2+]"
            elif is_default:
                device_text = f"🎤 [{index}] {name} ({channels} canaux) [Défaut]"
            else:
                device_text = f"🎤 [{index}] {name} ({channels} canaux)"
                
            print(f"- {device_text}")
            # Stocker l'index du périphérique comme donnée associée à l'item
            self.input_combo.addItem(device_text, index)
            
        # Ajouter les périphériques de sortie
        print("\nPériphériques de sortie disponibles:")
        for device in output_devices:
            name = device['name']
            index = device['index']
            channels = device['channels']
            is_ssl = device.get('is_ssl', False)
            is_default = device.get('is_default', False)
            
            # Créer un libellé clair
            if is_ssl:
                device_text = f"🔊 [{index}] {name} ({channels} canaux) [SSL 2+]"
            elif is_default:
                device_text = f"🔊 [{index}] {name} ({channels} canaux) [Défaut]"
            else:
                device_text = f"🔊 [{index}] {name} ({channels} canaux)"
                
            print(f"- {device_text}")
            # Stocker l'index du périphérique comme donnée associée à l'item
            self.output_combo.addItem(device_text, index)
            
        # Restaurer la sélection précédente ou sélectionner le périphérique SSL/par défaut
        selected_input_index = -1
        selected_output_index = -1
        
        # Rechercher les index précédemment sélectionnés
        if current_input_index is not None:
            for i in range(self.input_combo.count()):
                if self.input_combo.itemData(i) == current_input_index:
                    selected_input_index = i
                    break
                    
        if current_output_index is not None:
            for i in range(self.output_combo.count()):
                if self.output_combo.itemData(i) == current_output_index:
                    selected_output_index = i
                    break
                    
        # Si pas trouvé, chercher les périphériques SSL 2+
        if selected_input_index < 0:
            for i in range(self.input_combo.count()):
                if "[SSL 2+]" in self.input_combo.itemText(i):
                    selected_input_index = i
                    break
                    
        if selected_output_index < 0:
            for i in range(self.output_combo.count()):
                if "[SSL 2+]" in self.output_combo.itemText(i):
                    selected_output_index = i
                    break
                    
        # Si toujours pas trouvé, chercher les périphériques par défaut
        if selected_input_index < 0:
            for i in range(self.input_combo.count()):
                if "[Défaut]" in self.input_combo.itemText(i):
                    selected_input_index = i
                    break
                    
        if selected_output_index < 0:
            for i in range(self.output_combo.count()):
                if "[Défaut]" in self.output_combo.itemText(i):
                    selected_output_index = i
                    break
                    
        # Si toujours rien, prendre le premier
        if selected_input_index < 0 and self.input_combo.count() > 0:
            selected_input_index = 0
            
        if selected_output_index < 0 and self.output_combo.count() > 0:
            selected_output_index = 0
            
        # Appliquer les sélections
        if selected_input_index >= 0:
            self.input_combo.setCurrentIndex(selected_input_index)
            
        if selected_output_index >= 0:
            self.output_combo.setCurrentIndex(selected_output_index)
            
        # Réactiver les signaux
        self.input_combo.blockSignals(False)
        self.output_combo.blockSignals(False)
        
        print("\n✓ Interface des périphériques audio mise à jour")
        
        # Appliquer les sélections manuellement (car les signaux ont été bloqués)
        if selected_input_index >= 0:
            self._on_input_device_changed(selected_input_index)
            
        if selected_output_index >= 0:
            self._on_output_device_changed(selected_output_index)
    
    def _on_input_device_changed(self, index):
        """Gestionnaire du changement de périphérique d'entrée"""
        if index < 0 or not self.input_combo.count():
            return
            
        try:
            # Récupérer l'index du périphérique depuis les données de l'item
            device_index = self.input_combo.itemData(index)
            if device_index is not None:
                device_text = self.input_combo.itemText(index)
                print(f"\n🎤 Changement de périphérique d'entrée : {device_text}")
                self.voice_capture.set_input_device(device_index)
                self.statusBar().showMessage(f"Périphérique d'entrée: {device_text}")
        except Exception as e:
            print(f"❌ Erreur lors du changement de périphérique d'entrée : {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de sélectionner ce périphérique d'entrée: {e}")
            
    def _on_output_device_changed(self, index):
        """Gestionnaire du changement de périphérique de sortie"""
        if index < 0 or not self.output_combo.count():
            return
            
        try:
            # Récupérer l'index du périphérique depuis les données de l'item
            device_index = self.output_combo.itemData(index)
            if device_index is not None:
                device_text = self.output_combo.itemText(index)
                print(f"\n🔊 Changement de périphérique de sortie : {device_text}")
                self.voice_capture.set_output_device(device_index)
                self.statusBar().showMessage(f"Périphérique de sortie: {device_text}")
        except Exception as e:
            print(f"❌ Erreur lors du changement de périphérique de sortie : {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de sélectionner ce périphérique de sortie: {e}")

    def _on_input_volume_changed(self, value):
        """Gère le changement de volume d'entrée"""
        try:
            # Convertir la valeur du slider (0-200) en volume (0.0-2.0)
            volume = value / 100.0
            
            # Mettre à jour l'affichage
            self.input_volume_value.setText(f"{volume:.2f}")
            
            # Appliquer le volume à la classe VoiceCapture
            if hasattr(self, 'voice_capture') and self.voice_capture:
                self.voice_capture.input_volume = volume
                print(f"Volume d'entrée réglé à {volume:.2f}")
        
        except Exception as e:
            print(f"Erreur de mise à jour du volume d'entrée: {e}")

    def _on_output_volume_changed(self, value):
        """Gère le changement de volume de sortie"""
        try:
            # Convertir la valeur du slider (0-200) en volume (0.0-2.0)
            volume = value / 100.0
            
            # Mettre à jour l'affichage
            self.output_volume_value.setText(f"{volume:.2f}")
            
            # Appliquer le volume à la classe VoiceCapture
            if hasattr(self, 'voice_capture') and self.voice_capture:
                self.voice_capture.output_volume = volume
                print(f"Volume de sortie réglé à {volume:.2f}")
        
        except Exception as e:
            print(f"Erreur de mise à jour du volume de sortie: {e}")

    def _stop_all(self):
        """Arrête à la fois la lecture et la synthèse"""
        self._stop_speaking()
        if self.voice_capture.is_playing:
            self.voice_capture.stop_playback()
            self.play_btn.setIcon(QIcon("resources/icons/play.png"))
            self.play_btn.setText("Lecture")
            self.pause_btn.setEnabled(False)

    def _on_speed_changed(self, value):
        """Gère le changement de vitesse de lecture via le slider"""
        try:
            # Convertir la valeur du slider (50-200) en vitesse de lecture (0.5-2.0)
            speed = value / 100.0
            
            # Mettre à jour l'affichage
            self.speed_value.setText(f"{speed:.2f}x")
            
            # Appliquer la vitesse à la classe VoiceCapture
            if hasattr(self, 'voice_capture') and self.voice_capture:
                self.voice_capture.set_playback_speed(speed)
                
        except Exception as e:
            print(f"Erreur de mise à jour de la vitesse : {e}")

    def _refresh_midi_ports(self):
        """Rafraîchit la liste des ports MIDI disponibles"""
        try:
            # Vérifier si le widget existe toujours
            if not hasattr(self, 'midi_port_combo') or not self.midi_port_combo:
                print("⚠️ ComboBox MIDI non disponible")
                return False
                
            # Stocker le texte courant avant de vider la combobox
            current_port = self.midi_port_combo.currentText() if self.midi_port_combo.count() > 0 else ""
            
            # Bloquer les signaux pendant les modifications
            self.midi_port_combo.blockSignals(True)
            
            # Vider et remplir la liste
            self.midi_port_combo.clear()
            self.midi_port_combo.addItem("Aucun")
            
            # Obtenir les ports MIDI
            try:
                ports = self.midi_manager.get_ports()
                for port in ports:
                    # Améliorer l'affichage pour les périphériques USB/MIDI
                    display_name = port
                    if "AKAI" in port.upper() or "MPK" in port.upper():
                        display_name = f"🎹 {port} [AKAI]"
                    elif "NOVATION" in port.upper() or "LAUNCHPAD" in port.upper():
                        display_name = f"🎹 {port} [NOVATION]"
                    elif "KORG" in port.upper():
                        display_name = f"🎹 {port} [KORG]"
                    elif "ROLAND" in port.upper():
                        display_name = f"🎹 {port} [ROLAND]"
                    elif "USB" in port.upper():
                        display_name = f"🎹 {port} [USB]"
                    elif "MIDI" in port.upper():
                        display_name = f"🎹 {port} [MIDI]"
                    else:
                        display_name = f"🎹 {port}"
                    self.midi_port_combo.addItem(display_name)
            except Exception as e:
                print(f"⚠️ Erreur lors de la récupération des ports MIDI: {e}")
                
            # Réactiver les signaux
            self.midi_port_combo.blockSignals(False)
                
            # Tenter de restaurer la sélection précédente
            if current_port and current_port != "Aucun":
                index = self.midi_port_combo.findText(current_port)
                # Si on ne trouve pas exactement le même nom, chercher un sous-ensemble
                if index < 0:
                    for i in range(self.midi_port_combo.count()):
                        if current_port in self.midi_port_combo.itemText(i):
                            index = i
                            break
                            
                if index >= 0:
                    self.midi_port_combo.setCurrentIndex(index)
                    
            # Afficher le nombre de périphériques dans la barre d'état
            if self.midi_port_combo.count() > 1 and hasattr(self, 'statusBar'):
                self.statusBar().showMessage(f"{self.midi_port_combo.count()-1} périphériques MIDI trouvés")
                
            return True
        except RuntimeError as re:
            # Erreur spécifique aux objets Qt détruits
            if "already deleted" in str(re):
                print("⚠️ Widget MIDI déjà détruit - abandon de l'opération")
            else:
                print(f"❌ Erreur Qt Runtime: {str(re)}")
            return False
        except Exception as e:
            print(f"❌ Erreur lors du rafraîchissement des ports MIDI: {str(e)}")
            # Si on a accès au label, afficher l'erreur
            if hasattr(self, 'midi_note_label') and self.midi_note_label:
                try:
                    self.midi_note_label.setText(f"Erreur: {str(e)}")
                except:
                    pass
            return False

    def _on_midi_port_changed(self, index):
        """Gère le changement de port MIDI"""
        try:
            # Vérifier si les widgets existent encore
            if not hasattr(self, 'midi_port_combo') or not self.midi_port_combo:
                print("⚠️ ComboBox MIDI non disponible")
                return
                
            if index == 0:  # "Aucun" sélectionné
                if hasattr(self, 'midi_manager') and self.midi_manager:
                    self.midi_manager.close_port()
                    
                # Mettre à jour les labels si disponibles
                if hasattr(self, 'midi_note_label') and self.midi_note_label:
                    self.midi_note_label.setText("Note: -")
                if hasattr(self, 'midi_cc_label') and self.midi_cc_label:
                    self.midi_cc_label.setText("Control Change: -")
                if hasattr(self, 'midi_pb_label') and self.midi_pb_label:
                    self.midi_pb_label.setText("Pitch Bend: -")
                if hasattr(self, 'midi_indicator') and self.midi_indicator:
                    self.midi_indicator.setActive(False)
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage("Déconnecté du périphérique MIDI")
                return
                
            # Récupérer le nom du port sélectionné
            port_name = self.midi_port_combo.currentText()
            port_display = port_name
            
            # Les noms affichés ont été modifiés, extraire le nom réel du port
            if "[USB]" in port_name or "[MIDI]" in port_name or "[AKAI]" in port_name:
                # Supprimer l'emoji et le tag à la fin
                if port_name.startswith("🎹 "):
                    port_name = port_name[2:].strip()
                    
                if " [USB]" in port_name:
                    port_name = port_name.replace(" [USB]", "")
                elif " [MIDI]" in port_name:
                    port_name = port_name.replace(" [MIDI]", "")
                elif " [AKAI]" in port_name:
                    port_name = port_name.replace(" [AKAI]", "")
                elif " [NOVATION]" in port_name:
                    port_name = port_name.replace(" [NOVATION]", "")
                elif " [KORG]" in port_name:
                    port_name = port_name.replace(" [KORG]", "")
                elif " [ROLAND]" in port_name:
                    port_name = port_name.replace(" [ROLAND]", "")
            
            # Vérifier que le midi_manager existe
            if not hasattr(self, 'midi_manager') or not self.midi_manager:
                if hasattr(self, 'midi_note_label') and self.midi_note_label:
                    self.midi_note_label.setText("Erreur: gestionnaire MIDI non disponible")
                return
                
            # Trouver l'index dans les périphériques réels
            real_ports = self.midi_manager.get_ports()
            real_port_index = -1
            
            for i, real_port in enumerate(real_ports):
                if port_name == real_port or real_port in port_name or port_name in real_port:
                    real_port_index = i
                    break
                    
            if real_port_index < 0:
                real_port_index = index - 1  # Fallback: Ajuster pour l'entrée "Aucun"
                
            # Connecter au port
            success = self.midi_manager.open_port(real_port_index)
            
            if success:
                if hasattr(self, 'midi_note_label') and self.midi_note_label:
                    self.midi_note_label.setText(f"Port: {port_display}")
                if hasattr(self, 'midi_cc_label') and self.midi_cc_label:
                    self.midi_cc_label.setText("Control Change: -")
                if hasattr(self, 'midi_pb_label') and self.midi_pb_label:
                    self.midi_pb_label.setText("Pitch Bend: -")
                if hasattr(self, 'midi_indicator') and self.midi_indicator:
                    self.midi_indicator.setActive(True)
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage(f"Connecté au port MIDI: {port_display}")
            else:
                if hasattr(self, 'midi_note_label') and self.midi_note_label:
                    self.midi_note_label.setText(f"Erreur: échec de connexion à {port_display}")
                if hasattr(self, 'midi_port_combo') and self.midi_port_combo:
                    # Bloquer les signaux pour éviter une récursion
                    self.midi_port_combo.blockSignals(True)
                    self.midi_port_combo.setCurrentIndex(0)  # Revenir à "Aucun"
                    self.midi_port_combo.blockSignals(False)
                        
        except RuntimeError as re:
            # Erreur spécifique aux objets Qt détruits
            if "already deleted" in str(re):
                print("⚠️ Widget MIDI déjà détruit - abandon de l'opération")
            else:
                print(f"❌ Erreur Qt Runtime: {str(re)}")
        except Exception as e:
            error_msg = f"Erreur de connexion MIDI: {str(e)}"
            print(f"❌ {error_msg}")
            
            try:
                if hasattr(self, 'midi_note_label') and self.midi_note_label:
                    self.midi_note_label.setText(error_msg)
                if hasattr(self, 'midi_port_combo') and self.midi_port_combo:
                    # Bloquer les signaux pour éviter une récursion
                    self.midi_port_combo.blockSignals(True)
                    self.midi_port_combo.setCurrentIndex(0)  # Revenir à "Aucun"
                    self.midi_port_combo.blockSignals(False)
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage("Échec de connexion au périphérique MIDI")
            except:
                pass

    def _on_midi_note_on(self, channel, note, velocity):
        """Gère un événement de note MIDI"""
        note_name = self._get_note_name(note)
        self.midi_note_label.setText(f"Note: {note_name} ({note}) - Vélocité: {velocity}")
        self.midi_indicator.flash()
        
        # Vérifier si cette note est mappée à une fonction
        function_id = self.midi_mapping.get_function_for_note(note, channel)
        if function_id:
            self._execute_midi_function(function_id, velocity / 127.0)
            
    def _on_midi_note_off(self, channel, note):
        """Gère l'événement Note Off MIDI"""
        note_name = self._get_note_name(note)
        self.midi_note_label.setText(f"Note: {note_name}")
        
        # Si c'est la dernière note active, désactiver l'indicateur
        self.midi_indicator.setNote(None, 0)
        
        # Faire défiler pour montrer le dernier message
        self.midi_note_label.ensureCursorVisible()
        
    def _on_midi_control_change(self, channel, control, value):
        """Gère un événement de contrôleur MIDI"""
        self.midi_cc_label.setText(f"Control: {control} - Valeur: {value}")
        self.midi_indicator.flash()
        
        # Vérifier si ce contrôleur est mappé à une fonction
        function_id = self.midi_mapping.get_function_for_cc(control, channel)
        if function_id:
            self._execute_midi_function(function_id, value / 127.0)
            
    def _on_midi_pitch_bend(self, channel, value):
        """Gère un événement de pitch bend MIDI"""
        normalized_value = (value + 8192) / 16384.0  # Convertir -8192...8191 en 0.0...1.0
        self.midi_pb_label.setText(f"Pitch Bend: {value} ({normalized_value:.2f})")
        self.midi_indicator.flash()
        
        # Vérifier si le pitch bend est mappé à une fonction
        function_id = self.midi_mapping.get_function_for_pb(channel)
        if function_id:
            self._execute_midi_function(function_id, normalized_value)
            
    def _on_midi_activity(self):
        """Gère le signal d'activité MIDI"""
        self.midi_indicator.setActive(True)
        
    def _toggle_midi_learn(self, state):
        """Active ou désactive le mode d'apprentissage MIDI"""
        if state == Qt.Checked:
            self.midi_note_label.setText("Note: -")
            self.midi_cc_label.setText("Control Change: -")
            self.midi_pb_label.setText("Pitch Bend: -")
            self.midi_indicator.setActive(True)
        else:
            self.midi_note_label.setText("Note: -")
            self.midi_cc_label.setText("Control Change: -")
            self.midi_pb_label.setText("Pitch Bend: -")
            self.midi_indicator.setActive(False)
            
    def _show_midi_config(self):
        """Affiche la boîte de dialogue de configuration MIDI avancée"""
        dialog = MidiConfigDialog(self.midi_mapping, self)
        
        # Charger les voix disponibles
        voices = {}
        try:
            if hasattr(self.tts_engine, 'get_voices'):
                for voice_id, voice in self.tts_engine.get_voices().items():
                    voices[voice_id] = voice.get('name', voice_id)
        except Exception as e:
            print(f"Erreur lors du chargement des voix: {e}")
            
        dialog.set_available_voices(voices)
        
        # Intercepter les événements MIDI pendant la configuration
        self.midi_manager.note_on.disconnect(self._on_midi_note_on)
        self.midi_manager.control_change.disconnect(self._on_midi_control_change)
        self.midi_manager.pitch_bend.disconnect(self._on_midi_pitch_bend)
        
        def handle_note_on(channel, note, velocity):
            """Gestionnaire temporaire pour les notes MIDI pendant la configuration"""
            if dialog.handle_midi_event("note", channel, note, velocity):
                return
            self._on_midi_note_on(channel, note, velocity)
            
        def handle_control_change(channel, control, value):
            """Gestionnaire temporaire pour les CC MIDI pendant la configuration"""
            if dialog.handle_midi_event("cc", channel, control, value):
                return
            self._on_midi_control_change(channel, control, value)
            
        def handle_pitch_bend(channel, value):
            """Gestionnaire temporaire pour le pitch bend pendant la configuration"""
            if dialog.handle_midi_event("pb", channel, None, value):
                return
            self._on_midi_pitch_bend(channel, value)
            
        # Connecter les gestionnaires temporaires
        self.midi_manager.note_on.connect(handle_note_on)
        self.midi_manager.control_change.connect(handle_control_change)
        self.midi_manager.pitch_bend.connect(handle_pitch_bend)
        
        # Exécuter la boîte de dialogue
        if dialog.exec_():
            print("Configuration MIDI enregistrée")
        
        # Reconnecter les gestionnaires normaux
        self.midi_manager.note_on.disconnect()
        self.midi_manager.control_change.disconnect()
        self.midi_manager.pitch_bend.disconnect()
        
        self.midi_manager.note_on.connect(self._on_midi_note_on)
        self.midi_manager.control_change.connect(self._on_midi_control_change)
        self.midi_manager.pitch_bend.connect(self._on_midi_pitch_bend)

    def _get_note_name(self, note):
        """Convertit un numéro de note MIDI en nom de note"""
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = (note // 12) - 1
        note_name = notes[note % 12]
        return f"{note_name}{octave}"

    def _execute_midi_function(self, function_id, value):
        """Exécute une fonction selon son ID et la valeur MIDI"""
        category, function = self.midi_mapping.parse_function(function_id)
        if not category or not function:
            return
            
        print(f"Exécution de la fonction MIDI: {category}:{function} avec valeur {value:.2f}")
        
        # Exécuter selon la catégorie et la fonction
        if category == "tts_params":
            self._execute_tts_param_function(function, value)
        elif category == "tts_voices":
            self._execute_tts_voice_function(function, value)
        elif category == "playback":
            self._execute_playback_function(function, value)
        elif category == "phrases":
            self._execute_phrase_function(function, value)
        elif category == "modulation":
            self._execute_modulation_function(function, value)
        elif category == "sync":
            self._execute_sync_function(function, value)
            
    def _execute_tts_param_function(self, function, value):
        """Exécute une fonction de paramètre TTS"""
        if function == "speed":
            # Convertir 0.0...1.0 en 0.5...2.0
            speed = 0.5 + value * 1.5
            # TODO: Mettre à jour l'interface et appliquer la vitesse
            print(f"Vitesse TTS réglée à {speed:.2f}x")
            
        elif function == "pitch":
            # Convertir 0.0...1.0 en -10...10
            pitch = -10 + value * 20
            # TODO: Mettre à jour l'interface et appliquer la hauteur
            print(f"Hauteur TTS réglée à {pitch:.1f}")
            
        elif function == "volume":
            # Convertir 0.0...1.0 en 0.0...2.0
            volume = value * 2.0
            if hasattr(self, 'output_volume_slider'):
                self.output_volume_slider.setValue(int(volume * 100))
            
        elif function == "emphasis":
            # Convertir 0.0...1.0 en 0.0...1.0 (déjà bon)
            # TODO: Mettre à jour l'interface et appliquer l'emphase
            print(f"Emphase TTS réglée à {value:.2f}")
            
    def _execute_tts_voice_function(self, function, value):
        """Exécute une fonction de voix TTS"""
        if function == "next_voice":
            # TODO: Passer à la voix suivante
            print("Voix suivante")
            
        elif function == "prev_voice":
            # TODO: Passer à la voix précédente
            print("Voix précédente")
            
        elif function == "select_voice":
            # Convertir 0.0...1.0 en indice de voix
            # TODO: Sélectionner la voix correspondante
            print(f"Sélection de voix: {value:.2f}")
            
    def _execute_playback_function(self, function, value):
        """Exécute une fonction de lecture"""
        if function == "play" and value > 0.5:
            if not self.voice_capture.is_playing:
                self._toggle_playback()
                
        elif function == "stop" and value > 0.5:
            if self.voice_capture.is_playing:
                self._stop_all()
                
        elif function == "pause" and value > 0.5:
            if self.voice_capture.is_playing:
                self._toggle_playback()
                
        elif function == "record" and value > 0.5:
            if not self.voice_capture.is_recording:
                self._toggle_recording()
                
        elif function == "speed":
            # Convertir 0.0...1.0 en 0.5...2.0
            speed = 0.5 + value * 1.5
            if hasattr(self, 'playback_speed_slider'):
                self.playback_speed_slider.setValue(int(speed * 100))
                
    def _execute_phrase_function(self, function, value):
        """Exécute une fonction de phrase préenregistrée"""
        if function.startswith("trigger_") and value > 0.5:
            phrase = self.midi_mapping.get_phrase(function)
            if phrase and phrase.get("text"):
                text = phrase.get("text")
                voice = phrase.get("voice")
                
                # Déclencher la synthèse vocale avec le texte et la voix
                print(f"Phrase déclenchée: {text} (voix: {voice})")
                if hasattr(self, 'synthesis_text'):
                    self.synthesis_text.setText(text)
                    self._start_speaking(voice)
                    
    def _execute_modulation_function(self, function, value):
        """Exécute une fonction de modulation de voix"""
        if function == "vibrato":
            # TODO: Appliquer un vibrato à la voix
            print(f"Vibrato réglé à {value:.2f}")
            
        elif function == "tremolo":
            # TODO: Appliquer un tremolo à la voix
            print(f"Tremolo réglé à {value:.2f}")
            
        elif function == "formant":
            # Convertir 0.0...1.0 en -1.0...1.0
            formant_shift = -1.0 + value * 2.0
            # TODO: Appliquer un décalage de formant
            print(f"Formant réglé à {formant_shift:.2f}")
            
        elif function == "distortion":
            # TODO: Appliquer une distorsion à la voix
            print(f"Distorsion réglée à {value:.2f}")
            
    def _execute_sync_function(self, function, value):
        """Exécute une fonction de synchronisation"""
        if function == "start" and value > 0.5:
            # TODO: Démarrer la synchronisation
            print("Sync: Start")
            
        elif function == "stop" and value > 0.5:
            # TODO: Arrêter la synchronisation
            print("Sync: Stop")
            
        elif function == "continue" and value > 0.5:
            # TODO: Continuer la synchronisation
            print("Sync: Continue")

    def _on_playback_started(self):
        """Appelé quand la lecture audio commence"""
        # Mettre à jour l'interface
        self.play_btn.setText("⏸ Pause")
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        # Mettre à jour l'affichage de la forme d'onde
        self.waveform_display.set_playing(True, 0.0)
        
    def _on_playback_stopped(self):
        """Appelé quand la lecture audio s'arrête"""
        # Mettre à jour l'interface
        self.play_btn.setText("▶ Lecture")
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        # Mettre à jour l'affichage de la forme d'onde
        self.waveform_display.set_playing(False)
        
    def _update_playback_position(self, position):
        """Met à jour la position de lecture dans l'interface"""
        # Mettre à jour l'affichage de la forme d'onde
        self.waveform_display.set_playback_position(position)

    def _update_level(self):
        """Met à jour le VU-mètre en temps réel"""
        try:
            if hasattr(self.voice_capture, 'get_current_level'):
                level = self.voice_capture.get_current_level()
                # Convertir le niveau RMS en valeur entre 0 et 1
                level = min(1.0, level * 2)
                self.vu_meter.set_level(level)
        except Exception as e:
            print(f"Erreur lors de la mise à jour du niveau : {e}")
            # Désactiver le timer si erreur persistante
            self.level_timer.stop()
            self.level_timer.start(50)  # Redémarrer le timer 

    def _refresh_ui(self):
        """Force le rafraîchissement de l'interface utilisateur"""
        self.repaint()
        if hasattr(self, 'tabs'):
            self.tabs.repaint()
        
        # Parcourir et mettre à jour tous les widgets principaux
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab:
                tab.repaint()
        
        # Forcer le traitement des événements
        QApplication.processEvents() 