"""
Module pour la modulation de la voix via MIDI.

Ce module fournit des widgets pour contrôler et visualiser
la modulation de la voix en temps réel via des contrôleurs MIDI.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QSlider, QDial, QGroupBox, QComboBox, 
                              QPushButton, QCheckBox, QGridLayout, QSizePolicy)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QSize, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QPen, QColor, QLinearGradient, QBrush, QFont, QPainterPath

class SliderWithLabel(QWidget):
    """Slider avec une étiquette et une valeur numérique"""
    
    valueChanged = Signal(int)  # Signal émis lorsque la valeur change
    
    def __init__(self, label, min_val=0, max_val=127, default_val=64, parent=None):
        super().__init__(parent)
        self.label_text = label
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Label
        self.label = QLabel(label)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setValue(default_val)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #333, stop:1 #888);
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #4096ff, stop:1 #007bff);
                border: 1px solid #5c5c5c;
                width: 18px;
                border-radius: 9px;
                margin: -5px 0;
            }
        """)
        layout.addWidget(self.slider)
        
        # Valeur
        self.value_label = QLabel(str(default_val))
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        # Connexion du signal
        self.slider.valueChanged.connect(self._on_value_changed)
        
    def _on_value_changed(self, value):
        """Gère le changement de valeur du slider"""
        self.value_label.setText(str(value))
        self.valueChanged.emit(value)
        
    def setValue(self, value):
        """Définit la valeur du slider"""
        self.slider.setValue(value)
        
    def value(self):
        """Retourne la valeur actuelle du slider"""
        return self.slider.value()
        
    def setMidiControlled(self, is_controlled):
        """Indique si le slider est contrôlé par MIDI"""
        if is_controlled:
            self.label.setStyleSheet("color: #4096ff; font-weight: bold;")
        else:
            self.label.setStyleSheet("")


