"""
Module for voice synthesis and text-to-speech transformation.

This module provides an interface for voice synthesis from text,
with multilingual support, MIDI connection for modulation, and control
of synthesized voice parameters.
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

# Import model manager
from core.voice_cloning import model_manager, PlaybackManager


class VoiceModelSelector(QWidget):
    """Widget for selecting and managing voice models"""
    
    model_selected = Signal(str)  # Signal emitted when a model is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI configuration
        self.setup_ui()
        
        # Load available models
        self.refresh_models()
        
    def setup_ui(self):
        """Initialize user interface"""
        layout = QVBoxLayout(self)
        
        # Model list
        self.model_list = QListWidget()
        self.model_list.setSelectionMode(QListWidget.SingleSelection)
        self.model_list.itemClicked.connect(self._on_model_selected)
        layout.addWidget(self.model_list, 1)  # Stretch factor 1
        
        # Management buttons
        buttons_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_models)
        buttons_layout.addWidget(self.refresh_button)
        
        layout.addLayout(buttons_layout)
        
    def refresh_models(self):
        """Refresh list of available models"""
        self.model_list.clear()
        
        # Get installed models from manager
        installed_models = model_manager.get_installed_models()
        
        # Lists to group models
        standard_models = []
        user_voices = []
        
        # Go through installed models
        for model_id, model_info in installed_models.items():
            # Model name
            name = model_info.get("name", model_id)
            
            # Supported languages
            languages = model_info.get("languages", ["en"])
            langs_str = ", ".join(languages)
            
            # Voice type (user or standard)
            is_user_voice = model_info.get("user_voice", False)
            
            # Engine used
            engine = model_info.get("engine", "custom")
            
            # Create item for this model
            item = QListWidgetItem(f"{name} ({langs_str})")
            item.setData(Qt.UserRole, model_id)  # Store ID
            item.setData(Qt.UserRole + 1, engine)  # Store engine
            
            # Sort by type
            if is_user_voice:
                # Use a different color for user voices
                item.setForeground(QColor(0, 150, 0))  # Green
                user_voices.append(item)
            else:
                standard_models.append(item)
        
        # Add user voices first with a header
        if user_voices:
            header_item = QListWidgetItem("--- USER VOICES ---")
            header_item.setFlags(Qt.NoItemFlags)
            header_item.setBackground(QColor(230, 230, 230))
            header_item.setForeground(QColor(80, 80, 80))
            self.model_list.addItem(header_item)
            
            for item in user_voices:
                self.model_list.addItem(item)
        
        # Then add standard models with a header
        if standard_models:
            header_item = QListWidgetItem("--- STANDARD MODELS ---")
            header_item.setFlags(Qt.NoItemFlags)
            header_item.setBackground(QColor(230, 230, 230))
            header_item.setForeground(QColor(80, 80, 80))
            self.model_list.addItem(header_item)
            
            for item in standard_models:
                self.model_list.addItem(item)
            
        # Default model if no models found
        if self.model_list.count() == 0:
            item = QListWidgetItem("Default voice (en, fr)")
            item.setData(Qt.UserRole, "default")
            self.model_list.addItem(item)
        
        # Select first user voice if it exists, otherwise first standard model
        for i in range(self.model_list.count()):
            item = self.model_list.item(i)
            if item and item.flags() & Qt.ItemIsSelectable:
                self.model_list.setCurrentItem(item)
                self._on_model_selected(item)
                break
            
    def _on_model_selected(self, item):
        """Handle model selection from the list"""
        if not item or not (item.flags() & Qt.ItemIsSelectable):
            return  # Ignore headers and other non-selectable items
            
        model_id = item.data(Qt.UserRole)
        if model_id:
            self.model_selected.emit(model_id)
        
    def get_current_model(self):
        """Return the ID of the currently selected model"""
        current_item = self.model_list.currentItem()
        if current_item and (current_item.flags() & Qt.ItemIsSelectable):
            return current_item.data(Qt.UserRole)
        return "default"
        
    def select_model(self, model_id):
        """Select a model in the list by its ID"""
        for i in range(self.model_list.count()):
            item = self.model_list.item(i)
            if item and (item.flags() & Qt.ItemIsSelectable) and item.data(Qt.UserRole) == model_id:
                self.model_list.setCurrentItem(item)
                self._on_model_selected(item)
                return True
        return False


class SynthesisControls(QWidget):
    """Widget to control voice synthesis parameters"""
    
    parameters_changed = Signal(dict)  # Signal emitted when parameters change
    engine_selected = Signal(str)      # Signal emitted when engine is changed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Synthesis parameters
        self.parameters = {
            "speed": 1.0,       # Speech speed (0.5 - 2.0)
            "pitch": 0.0,       # Pitch (-12 - +12 semitones)
            "formant": 0.0,     # Formant (-50 - +50 %)
            "emotion": "neutral", # Emotion (neutral, happy, sad, etc.)
            "engine_type": "auto" # Type of engine to use (auto, midi, fast)
        }
        
        # UI configuration
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize user interface"""
        layout = QVBoxLayout(self)
        
        # Basic parameters group
        basic_group = QGroupBox("Basic Parameters")
        basic_layout = QVBoxLayout(basic_group)
        
        # Speed control
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickInterval(25)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("1.0x")
        speed_layout.addWidget(self.speed_label)
        basic_layout.addLayout(speed_layout)
        
        # Pitch control
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(QLabel("Pitch:"))
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setTickInterval(3)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)
        self.pitch_slider.valueChanged.connect(self._on_pitch_changed)
        pitch_layout.addWidget(self.pitch_slider)
        self.pitch_label = QLabel("0 st")
        pitch_layout.addWidget(self.pitch_label)
        basic_layout.addLayout(pitch_layout)
        
        # Formant control
        formant_layout = QHBoxLayout()
        formant_layout.addWidget(QLabel("Formant:"))
        self.formant_slider = QSlider(Qt.Horizontal)
        self.formant_slider.setRange(-50, 50)
        self.formant_slider.setValue(0)
        self.formant_slider.setTickInterval(10)
        self.formant_slider.setTickPosition(QSlider.TicksBelow)
        self.formant_slider.valueChanged.connect(self._on_formant_changed)
        formant_layout.addWidget(self.formant_slider)
        self.formant_label = QLabel("0%")
        formant_layout.addWidget(self.formant_label)
        basic_layout.addLayout(formant_layout)
        
        # Add basic parameters group
        layout.addWidget(basic_group)
        
        # Advanced parameters group
        advanced_group = QGroupBox("Advanced Parameters")
        advanced_layout = QVBoxLayout(advanced_group)
        
        # Emotion selection
        emotion_layout = QHBoxLayout()
        emotion_layout.addWidget(QLabel("Emotion:"))
        self.emotion_combo = QComboBox()
        self.emotion_combo.addItems(["Neutral", "Happy", "Sad", "Angry", "Surprised", "Calm"])
        self.emotion_combo.currentIndexChanged.connect(self._on_emotion_changed)
        emotion_layout.addWidget(self.emotion_combo)
        advanced_layout.addLayout(emotion_layout)
        
        # Engine selection
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("Engine:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Auto", "High Quality (MIDI)", "Fast Response"])
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        engine_layout.addWidget(self.engine_combo)
        advanced_layout.addLayout(engine_layout)
        
        # MIDI mode
        midi_layout = QHBoxLayout()
        midi_layout.addWidget(QLabel("MIDI Control:"))
        self.midi_check = QCheckBox("Enable MIDI Modulation")
        self.midi_check.setChecked(True)
        midi_layout.addWidget(self.midi_check)
        advanced_layout.addLayout(midi_layout)
        
        # Add advanced parameters group
        layout.addWidget(advanced_group)
        
        # Spacer
        layout.addStretch(1)
        
    def _set_mode(self, mode):
        """Set mode (manual or MIDI)"""
        if mode == "midi":
            self.midi_check.setChecked(True)
            # Grey out sliders but don't disable them completely
            self.speed_slider.setEnabled(False)
            self.pitch_slider.setEnabled(False)
            self.formant_slider.setEnabled(False)
        else:
            self.midi_check.setChecked(False)
            # Re-enable sliders
            self.speed_slider.setEnabled(True)
            self.pitch_slider.setEnabled(True)
            self.formant_slider.setEnabled(True)
        
        # Emit the mode change
        self.parameters["mode"] = mode
        self.parameters_changed.emit(self.parameters)
        
    def _on_speed_changed(self, value):
        """Handle speed slider change"""
        speed = value / 100.0
        self.parameters["speed"] = speed
        self.speed_label.setText(f"{speed:.1f}x")
        self.parameters_changed.emit(self.parameters)
        
    def _on_pitch_changed(self, value):
        """Handle pitch slider change"""
        self.parameters["pitch"] = value
        self.pitch_label.setText(f"{value:+d} st")
        self.parameters_changed.emit(self.parameters)
    
    def _on_formant_changed(self, value):
        """Handle formant slider change"""
        self.parameters["formant"] = value
        self.formant_label.setText(f"{value:+d}%")
        self.parameters_changed.emit(self.parameters)
    
    def _on_emotion_changed(self, index):
        """Handle emotion combobox change"""
        emotion = self.emotion_combo.currentText().lower()
        self.parameters["emotion"] = emotion
        self.parameters_changed.emit(self.parameters)
    
    def _on_engine_changed(self, index):
        """Handle engine combobox change"""
        engine_map = ["auto", "midi", "fast"]
        engine_type = engine_map[index] if index < len(engine_map) else "auto"
        self.parameters["engine_type"] = engine_type
        self.engine_selected.emit(engine_type)
        
    def update_from_midi(self, modulation_data):
        """Update controls from MIDI controller data"""
        if not self.midi_check.isChecked():
            return
            
        # Update speed based on MIDI
        if "speed" in modulation_data:
            speed_value = int(modulation_data["speed"] * 100)
            if speed_value != self.speed_slider.value():
                self.speed_slider.setValue(speed_value)
                
        # Update pitch based on MIDI
        if "pitch" in modulation_data:
            pitch_value = int(modulation_data["pitch"])
            if pitch_value != self.pitch_slider.value():
                self.pitch_slider.setValue(pitch_value)
                
        # Update formant based on MIDI
        if "formant" in modulation_data:
            formant_value = int(modulation_data["formant"])
            if formant_value != self.formant_slider.value():
                self.formant_slider.setValue(formant_value)


