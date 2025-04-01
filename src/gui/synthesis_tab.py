"""
Module pour la synthèse vocale et la transformation text-to-speech.

Ce module fournit une interface pour la synthèse vocale à partir de texte,
avec support multilingue, connexion MIDI pour la modulation, et contrôle
des paramètres de la voix synthétisée.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QSlider, QPushButton, QComboBox, QFileDialog,
                              QGroupBox, QSplitter, QProgressBar, QSizePolicy,
                              QTextEdit, QCheckBox, QMessageBox, QListWidget,
                              QListWidgetItem)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QByteArray, QBuffer, QIODevice, QMetaObject, Q_ARG
from PySide6.QtGui import QPainter, QPen, QColor, QLinearGradient, QPainterPath

import os
import sys
import json
import numpy as np
import threading
import torch
from scipy.io import wavfile
import soundfile as sf
import sounddevice as sd
import time

# Importer le gestionnaire de modèles
from core.voice_cloning import model_manager, PlaybackManager


class VoiceModelSelector(QWidget):
    """Widget pour sélectionner et gérer les modèles de voix"""
    
    model_selected = Signal(str)  # Signal émis quand un modèle est sélectionné
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration de l'interface
        self.setup_ui()
        
        # Charger les modèles disponibles
        self.refresh_models()
        
    def setup_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Liste des modèles
        self.model_list = QListWidget()
        self.model_list.setSelectionMode(QListWidget.SingleSelection)
        self.model_list.itemClicked.connect(self._on_model_selected)
        layout.addWidget(self.model_list, 1)  # Stretch factor 1
        
        # Boutons de gestion
        buttons_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Rafraîchir")
        self.refresh_button.clicked.connect(self.refresh_models)
        buttons_layout.addWidget(self.refresh_button)
        
        layout.addLayout(buttons_layout)
        
    def refresh_models(self):
        """Rafraîchit la liste des modèles disponibles"""
        self.model_list.clear()
        
        # Récupérer les modèles installés depuis le gestionnaire
        installed_models = model_manager.get_installed_models()
        
        # Liste pour grouper les modèles
        standard_models = []
        user_voices = []
        
        # Parcourir les modèles installés
        for model_id, model_info in installed_models.items():
            # Nom du modèle
            name = model_info.get("name", model_id)
            
            # Langues supportées
            languages = model_info.get("languages", ["fr"])
            langs_str = ", ".join(languages)
            
            # Type de voix (utilisateur ou standard)
            is_user_voice = model_info.get("user_voice", False)
            
            # Moteur utilisé
            engine = model_info.get("engine", "custom")
            
            # Créer l'item pour ce modèle
            item = QListWidgetItem(f"{name} ({langs_str})")
            item.setData(Qt.UserRole, model_id)  # Stocker l'ID
            item.setData(Qt.UserRole + 1, engine)  # Stocker le moteur
            
            # Tri en fonction du type
            if is_user_voice:
                # Utiliser une couleur différente pour les voix utilisateur
                item.setForeground(QColor(0, 150, 0))  # Vert
                user_voices.append(item)
            else:
                standard_models.append(item)
        
        # Ajouter d'abord les voix utilisateur avec un en-tête
        if user_voices:
            header_item = QListWidgetItem("--- VOIX UTILISATEUR ---")
            header_item.setFlags(Qt.NoItemFlags)
            header_item.setBackground(QColor(230, 230, 230))
            header_item.setForeground(QColor(80, 80, 80))
            self.model_list.addItem(header_item)
            
            for item in user_voices:
                self.model_list.addItem(item)
        
        # Puis ajouter les modèles standard avec un en-tête
        if standard_models:
            header_item = QListWidgetItem("--- MODÈLES STANDARDS ---")
            header_item.setFlags(Qt.NoItemFlags)
            header_item.setBackground(QColor(230, 230, 230))
            header_item.setForeground(QColor(80, 80, 80))
            self.model_list.addItem(header_item)
            
            for item in standard_models:
                self.model_list.addItem(item)
            
        # Modèle par défaut si aucun modèle trouvé
        if self.model_list.count() == 0:
            item = QListWidgetItem("Voix par défaut (fr, en)")
            item.setData(Qt.UserRole, "default")
            self.model_list.addItem(item)
        
        # Sélectionner le premier modèle de voix utilisateur s'il existe, sinon le premier modèle standard
        for i in range(self.model_list.count()):
            item = self.model_list.item(i)
            if item and item.flags() & Qt.ItemIsSelectable:
                self.model_list.setCurrentItem(item)
                self._on_model_selected(item)
                break
            
    def _on_model_selected(self, item):
        """Gère la sélection d'un modèle dans la liste"""
        if not item or not (item.flags() & Qt.ItemIsSelectable):
            return  # Ignorer les en-têtes et autres items non sélectionnables
            
        model_id = item.data(Qt.UserRole)
        if model_id:
            self.model_selected.emit(model_id)
        
    def get_current_model(self):
        """Retourne l'ID du modèle actuellement sélectionné"""
        current_item = self.model_list.currentItem()
        if current_item and (current_item.flags() & Qt.ItemIsSelectable):
            return current_item.data(Qt.UserRole)
        return "default"
        
    def select_model(self, model_id):
        """Sélectionne un modèle dans la liste par son ID"""
        for i in range(self.model_list.count()):
            item = self.model_list.item(i)
            if item and (item.flags() & Qt.ItemIsSelectable) and item.data(Qt.UserRole) == model_id:
                self.model_list.setCurrentItem(item)
                self._on_model_selected(item)
                return True
        return False