class ModulationVisualizer(QWidget):
    """Widget pour visualiser l'effet de modulation en temps réel"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 80)
        
        # Paramètres de modulation
        self.pitch = 0          # -24 à +24 demi-tons
        self.formant = 0        # -100 à +100 %
        self.vibrato = 0        # 0 à 100 %
        self.tremolo = 0        # 0 à 100 %
        self.distortion = 0     # 0 à 100 %
        
        # Animation pour l'effet vibrato/tremolo
        self.phase = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_phase)
        self.timer.start(16)  # ~60 fps
        
    def _update_phase(self):
        """Met à jour la phase pour les animations"""
        self.phase = (self.phase + 0.1) % (2 * 3.14159)
        self.update()
        
    def set_pitch(self, value):
        """Définit la hauteur tonale (-24 à +24)"""
        self.pitch = value
        self.update()
        
    def set_formant(self, value):
        """Définit le formant (-100 à +100)"""
        self.formant = value
        self.update()
        
    def set_vibrato(self, value):
        """Définit l'intensité du vibrato (0 à 100)"""
        self.vibrato = value
        self.update()
        
    def set_tremolo(self, value):
        """Définit l'intensité du tremolo (0 à 100)"""
        self.tremolo = value
        self.update()
        
    def set_distortion(self, value):
        """Définit l'intensité de la distorsion (0 à 100)"""
        self.distortion = value
        self.update()
        
    def paintEvent(self, event):
        """Dessine la visualisation de la modulation"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Dessiner le fond
        painter.fillRect(0, 0, width, height, QColor(30, 30, 30))
        
        # Paramètres de la forme d'onde
        center_y = height / 2
        amplitude = height / 4 * (1.0 - self.tremolo / 200.0)
        
        # Coefficient de distorsion
        distortion_factor = self.distortion / 100.0
        
        # Fréquence de base (modifiée par le pitch)
        base_freq = 1.0 + self.pitch / 48.0  # -24/+24 demi-tons -> 0.5/1.5
        
        # Coefficient de vibrato
        vibrato_intensity = self.vibrato / 100.0 * 0.25
        
        # Dessiner la forme d'onde
        path = QPainterPath()
        path.moveTo(0, center_y)
        
        for x in range(width):
            # Normaliser x entre 0 et 2pi
            t = (x / width) * 2 * 3.14159 * 8
            
            # Appliquer le vibrato (modulation de fréquence)
            t_vibrato = t * (base_freq + vibrato_intensity * math.sin(self.phase * 5))
            
            # Calcul de la forme d'onde
            if distortion_factor < 0.1:
                # Forme d'onde sinusoïdale (voix douce)
                y = math.sin(t_vibrato)
            else:
                # Forme d'onde distordue
                y = math.sin(t_vibrato)
                
                # Ajouter des harmoniques pour la distorsion
                for i in range(2, int(distortion_factor * 10) + 1):
                    y += (math.sin(t_vibrato * i) / i) * distortion_factor
                    
                # Normaliser
                y = max(-1.0, min(1.0, y * (1 + distortion_factor)))
            
            # Appliquer le tremolo (modulation d'amplitude)
            tremolo_factor = 1.0 - (self.tremolo / 100.0 * 0.5 * (1 + math.sin(self.phase * 3)))
            
            # Position verticale finale
            final_y = center_y - y * amplitude * tremolo_factor
            
            if x == 0:
                path.moveTo(x, final_y)
            else:
                path.lineTo(x, final_y)
        
        # Dessiner la forme d'onde avec un dégradé en fonction du formant
        formant_factor = (self.formant + 100) / 200.0  # 0 à 1
        gradient = QLinearGradient(0, 0, 0, height)
        
        # Couleur basée sur le formant (bleu->vert->rouge)
        if formant_factor < 0.5:
            # De bleu à vert
            r = int(formant_factor * 2 * 255)
            g = 100 + int(formant_factor * 2 * 155)
            b = 255 - int(formant_factor * 2 * 155)
        else:
            # De vert à rouge
            f = (formant_factor - 0.5) * 2
            r = 100 + int(f * 155)
            g = 255 - int(f * 155)
            b = 100 - int(f * 100)
        
        wave_color = QColor(r, g, b)
        
        # Dégradé pour l'effet de profondeur
        gradient.setColorAt(0, wave_color.lighter(150))
        gradient.setColorAt(1, wave_color.darker(150))
        
        painter.setPen(QPen(wave_color, 2))
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)
        
        # Dessiner une ligne horizontale au centre
        painter.setPen(QPen(QColor(70, 70, 70), 1, Qt.DashLine))
        painter.drawLine(0, center_y, width, center_y)


class MidiModulationPanel(QWidget):
    """Panneau de contrôle pour la modulation vocale via MIDI"""
    
    modulationChanged = Signal(dict)  # Signal émis quand la modulation change
    noteTriggered = Signal(int, int)  # Signal émis quand une note est jouée via le clavier (note, vélocité)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration de base
        self.setMinimumWidth(300)
        self.setup_ui()
        
        # Dictionnaire pour stocker les mappages MIDI -> contrôle
        self.midi_controls = {}
        
        # Activer par défaut
        self.enable_checkbox.setChecked(True)
        
    def setup_ui(self):
        """Initialise l'interface utilisateur"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # En-tête avec activation
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Modulation MIDI")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.enable_checkbox = QCheckBox("Activer")
        self.enable_checkbox.toggled.connect(self._on_enable_toggled)
        header_layout.addWidget(self.enable_checkbox)
        
        main_layout.addLayout(header_layout)
        
        # Visualisation
        visual_group = QGroupBox("Visualisation")
        visual_layout = QVBoxLayout(visual_group)
        
        self.visualizer = ModulationVisualizer()
        visual_layout.addWidget(self.visualizer)
        
        main_layout.addWidget(visual_group)
        
        # Contrôles
        controls_layout = QGridLayout()
        controls_layout.setColumnStretch(0, 1)
        controls_layout.setColumnStretch(1, 1)
        
        # Contrôles de hauteur et formant
        self.pitch_slider = SliderWithLabel("Hauteur", -24, 24, 0)
        self.pitch_slider.valueChanged.connect(self._on_pitch_changed)
        controls_layout.addWidget(self.pitch_slider, 0, 0)
        
        self.formant_slider = SliderWithLabel("Formant", -100, 100, 0)
        self.formant_slider.valueChanged.connect(self._on_formant_changed)
        controls_layout.addWidget(self.formant_slider, 0, 1)
        
        # Contrôles de vibrato et tremolo
        self.vibrato_slider = SliderWithLabel("Vibrato", 0, 100, 0)
        self.vibrato_slider.valueChanged.connect(self._on_vibrato_changed)
        controls_layout.addWidget(self.vibrato_slider, 1, 0)
        
        self.tremolo_slider = SliderWithLabel("Tremolo", 0, 100, 0)
        self.tremolo_slider.valueChanged.connect(self._on_tremolo_changed)
        controls_layout.addWidget(self.tremolo_slider, 1, 1)
        
        # Contrôle de distorsion
        self.distortion_slider = SliderWithLabel("Distorsion", 0, 100, 0)
        self.distortion_slider.valueChanged.connect(self._on_distortion_changed)
        controls_layout.addWidget(self.distortion_slider, 2, 0)
        
        main_layout.addLayout(controls_layout)
        
        # Mode de déclenchement
        trigger_group = QGroupBox("Mode de déclenchement")
        trigger_layout = QVBoxLayout(trigger_group)
        
        self.trigger_mode = QComboBox()
        self.trigger_mode.addItem("Temps réel", "realtime")
        self.trigger_mode.addItem("Sur note", "note")
        self.trigger_mode.addItem("Sur enregistrement", "recording")
        trigger_layout.addWidget(self.trigger_mode)
        
        main_layout.addWidget(trigger_group)
        
        # Espacement
        main_layout.addStretch()
        
    def _on_enable_toggled(self, enabled):
        """Gère l'activation/désactivation de la modulation"""
        # Mettre à jour l'interface
        self._update_ui_state(enabled)
        
        # Émettre le signal avec les valeurs actuelles
        if enabled:
            self._emit_modulation_values()
        else:
            # Réinitialiser tous les paramètres
            self.modulationChanged.emit({
                "enabled": False,
                "pitch": 0,
                "formant": 0,
                "vibrato": 0,
                "tremolo": 0,
                "distortion": 0,
                "trigger_mode": self.trigger_mode.currentData()
            })
            
    def _update_ui_state(self, enabled):
        """Met à jour l'état de l'interface selon l'activation"""
        self.pitch_slider.setEnabled(enabled)
        self.formant_slider.setEnabled(enabled)
        self.vibrato_slider.setEnabled(enabled)
        self.tremolo_slider.setEnabled(enabled)
        self.distortion_slider.setEnabled(enabled)
        self.trigger_mode.setEnabled(enabled)
        
    def _on_pitch_changed(self, value):
        """Gère le changement de hauteur"""
        self.visualizer.set_pitch(value)
        self._emit_modulation_values()
        
    def _on_formant_changed(self, value):
        """Gère le changement de formant"""
        self.visualizer.set_formant(value)
        self._emit_modulation_values()
        
    def _on_vibrato_changed(self, value):
        """Gère le changement de vibrato"""
        self.visualizer.set_vibrato(value)
        self._emit_modulation_values()
        
    def _on_tremolo_changed(self, value):
        """Gère le changement de tremolo"""
        self.visualizer.set_tremolo(value)
        self._emit_modulation_values()
        
    def _on_distortion_changed(self, value):
        """Gère le changement de distorsion"""
        self.visualizer.set_distortion(value)
        self._emit_modulation_values()
        
    def _emit_modulation_values(self):
        """Émet le signal avec toutes les valeurs de modulation"""
        if not self.enable_checkbox.isChecked():
            return
            
        self.modulationChanged.emit({
            "enabled": True,
            "pitch": self.pitch_slider.value(),
            "formant": self.formant_slider.value(),
            "vibrato": self.vibrato_slider.value(),
            "tremolo": self.tremolo_slider.value(),
            "distortion": self.distortion_slider.value(),
            "trigger_mode": self.trigger_mode.currentData()
        })
        
    def handle_midi_cc(self, channel, cc, value):
        """Gère un contrôleur MIDI"""
        # Identifier le contrôle associé à ce CC
        control_id = f"{channel}:{cc}"
        
        if control_id in self.midi_controls:
            control = self.midi_controls[control_id]
            
            # Normaliser la valeur MIDI (0-127) à la plage du contrôle
            if control == "pitch":
                normalized_value = int(-24 + (value / 127) * 48)  # -24 à +24
                self.pitch_slider.setValue(normalized_value)
                return True
                
            elif control == "formant":
                normalized_value = int(-100 + (value / 127) * 200)  # -100 à +100
                self.formant_slider.setValue(normalized_value)
                return True
                
            elif control == "vibrato":
                normalized_value = int((value / 127) * 100)  # 0 à 100
                self.vibrato_slider.setValue(normalized_value)
                return True
                
            elif control == "tremolo":
                normalized_value = int((value / 127) * 100)  # 0 à 100
                self.tremolo_slider.setValue(normalized_value)
                return True
                
            elif control == "distortion":
                normalized_value = int((value / 127) * 100)  # 0 à 100
                self.distortion_slider.setValue(normalized_value)
                return True
                
        return False
        
    def handle_midi_note(self, channel, note, velocity):
        """Gère une note MIDI pour le mode de déclenchement par note"""
        if self.enable_checkbox.isChecked() and self.trigger_mode.currentData() == "note":
            self.noteTriggered.emit(note, velocity)
            return True
            
        return False
        
    def set_midi_mapping(self, mapping):
        """Définit le mapping MIDI -> contrôles"""
        self.midi_controls = mapping
        
        # Mettre à jour l'apparence des contrôles selon le mapping
        self.pitch_slider.setMidiControlled("pitch" in self.midi_controls.values())
        self.formant_slider.setMidiControlled("formant" in self.midi_controls.values())
        self.vibrato_slider.setMidiControlled("vibrato" in self.midi_controls.values())
        self.tremolo_slider.setMidiControlled("tremolo" in self.midi_controls.values())
        self.distortion_slider.setMidiControlled("distortion" in self.midi_controls.values())
        
    def reset_modulation(self):
        """Réinitialise tous les paramètres de modulation"""
        self.pitch_slider.setValue(0)
        self.formant_slider.setValue(0)
        self.vibrato_slider.setValue(0)
        self.tremolo_slider.setValue(0)
        self.distortion_slider.setValue(0)
        self._emit_modulation_values()


import math  # Nécessaire pour les fonctions trigonométriques 