class LanguageSelector(QWidget):
    """Widget for selecting synthesis language"""
    
    language_changed = Signal(str)  # Signal emitted when language changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Language mapping (code -> name)
        self.languages = {
            "en": "English",
            "fr": "French",
            "es": "Spanish",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic"
        }
        
        # Currently supported languages for the selected model
        self.supported_languages = ["en", "fr"]
        
        # Setup the interface
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize user interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(QLabel("Language:"))
        
        self.language_combo = QComboBox()
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        layout.addWidget(self.language_combo)
        
        # Initial update with default languages
        self.update_languages(self.supported_languages)
        
    def update_languages(self, supported_languages):
        """Update the list of available languages"""
        # Store current language if exists
        current_lang = None
        if self.language_combo.currentIndex() >= 0:
            current_lang = self.language_combo.currentData()
        
        # Update supported languages
        self.supported_languages = supported_languages
        
        # Update combobox
        self.language_combo.clear()
        
        for lang_code in supported_languages:
            lang_name = self.languages.get(lang_code, lang_code.upper())
            self.language_combo.addItem(lang_name, lang_code)
        
        # Try to restore previous language selection
        if current_lang and current_lang in supported_languages:
            self.set_language(current_lang)
        elif "en" in supported_languages:
            self.set_language("en")
        elif len(supported_languages) > 0:
            self.set_language(supported_languages[0])
        
    def set_language(self, language_code):
        """Set the current language"""
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == language_code:
                self.language_combo.setCurrentIndex(i)
                return True
        return False
        
    def _on_language_changed(self, index):
        """Handle language selection change"""
        if index >= 0:
            language = self.language_combo.itemData(index)
            self.language_changed.emit(language)
    
    def get_current_language(self):
        """Get the currently selected language code"""
        index = self.language_combo.currentIndex()
        if index >= 0:
            return self.language_combo.itemData(index)
        return "en"  # Default to English