class SynthesisControls(QWidget):
    """Widget pour contrôler les paramètres de synthèse vocale"""
    
    parameters_changed = Signal(dict)  # Signal émis quand les paramètres changent
    engine_selected = Signal(str)      # Signal émis quand le moteur est changé
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Paramètres de synthèse
        self.parameters = {
            "speed": 1.0,       # Vitesse de parole (0.5 - 2.0)
            "pitch": 0.0,       # Hauteur tonale (-12 - +12 demi-tons)
            "formant": 0.0,     # Formant (-50 - +50 %)
            "emotion": "neutral", # Émotion (neutre, joyeux, triste, etc.)
            "engine_type": "auto" # Type de moteur à utiliser (auto, midi, fast)
        }
        
        # Configuration de l'interface
        self.setup_ui()
        
    def setup_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Groupe des paramètres de base
        basic_group = QGroupBox("Paramètres de base")
        basic_layout = QVBoxLayout(basic_group)
        
        # Contrôle de la vitesse
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Vitesse:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(25)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("1.0x")
        speed_layout.addWidget(self.speed_label)
        basic_layout.addLayout(speed_layout)
        
        # Contrôle de la hauteur
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(QLabel("Hauteur:"))
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)
        self.pitch_slider.setTickInterval(2)
        pitch_layout.addWidget(self.pitch_slider)
        self.pitch_label = QLabel("0")
        pitch_layout.addWidget(self.pitch_label)
        basic_layout.addLayout(pitch_layout)
        
        # Contrôle du formant
        formant_layout = QHBoxLayout()
        formant_layout.addWidget(QLabel("Formant:"))
        self.formant_slider = QSlider(Qt.Horizontal)
        self.formant_slider.setRange(-50, 50)
        self.formant_slider.setValue(0)
        self.formant_slider.setTickPosition(QSlider.TicksBelow)
        self.formant_slider.setTickInterval(10)
        formant_layout.addWidget(self.formant_slider)
        self.formant_label = QLabel("0%")
        formant_layout.addWidget(self.formant_label)
        basic_layout.addLayout(formant_layout)
        
        layout.addWidget(basic_group)
        
        # Groupe des options avancées
        advanced_group = QGroupBox("Options avancées")
        advanced_layout = QVBoxLayout(advanced_group)
        
        # Sélection de l'émotion
        emotion_layout = QHBoxLayout()
        emotion_layout.addWidget(QLabel("Émotion:"))
        self.emotion_combo = QComboBox()
        self.emotion_combo.addItem("Neutre", "neutral")
        self.emotion_combo.addItem("Joyeux", "happy")
        self.emotion_combo.addItem("Triste", "sad")
        self.emotion_combo.addItem("En colère", "angry")
        self.emotion_combo.addItem("Peur", "fear")
        self.emotion_combo.addItem("Surprise", "surprise")
        emotion_layout.addWidget(self.emotion_combo)
        advanced_layout.addLayout(emotion_layout)
        
        # Sélection du moteur TTS
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("Moteur:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("Automatique", "auto")
        self.engine_combo.addItem("OpenVoice V2", "openvoice_v2")
        self.engine_combo.addItem("Bark", "bark")
        self.engine_combo.addItem("Coqui TTS", "coqui_tts")
        self.engine_combo.addItem("gTTS", "gtts")
        engine_layout.addWidget(self.engine_combo)
        advanced_layout.addLayout(engine_layout)
        
        # Mode rapide ou MIDI (boutons radio)
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        
        self.mode_fast_button = QPushButton("Mode Rapide")
        self.mode_fast_button.setCheckable(True)
        self.mode_fast_button.setChecked(True)
        self.mode_fast_button.clicked.connect(lambda: self._set_mode("fast"))
        
        self.mode_midi_button = QPushButton("Mode MIDI")
        self.mode_midi_button.setCheckable(True)
        self.mode_midi_button.clicked.connect(lambda: self._set_mode("midi"))
        
        mode_layout.addWidget(self.mode_fast_button)
        mode_layout.addWidget(self.mode_midi_button)
        
        advanced_layout.addLayout(mode_layout)
        
        layout.addWidget(advanced_group)
        
        # Connecter les signaux
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        self.pitch_slider.valueChanged.connect(self._on_pitch_changed)
        self.formant_slider.valueChanged.connect(self._on_formant_changed)
        self.emotion_combo.currentIndexChanged.connect(self._on_emotion_changed)
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        
        # Mise à jour initiale
        self._on_speed_changed(self.speed_slider.value())
        self._on_pitch_changed(self.pitch_slider.value())
        self._on_formant_changed(self.formant_slider.value())
        
    def _set_mode(self, mode):
        """Définit le mode d'utilisation (rapide ou MIDI)"""
        if mode == "fast":
            self.mode_fast_button.setChecked(True)
            self.mode_midi_button.setChecked(False)
            self.parameters["engine_type"] = "fast"
        elif mode == "midi":
            self.mode_fast_button.setChecked(False)
            self.mode_midi_button.setChecked(True)
            self.parameters["engine_type"] = "midi"
        
        self.parameters_changed.emit(self.parameters)
        
    def _on_speed_changed(self, value):
        """Gère le changement de vitesse"""
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.1f}x")
        self.parameters["speed"] = speed
        self.parameters_changed.emit(self.parameters)
        
    def _on_pitch_changed(self, value):
        """Gère le changement de hauteur"""
        self.pitch_label.setText(f"{value}")
        self.parameters["pitch"] = value
        self.parameters_changed.emit(self.parameters)
        
    def _on_formant_changed(self, value):
        """Gère le changement de formant"""
        self.formant_label.setText(f"{value}%")
        self.parameters["formant"] = value
        self.parameters_changed.emit(self.parameters)
        
    def _on_emotion_changed(self, index):
        """Gère le changement d'émotion"""
        self.parameters["emotion"] = self.emotion_combo.currentData()
        self.parameters_changed.emit(self.parameters)
        
    def _on_engine_changed(self, index):
        """Gère le changement de moteur"""
        engine = self.engine_combo.currentData()
        self.parameters["engine_type"] = engine
        self.parameters_changed.emit(self.parameters)
        self.engine_selected.emit(engine)
        
    def update_from_midi(self, modulation_data):
        """Met à jour les contrôles à partir des données de modulation MIDI"""
        # Mettre à jour la vitesse si présente
        if "speed" in modulation_data:
            speed = modulation_data["speed"]
            self.speed_slider.setValue(int(speed * 100))
            
        # Mettre à jour la hauteur si présente
        if "pitch" in modulation_data:
            pitch = modulation_data["pitch"]
            self.pitch_slider.setValue(int(pitch))
            
        # Mettre à jour le formant si présent
        if "formant" in modulation_data:
            formant = modulation_data["formant"]
            self.formant_slider.setValue(int(formant))
            
        # Mettre à jour le mode si le midi est activé
        if modulation_data.get("midi_active", False):
            self._set_mode("midi")