class SynthesisTab(QWidget):
    """Main tab for voice synthesis and text-to-speech"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Text-to-speech engine
        self.tts_engine = None
        self.current_model = "default"
        self.current_language = "en"
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self._connect_signals()
        
    def setup_ui(self):
        """Initialize user interface"""
        main_layout = QVBoxLayout(self)
        
        # Create a splitter for main areas
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # Top area - Text input and synthesis controls
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        
        # Text input area (left)
        text_group = QGroupBox("Text to Synthesize")
        text_layout = QVBoxLayout(text_group)
        
        # Language selector
        self.language_selector = LanguageSelector()
        text_layout.addWidget(self.language_selector)
        
        # Text input
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Enter text to synthesize...")
        self.text_edit.setMinimumHeight(100)
        text_layout.addWidget(self.text_edit)
        
        # Synthesis button
        buttons_layout = QHBoxLayout()
        self.synthesize_button = QPushButton("Generate Speech")
        self.synthesize_button.setStyleSheet("background-color: #3daee9; color: white; font-weight: bold; padding: 8px;")
        buttons_layout.addWidget(self.synthesize_button)
        
        # Save button
        self.save_button = QPushButton("Save Audio")
        self.save_button.setEnabled(False)
        buttons_layout.addWidget(self.save_button)
        
        text_layout.addLayout(buttons_layout)
        
        # Add text group to left side
        top_layout.addWidget(text_group, 2)  # 2/3 of width
        
        # Synthesis controls (right)
        controls_group = QGroupBox("Voice Parameters")
        controls_layout = QVBoxLayout(controls_group)
        
        # Voice model selector
        self.model_selector = VoiceModelSelector()
        controls_layout.addWidget(self.model_selector)
        
        # Synthesis parameters
        self.synthesizer = SynthesisControls()
        controls_layout.addWidget(self.synthesizer)
        
        # Add controls to right side
        top_layout.addWidget(controls_group, 1)  # 1/3 of width
        
        # Add top widget to splitter
        splitter.addWidget(top_widget)
        
        # Bottom area - Playback and visualization
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Playback controls
        self.playback_controls = QWidget()
        playback_layout = QHBoxLayout(self.playback_controls)
        
        self.play_button = QPushButton("▶ Play")
        self.play_button.setEnabled(False)
        playback_layout.addWidget(self.play_button)
        
        self.pause_button = QPushButton("⏸ Pause")
        self.pause_button.setEnabled(False)
        playback_layout.addWidget(self.pause_button)
        
        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.setEnabled(False)
        playback_layout.addWidget(self.stop_button)
        
        # Progress display
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        playback_layout.addWidget(self.progress_bar, 2)
        
        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        volume_layout.addWidget(self.volume_slider)
        playback_layout.addLayout(volume_layout)
        
        bottom_layout.addWidget(self.playback_controls)
        
        # Waveform visualization
        self.waveform_group = QGroupBox("Audio Waveform")
        waveform_layout = QVBoxLayout(self.waveform_group)
        
        # Add bottom widget to splitter
        splitter.addWidget(bottom_widget)
        
        # Set initial splitter sizes (2/3 top, 1/3 bottom)
        splitter.setSizes([2000, 1000])
        
        # Status message
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")
        main_layout.addWidget(self.status_label)
        
    def _connect_signals(self):
        """Connect signals and slots"""
        # Voice model selection
        self.model_selector.model_selected.connect(self._on_model_selected)
        
        # Language selection
        self.language_selector.language_changed.connect(self._on_language_changed)
        
        # Synthesis button
        self.synthesize_button.clicked.connect(self._on_synthesize)
        
        # Save button
        self.save_button.clicked.connect(self._on_save_audio)
        
        # Playback controls
        self.play_button.clicked.connect(self._on_play)
        self.pause_button.clicked.connect(self._on_pause)
        self.stop_button.clicked.connect(self._on_stop)
        
    def _on_model_selected(self, model_id):
        """Handle voice model selection"""
        self.current_model = model_id
        self.status_label.setText(f"Selected model: {model_id}")
        
        # Update supported languages based on the selected model
        model_info = model_manager.get_model_info(model_id)
        if model_info and "languages" in model_info:
            self.language_selector.update_languages(model_info["languages"])
        
    def _on_language_changed(self, language):
        """Handle language selection"""
        self.current_language = language
        
    def _on_synthesize(self):
        """Handle synthesis button click"""
        text = self.text_edit.toPlainText().strip()
        
        if not text:
            self.status_label.setText("Please enter text to synthesize")
            return
            
        self.status_label.setText(f"Synthesizing text in {self.current_language}...")
        self.synthesize_button.setEnabled(False)
        
        # In a real implementation, this would call the TTS engine
        # For this demo, we'll just simulate success after a delay
        QTimer.singleShot(1000, self._synthesis_completed)
        
    def _synthesis_completed(self):
        """Called when synthesis is complete"""
        self.synthesize_button.setEnabled(True)
        self.status_label.setText("Synthesis completed")
        
        # Enable playback controls
        self.play_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
    def _on_save_audio(self):
        """Handle save audio button click"""
        # Show a file dialog to get save location
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Audio File", "", "WAV Files (*.wav);;All Files (*.*)"
        )
        
        if file_path:
            # In a real implementation, this would save the audio file
            self.status_label.setText(f"Audio saved to: {file_path}")
        
    def _on_play(self):
        """Handle play button click"""
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Playing audio...")
        
    def _on_pause(self):
        """Handle pause button click"""
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.status_label.setText("Playback paused")
        
    def _on_stop(self):
        """Handle stop button click"""
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Playback stopped")
        
    def set_pitch(self, value):
        """Set pitch value from external control (e.g., MIDI)"""
        self.synthesizer._on_pitch_changed(value)
        
    def set_speed(self, value):
        """Set speed value from external control (e.g., MIDI)"""
        speed_value = int(value * 100)
        self.synthesizer._on_speed_changed(speed_value)
        
    def set_volume(self, value):
        """Set volume value from external control (e.g., MIDI)"""
        volume_value = int(value * 100)
        self.volume_slider.setValue(volume_value) 