class LanguageSelector(QWidget):
    """Widget pour sélectionner la langue de synthèse"""
    
    language_changed = Signal(str)  # Signal émis quand la langue change
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration de base
        self.languages = {
            "fr": "Français",
            "en": "Anglais",
            "es": "Espagnol",
            "de": "Allemand",
            "it": "Italien",
            "pt": "Portugais",
            "nl": "Néerlandais",
            "ru": "Russe",
            "ja": "Japonais",
            "zh": "Chinois",
            "ar": "Arabe"
        }
        
        # Configuration de l'interface
        self.setup_ui()
        
    def setup_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(QLabel("Langue:"))
        
        self.language_combo = QComboBox()
        layout.addWidget(self.language_combo)
        
        # Langue par défaut: français
        self.update_languages(["fr", "en"])
        
        # Connecter le signal
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        
    def update_languages(self, supported_languages):
        """Met à jour la liste des langues disponibles"""
        # Sauvegarder la langue actuelle
        current_language = self.get_current_language()
        
        # Effacer la liste
        self.language_combo.clear()
        
        # Ajouter les langues supportées
        for lang_code in supported_languages:
            if lang_code in self.languages:
                self.language_combo.addItem(self.languages[lang_code], lang_code)
                
        # Restaurer la langue si possible
        if current_language in supported_languages:
            self.set_language(current_language)
        elif supported_languages:
            self.set_language(supported_languages[0])
            
    def set_language(self, language_code):
        """Définit la langue actuelle"""
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == language_code:
                self.language_combo.setCurrentIndex(i)
                break
                
    def _on_language_changed(self, index):
        """Gère le changement de langue"""
        if index >= 0:
            language_code = self.language_combo.itemData(index)
            self.language_changed.emit(language_code)
        
    def get_current_language(self):
        """Retourne le code de la langue actuellement sélectionnée"""
        if self.language_combo.count() > 0:
            return self.language_combo.currentData()
        return None


class TextToSpeechSynthesizer(QWidget):
    """Widget principal pour la synthèse text-to-speech"""
    
    synthesis_started = Signal()  # Signal émis quand la synthèse démarre
    synthesis_finished = Signal(np.ndarray, int)  # Signal émis quand la synthèse est terminée (données, taux)
    synthesis_progress = Signal(int, str)  # Signal émis pour mettre à jour la progression (valeur, message)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # État du widget
        self.synthesized_audio = None
        self.sample_rate = 0
        self.playing = False
        self.play_timer = None
        self.selected_model = "default"
        self.last_text = ""
        self.last_params = {}
        self.last_language = ""
        
        # Variables temporaires pour le transfert de données entre threads
        self._temp_audio_data = None
        self._temp_sample_rate = 0
        self._temp_error = None
        
        # Configuration de l'interface
        self.setup_ui()
        
    def setup_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Splitter principal
        self.main_splitter = QSplitter(Qt.Vertical)
        
        # Panneau supérieur (sélection de modèle/langue)
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        
        # Sélection de modèle
        model_group = QGroupBox("Modèle de voix")
        model_layout = QVBoxLayout(model_group)
        self.model_selector = VoiceModelSelector()
        self.model_selector.model_selected.connect(self._on_model_selected)
        model_layout.addWidget(self.model_selector)
        top_layout.addWidget(model_group)
        
        # Sélection de langue et paramètres
        lang_controls_group = QGroupBox("Langue et contrôles")
        lang_controls_layout = QVBoxLayout(lang_controls_group)
        
        # Sélection de langue
        self.language_selector = LanguageSelector()
        self.language_selector.language_changed.connect(self._on_language_changed)
        lang_controls_layout.addWidget(self.language_selector)
        
        # Option de traduction automatique
        self.auto_translate_cb = QCheckBox("Traduction automatique")
        self.auto_translate_cb.setToolTip("Traduire automatiquement le texte quand la langue change")
        lang_controls_layout.addWidget(self.auto_translate_cb)
        
        top_layout.addWidget(lang_controls_group)
        
        # Ajouter le panneau supérieur au splitter
        self.main_splitter.addWidget(top_panel)
        
        # Panneau central (texte et paramètres)
        middle_panel = QWidget()
        middle_layout = QHBoxLayout(middle_panel)
        
        # Zone de texte
        text_group = QGroupBox("Texte à synthétiser")
        text_layout = QVBoxLayout(text_group)
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Entrez le texte à synthétiser...")
        text_layout.addWidget(self.text_edit)
        
        # Boutons pour le texte
        text_buttons_layout = QHBoxLayout()
        self.clear_button = QPushButton("Effacer")
        self.clear_button.clicked.connect(self.text_edit.clear)
        text_buttons_layout.addWidget(self.clear_button)
        
        self.translate_button = QPushButton("Traduire")
        self.translate_button.clicked.connect(self._translate_text)
        text_buttons_layout.addWidget(self.translate_button)
        
        text_layout.addLayout(text_buttons_layout)
        middle_layout.addWidget(text_group)
        
        # Contrôles de synthèse
        self.synthesis_controls = SynthesisControls()
        self.synthesis_controls.parameters_changed.connect(self._on_parameters_changed)
        self.synthesis_controls.engine_selected.connect(lambda engine: self._set_engine(engine))
        middle_layout.addWidget(self.synthesis_controls)
        
        # Ajouter le panneau central au splitter
        self.main_splitter.addWidget(middle_panel)
        
        # Panneau inférieur (commandes de synthèse et contrôles de lecture)
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        
        # Boutons de synthèse et de lecture
        buttons_layout = QHBoxLayout()
        
        self.synthesize_button = QPushButton("Synthétiser")
        self.synthesize_button.setStyleSheet("font-weight: bold;")
        self.synthesize_button.clicked.connect(self.synthesize)
        buttons_layout.addWidget(self.synthesize_button)
        
        self.resynthesis_button = QPushButton("Resynthétiser")
        self.resynthesis_button.setEnabled(False)
        self.resynthesis_button.clicked.connect(self.resynthesis)
        buttons_layout.addWidget(self.resynthesis_button)
        
        self.play_button = QPushButton("Lecture")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_audio)
        buttons_layout.addWidget(self.play_button)
        
        self.save_button = QPushButton("Sauvegarder")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_audio)
        buttons_layout.addWidget(self.save_button)
        
        bottom_layout.addLayout(buttons_layout)
        
        # Barre de progression et message
        progress_layout = QVBoxLayout()
        
        self.progress_label = QLabel("Prêt")
        self.progress_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        bottom_layout.addLayout(progress_layout)
        
        # Ajouter le panneau inférieur au splitter
        self.main_splitter.addWidget(bottom_panel)
        
        # Ajouter le splitter au layout principal
        layout.addWidget(self.main_splitter)
        
        # Configurer la proportion du splitter
        self.main_splitter.setSizes([100, 300, 100])
        
        # Timer pour vérifier l'état de la lecture
        self.playback_timer = QTimer()
        self.playback_timer.setInterval(100)
        self.playback_timer.timeout.connect(self._check_playback_status)
        
        # Connecter les signaux de progression
        self.synthesis_progress.connect(self._update_synthesis_progress)
        
    def _update_synthesis_progress(self, value, message):
        """Met à jour l'affichage de la progression de la synthèse"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        
    def _on_model_selected(self, model_id):
        """Gère la sélection d'un modèle de voix"""
        self.selected_model = model_id
        
        # Récupérer les informations sur le modèle
        model_info = model_manager.get_model_info(model_id)
        if model_info:
            # Mettre à jour les langues supportées
            languages = model_info.get("languages", ["fr"])
            self.language_selector.update_languages(languages)
            
            # Si le modèle a un moteur spécifique, le suggérer
            engine = model_info.get("engine", "auto")
            if engine and engine != "auto":
                engine_index = self.synthesis_controls.engine_combo.findData(engine)
                if engine_index >= 0:
                    self.synthesis_controls.engine_combo.setCurrentIndex(engine_index)
            
            # Si c'est une voix utilisateur, suggérer le mode MIDI
            if model_info.get("user_voice", False):
                self.synthesis_controls._set_mode("midi")
        
    def _on_language_changed(self, language_code):
        """Gère le changement de langue"""
        # Si la traduction automatique est activée, traduire le texte
        if self.auto_translate_cb.isChecked():
            self._translate_text()
            
    def _translate_text(self):
        """Traduit le texte vers la langue sélectionnée"""
        try:
            # Récupérer le texte actuel
            text = self.text_edit.toPlainText()
            if not text:
                return
                
            # Récupérer la langue cible
            target_lang = self.language_selector.get_current_language()
            if not target_lang:
                return
                
            # Utiliser googletrans pour la traduction
            try:
                from googletrans import Translator
                translator = Translator()
                
                # Mise à jour de l'interface
                self.translate_button.setEnabled(False)
                self.translate_button.setText("Traduction en cours...")
                
                # Fonction pour effectuer la traduction dans un thread
                def do_translation():
                    try:
                        # Traduire le texte
                        translated = translator.translate(text, dest=target_lang[:2])
                        
                        # Mettre à jour l'interface dans le thread principal
                        def update_ui():
                            self.text_edit.setPlainText(translated.text)
                            self.translate_button.setEnabled(True)
                            self.translate_button.setText("Traduire")
                            
                        # Utiliser invokeMethod pour mettre à jour l'UI depuis un thread
                        QMetaObject.invokeMethod(self, "update_ui", Qt.QueuedConnection)
                        
                    except Exception as e:
                        # En cas d'erreur, restaurer l'interface
                        def report_error():
                            self.translate_button.setEnabled(True)
                            self.translate_button.setText("Traduire")
                            QMessageBox.warning(self, "Erreur de traduction", str(e))
                            
                        QMetaObject.invokeMethod(self, "report_error", Qt.QueuedConnection)
                
                # Lancer la traduction dans un thread
                translation_thread = threading.Thread(target=do_translation)
                translation_thread.daemon = True
                translation_thread.start()
                
            except ImportError:
                QMessageBox.warning(self, "Module manquant", 
                                  "Le module 'googletrans' est nécessaire pour la traduction.\n"
                                  "Installez-le avec: pip install googletrans==4.0.0-rc1")
                
        except Exception as e:
            QMessageBox.warning(self, "Erreur de traduction", str(e))
            
    def _set_engine(self, engine_type):
        """Définit le type de moteur sans déclencher la synthèse"""
        # Mettre à jour le combobox du moteur
        engine_index = self.synthesis_controls.engine_combo.findData(engine_type)
        if engine_index >= 0:
            self.synthesis_controls.engine_combo.setCurrentIndex(engine_index)
        
        # Mettre à jour les boutons de mode
        if engine_type == "fast":
            self.synthesis_controls._set_mode("fast")
        elif engine_type == "midi":
            self.synthesis_controls._set_mode("midi")
            
    def synthesize(self):
        """Synthétise le texte en utilisant le modèle et les paramètres actuels"""
        # Vérifier que nous avons du texte à synthétiser
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Texte manquant", "Veuillez entrer du texte à synthétiser.")
            return
            
        # Récupérer les paramètres
        model_id = self.selected_model
        language = self.language_selector.get_current_language()
        engine_type = self.synthesis_controls.parameters["engine_type"]
        
        # Stocker les paramètres pour une resynthèse éventuelle
        self.last_text = text
        self.last_language = language
        self.last_params = self.synthesis_controls.parameters.copy()
        
        # Vérifier si un modèle est sélectionné
        if not model_id or model_id == "default":
            # Aucun modèle sélectionné, utiliser le moteur de base
            use_engine = engine_type
            model_id = None
        else:
            # Modèle sélectionné, vérifier s'il s'agit d'une voix utilisateur
            model_info = model_manager.get_model_info(model_id)
            is_user_voice = model_info.get("user_voice", False)
            
            # Si c'est une voix utilisateur, utiliser le moteur spécifié
            if is_user_voice:
                use_engine = model_info.get("engine", "openvoice_v2")
            else:
                # Sinon, utiliser le moteur sélectionné
                use_engine = engine_type
        
        # Désactiver les boutons pendant la synthèse
        self.synthesize_button.setEnabled(False)
        self.resynthesis_button.setEnabled(False)
        self.play_button.setEnabled(False)
        self.save_button.setEnabled(False)
        
        # Réinitialiser l'audio précédent
        self.synthesized_audio = None
        self.sample_rate = 0
        
        # Afficher la barre de progression
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Préparation de la synthèse...")
        
        # Paramètres pour la synthèse
        params = self.synthesis_controls.parameters.copy()
        params["engine_type"] = use_engine
        
        # Méthode slot pour mettre à jour l'UI une fois la synthèse terminée
        @Slot(np.ndarray, int)
        def synthesis_completed(audio_data, sample_rate):
            # Stocker les résultats globalement pour qu'ils soient accessibles
            self.synthesized_audio = audio_data
            self.sample_rate = sample_rate
            
            # Cacher la barre de progression après un délai
            QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
            
            # Réactiver les boutons
            self.synthesize_button.setEnabled(True)
            self.resynthesis_button.setEnabled(True)
            self.play_button.setEnabled(True)
            self.save_button.setEnabled(True)
            
            # Lecture automatique de l'audio de façon directe
            # pour éviter les problèmes de thread Qt
            if PlaybackManager.play_audio(audio_data, sample_rate):
                self.playing = True
                self.play_button.setText("Arrêter")
                self.progress_label.setText("Lecture en cours...")
                self.playback_timer.start()
            
            # Signal indiquant que la synthèse est terminée
            self.synthesis_finished.emit(audio_data, sample_rate)
        
        # Méthode slot pour afficher les erreurs
        @Slot(str)
        def show_error(error_message):
            QMessageBox.critical(self, "Erreur de synthèse", 
                                f"Erreur lors de la synthèse vocale:\n{error_message}")
            self.progress_bar.setVisible(False)
            self.progress_label.setText("Erreur de synthèse")
            self.synthesize_button.setEnabled(True)
            
        # Fonction pour exécuter la synthèse dans un thread séparé
        def synthesis_thread_func():
            try:
                # Signal indiquant que la synthèse a commencé
                self.synthesis_started.emit()
                
                # Mettre à jour la progression dans le thread principal
                def emit_progress(value, message):
                    self.synthesis_progress.emit(value, message)
                
                # Mise à jour initiale de la progression
                emit_progress(5, "Initialisation du moteur de synthèse...")
                
                # Progression pour différentes étapes de synthèse
                emit_progress(10, "Traitement du texte...")
                time.sleep(0.1)  # Pour permettre la mise à jour de l'UI
                
                # Préparation du modèle
                emit_progress(20, "Préparation du modèle vocal...")
                time.sleep(0.1)  # Pour permettre la mise à jour de l'UI
                
                # Synthèse du texte
                emit_progress(30, "Synthèse vocale en cours...")
                
                # Callback de progression pour le processus de synthèse
                def progress_callback(progress, message):
                    # Convertir la progression de 0-1 à 30-80
                    value = 30 + int(progress * 50)
                    emit_progress(value, message)
                
                # Ajouter le callback aux paramètres
                params["progress_callback"] = progress_callback
                
                # Synthétiser le texte
                audio_data, sample_rate = model_manager.synthesize(
                    text, model_id, language, params
                )
                
                emit_progress(80, "Finalisation de l'audio...")
                
                # Post-traitement de l'audio
                emit_progress(90, "Post-traitement de l'audio...")
                time.sleep(0.1)  # Pour permettre la mise à jour de l'UI
                
                # Mise à jour finale
                emit_progress(100, "Synthèse terminée")
                
                # Stocker les résultats dans des variables pour les récupérer
                # dans le thread principal
                self._temp_audio_data = audio_data
                self._temp_sample_rate = sample_rate
                
                # Utiliser un signal simple sans arguments complexes
                QMetaObject.invokeMethod(
                    self,
                    "handle_synthesis_complete_internal",
                    Qt.QueuedConnection
                )
                
            except Exception as e:
                # Stocker le message d'erreur
                self._temp_error = str(e)
                
                # En cas d'erreur, envoyer un signal pour afficher un message
                QMetaObject.invokeMethod(
                    self,
                    "handle_synthesis_error_internal",
                    Qt.QueuedConnection
                )
        
        # Lancer la synthèse dans un thread
        synthesis_thread = threading.Thread(target=synthesis_thread_func)
        synthesis_thread.daemon = True
        synthesis_thread.start()

    @Slot()
    def handle_synthesis_complete_internal(self):
        """Méthode appelée en interne pour gérer la fin de synthèse"""
        # Récupérer les résultats temporaires
        audio_data = self._temp_audio_data
        sample_rate = self._temp_sample_rate
        
        # Effacer les variables temporaires
        self._temp_audio_data = None
        self._temp_sample_rate = None
        
        # Stocker les résultats
        self.synthesized_audio = audio_data
        self.sample_rate = sample_rate
        
        # Cacher la barre de progression après un délai
        QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
        
        # Réactiver les boutons
        self.synthesize_button.setEnabled(True)
        self.resynthesis_button.setEnabled(True)
        self.play_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
        # Lecture automatique de l'audio de façon directe
        # pour éviter les problèmes de thread Qt
        if PlaybackManager.play_audio(audio_data, sample_rate):
            self.playing = True
            self.play_button.setText("Arrêter")
            self.progress_label.setText("Lecture en cours...")
            self.playback_timer.start()
        
        # Signal indiquant que la synthèse est terminée
        self.synthesis_finished.emit(audio_data, sample_rate)

    @Slot()
    def handle_synthesis_error_internal(self):
        """Méthode appelée en interne en cas d'erreur de synthèse"""
        # Récupérer le message d'erreur
        error_message = self._temp_error
        
        # Effacer la variable temporaire
        self._temp_error = None
        
        # Afficher l'erreur
        QMessageBox.critical(self, "Erreur de synthèse", 
                            f"Erreur lors de la synthèse vocale:\n{error_message}")
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Erreur de synthèse")
        self.synthesize_button.setEnabled(True)
        
    def resynthesis(self):
        """Resynthétise le dernier texte avec les mêmes paramètres"""
        if not self.last_text:
            QMessageBox.warning(self, "Aucun texte précédent", "Aucun texte n'a été synthétisé précédemment.")
            return
            
        # Restaurer les paramètres
        self.text_edit.setPlainText(self.last_text)
        
        # Déclencher la synthèse
        self.synthesize()
        
    def play_audio(self):
        """Joue l'audio synthétisé"""
        if self.synthesized_audio is None:
            self.progress_label.setText("Aucun audio disponible")
            return
            
        if self.sample_rate == 0:
            self.progress_label.setText("Taux d'échantillonnage invalide")
            return
            
        # Si déjà en cours de lecture, arrêter
        if self.playing:
            try:
                PlaybackManager.stop_audio()
                self.playing = False
                self.play_button.setText("Lecture")
                if self.playback_timer.isActive():
                    self.playback_timer.stop()
                return
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Erreur lors de l'arrêt de la lecture: {str(e)}")
                return
                
        try:
            # Lancer la lecture via le gestionnaire de lecture
            success = PlaybackManager.play_audio(self.synthesized_audio, self.sample_rate)
            
            if success:
                self.playing = True
                self.play_button.setText("Arrêter")
                self.progress_label.setText("Lecture en cours...")
                
                # Démarrer le timer pour vérifier l'état de la lecture
                self.playback_timer.start()
            else:
                self.progress_label.setText("Échec de la lecture")
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur de lecture", 
                               f"Erreur lors de la lecture de l'audio:\n{str(e)}")
            self.progress_label.setText(f"Erreur: {str(e)}")
            
    @Slot()  
    def update_ui(self):
        """Met à jour l'interface utilisateur après la lecture"""
        self.play_button.setText("Lecture")
        self.progress_label.setText("Lecture terminée")
        if self.playback_timer.isActive():
            self.playback_timer.stop()
            
    def _check_playback_status(self):
        """Vérifie si la lecture est terminée"""
        if not self.playing:
            self.playback_timer.stop()
            self.play_button.setText("Lecture")
            self.progress_label.setText("Prêt")
            return
            
        # Vérifier si la lecture est toujours en cours
        try:
            # Vérifier l'état de lecture via le gestionnaire
            if not PlaybackManager.is_playing():
                self.playing = False
                # Mettre à jour l'interface dans le thread principal
                QMetaObject.invokeMethod(self, "update_ui", Qt.QueuedConnection)
        except Exception:
            # En cas d'erreur, considérer que la lecture est terminée
            self.playing = False
            # Mettre à jour l'interface dans le thread principal
            QMetaObject.invokeMethod(self, "update_ui", Qt.QueuedConnection)
    
    def save_audio(self):
        """Sauvegarde l'audio synthétisé dans un fichier"""
        if self.synthesized_audio is None or self.sample_rate == 0:
            QMessageBox.warning(self, "Avertissement", "Aucun audio synthétisé à sauvegarder")
            return
            
        # Demander le nom du fichier
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Sauvegarder l'audio", 
            "synthese_vocale.wav",
            "Fichiers WAV (*.wav);;Fichiers MP3 (*.mp3);;Fichiers FLAC (*.flac)"
        )
        
        if not file_path:
            return
            
        try:
            # Vérifier l'extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            if ext == '.wav':
                # Enregistrer en WAV
                wavfile.write(file_path, self.sample_rate, self.synthesized_audio)
            elif ext in ['.mp3', '.flac']:
                # Pour MP3 et FLAC, utiliser soundfile
                sf.write(file_path, self.synthesized_audio, self.sample_rate)
            else:
                # Ajouter l'extension .wav par défaut
                file_path += '.wav'
                wavfile.write(file_path, self.sample_rate, self.synthesized_audio)
                
            QMessageBox.information(self, "Sauvegarde réussie", 
                                  f"Audio sauvegardé avec succès:\n{file_path}")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Erreur de sauvegarde", 
                               f"Erreur lors de la sauvegarde de l'audio:\n{str(e)}")
    
    def handle_midi_modulation(self, modulation_data):
        """Gère les données de modulation MIDI"""
        self.synthesis_controls.update_from_midi(modulation_data)

    def _on_parameters_changed(self, parameters):
        """Gère les changements de paramètres"""
        pass


class SynthesisTab(QWidget):
    """Onglet principal pour la synthèse vocale"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration de l'interface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Titre
        title_label = QLabel("Synthèse Vocale")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Widget de synthèse
        self.synthesizer = TextToSpeechSynthesizer()
        layout.addWidget(self.synthesizer)
        
    def handle_midi_modulation(self, modulation_data):
        """Transmet les données de modulation MIDI au synthétiseur"""
        self.synthesizer.handle_midi_modulation(modulation_data)
        
    def set_pitch(self, value):
        """Définit la hauteur de la voix"""
        self.synthesizer.synthesis_controls.pitch_slider.setValue(value)
        
    def set_speed(self, value):
        """Définit la vitesse de la voix"""
        self.synthesizer.synthesis_controls.speed_slider.setValue(int(value * 100))
        
    def set_volume(self, value):
        """Définit le volume de la voix (non implémenté pour l'instant)"""
        pass 