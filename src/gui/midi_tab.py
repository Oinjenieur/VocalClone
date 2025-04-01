"""
Module d'interface graphique pour la gestion MIDI.

Ce module fournit l'interface utilisateur pour configurer et
utiliser les périphériques MIDI dans l'application de synthèse vocale.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QGridLayout, QSlider, QCheckBox,
    QSpinBox, QTabWidget, QProgressBar
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont

from utils.midi_device_manager import MidiDeviceManager


class MidiTab(QWidget):
    """Onglet pour la configuration et le contrôle MIDI"""
    
    midi_parameter_changed = Signal(str, float)  # paramètre, valeur
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialiser le gestionnaire MIDI
        self.midi_manager = MidiDeviceManager()
        self.midi_manager.device_connected.connect(self._handle_device_connected)
        self.midi_manager.device_disconnected.connect(self._handle_device_disconnected)
        self.midi_manager.midi_message_received.connect(self._handle_midi_message)
        
        # Dictionnaire de correspondance MIDI
        self.midi_mapping = {}  # {contrôleur: paramètre}
        
        # Créer l'interface utilisateur
        self._setup_ui()
        
        # Rafraîchir la liste des périphériques
        self._refresh_device_lists()
    
    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # Groupe pour les périphériques
        devices_group = QGroupBox("Périphériques MIDI")
        devices_layout = QGridLayout(devices_group)
        
        # Entrée MIDI
        devices_layout.addWidget(QLabel("Entrée:"), 0, 0)
        self.input_combo = QComboBox()
        devices_layout.addWidget(self.input_combo, 0, 1)
        self.input_button = QPushButton("Connecter")
        self.input_button.clicked.connect(self._toggle_input_connection)
        devices_layout.addWidget(self.input_button, 0, 2)
        
        # Sortie MIDI
        devices_layout.addWidget(QLabel("Sortie:"), 1, 0)
        self.output_combo = QComboBox()
        devices_layout.addWidget(self.output_combo, 1, 1)
        self.output_button = QPushButton("Connecter")
        self.output_button.clicked.connect(self._toggle_output_connection)
        devices_layout.addWidget(self.output_button, 1, 2)
        
        # Bouton de rafraîchissement
        refresh_button = QPushButton("Rafraîchir")
        refresh_button.clicked.connect(self._refresh_device_lists)
        devices_layout.addWidget(refresh_button, 2, 0, 1, 3)
        
        # Groupe pour le mappage MIDI
        mapping_group = QGroupBox("Mappage MIDI")
        mapping_layout = QVBoxLayout(mapping_group)
        
        # Mode d'apprentissage
        learn_layout = QHBoxLayout()
        self.learn_checkbox = QCheckBox("Mode d'apprentissage")
        self.learn_checkbox.toggled.connect(self._toggle_learn_mode)
        learn_layout.addWidget(self.learn_checkbox)
        self.current_param_label = QLabel("Aucun paramètre sélectionné")
        learn_layout.addWidget(self.current_param_label)
        mapping_layout.addLayout(learn_layout)
        
        # Onglets de paramètres
        param_tabs = QTabWidget()
        
        # Onglet de hauteur
        pitch_tab = QWidget()
        pitch_layout = QVBoxLayout(pitch_tab)
        
        # Contrôles de hauteur
        pitch_grid = QGridLayout()
        
        # Paramètre: Hauteur
        pitch_grid.addWidget(QLabel("Hauteur:"), 0, 0)
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setTickInterval(1)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)
        self.pitch_slider.valueChanged.connect(lambda v: self._update_parameter("pitch", v))
        pitch_grid.addWidget(self.pitch_slider, 0, 1)
        self.pitch_value = QLabel("0")
        pitch_grid.addWidget(self.pitch_value, 0, 2)
        self.pitch_learn = QPushButton("Apprendre")
        self.pitch_learn.clicked.connect(lambda: self._start_learn("pitch"))
        pitch_grid.addWidget(self.pitch_learn, 0, 3)
        self.pitch_clear = QPushButton("Effacer")
        self.pitch_clear.clicked.connect(lambda: self._clear_mapping("pitch"))
        pitch_grid.addWidget(self.pitch_clear, 0, 4)
        
        pitch_layout.addLayout(pitch_grid)
        param_tabs.addTab(pitch_tab, "Hauteur")
        
        # Onglet de vitesse
        speed_tab = QWidget()
        speed_layout = QVBoxLayout(speed_tab)
        
        # Contrôles de vitesse
        speed_grid = QGridLayout()
        
        # Paramètre: Vitesse
        speed_grid.addWidget(QLabel("Vitesse:"), 0, 0)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickInterval(10)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.valueChanged.connect(lambda v: self._update_parameter("speed", v/100.0))
        speed_grid.addWidget(self.speed_slider, 0, 1)
        self.speed_value = QLabel("1.0")
        speed_grid.addWidget(self.speed_value, 0, 2)
        self.speed_learn = QPushButton("Apprendre")
        self.speed_learn.clicked.connect(lambda: self._start_learn("speed"))
        speed_grid.addWidget(self.speed_learn, 0, 3)
        self.speed_clear = QPushButton("Effacer")
        self.speed_clear.clicked.connect(lambda: self._clear_mapping("speed"))
        speed_grid.addWidget(self.speed_clear, 0, 4)
        
        speed_layout.addLayout(speed_grid)
        param_tabs.addTab(speed_tab, "Vitesse")
        
        # Onglet d'expression
        expr_tab = QWidget()
        expr_layout = QVBoxLayout(expr_tab)
        
        # Contrôles d'expression
        expr_grid = QGridLayout()
        
        # Paramètre: Volume
        expr_grid.addWidget(QLabel("Volume:"), 0, 0)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 200)
        self.volume_slider.setValue(100)
        self.volume_slider.setTickInterval(10)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.volume_slider.valueChanged.connect(lambda v: self._update_parameter("volume", v/100.0))
        expr_grid.addWidget(self.volume_slider, 0, 1)
        self.volume_value = QLabel("1.0")
        expr_grid.addWidget(self.volume_value, 0, 2)
        self.volume_learn = QPushButton("Apprendre")
        self.volume_learn.clicked.connect(lambda: self._start_learn("volume"))
        expr_grid.addWidget(self.volume_learn, 0, 3)
        self.volume_clear = QPushButton("Effacer")
        self.volume_clear.clicked.connect(lambda: self._clear_mapping("volume"))
        expr_grid.addWidget(self.volume_clear, 0, 4)
        
        expr_layout.addLayout(expr_grid)
        param_tabs.addTab(expr_tab, "Expression")
        
        mapping_layout.addWidget(param_tabs)
        
        # Moniteur MIDI
        monitor_group = QGroupBox("Moniteur MIDI")
        monitor_layout = QVBoxLayout(monitor_group)
        
        self.last_message_label = QLabel("Aucun message reçu")
        monitor_layout.addWidget(self.last_message_label)
        
        # Indicateur d'activité
        activity_layout = QHBoxLayout()
        activity_layout.addWidget(QLabel("Activité:"))
        self.activity_indicator = QProgressBar()
        self.activity_indicator.setRange(0, 127)
        self.activity_indicator.setValue(0)
        activity_layout.addWidget(self.activity_indicator)
        
        # Timer pour réinitialiser l'indicateur d'activité
        self.activity_timer = QTimer(self)
        self.activity_timer.setSingleShot(True)
        self.activity_timer.timeout.connect(lambda: self.activity_indicator.setValue(0))
        
        monitor_layout.addLayout(activity_layout)
        
        # Ajouter les groupes au layout principal
        main_layout.addWidget(devices_group)
        main_layout.addWidget(mapping_group)
        main_layout.addWidget(monitor_group)
        
        # Configuration finale
        self.setLayout(main_layout)
    
    def _refresh_device_lists(self):
        """Rafraîchit les listes de périphériques"""
        # Sauvegarder les sélections actuelles
        current_input = self.input_combo.currentText() if self.input_combo.count() > 0 else ""
        current_output = self.output_combo.currentText() if self.output_combo.count() > 0 else ""
        
        # Mettre à jour les listes
        self.midi_manager._scan_devices()
        
        # Mettre à jour les combobox
        self.input_combo.clear()
        for port in self.midi_manager.get_available_inputs():
            self.input_combo.addItem(port)
        
        self.output_combo.clear()
        for port in self.midi_manager.get_available_outputs():
            self.output_combo.addItem(port)
        
        # Restaurer les sélections si possible
        if current_input:
            index = self.input_combo.findText(current_input)
            if index >= 0:
                self.input_combo.setCurrentIndex(index)
        
        if current_output:
            index = self.output_combo.findText(current_output)
            if index >= 0:
                self.output_combo.setCurrentIndex(index)
    
    def _toggle_input_connection(self):
        """Connecte ou déconnecte l'entrée MIDI"""
        if self.midi_manager.input_port_name is None:
            # Connecter
            index = self.input_combo.currentIndex()
            if index >= 0:
                success = self.midi_manager.connect_input(index)
                if success:
                    self.input_button.setText("Déconnecter")
        else:
            # Déconnecter
            success = self.midi_manager.disconnect_input()
            if success:
                self.input_button.setText("Connecter")
    
    def _toggle_output_connection(self):
        """Connecte ou déconnecte la sortie MIDI"""
        if self.midi_manager.output_port_name is None:
            # Connecter
            index = self.output_combo.currentIndex()
            if index >= 0:
                success = self.midi_manager.connect_output(index)
                if success:
                    self.output_button.setText("Déconnecter")
        else:
            # Déconnecter
            success = self.midi_manager.disconnect_output()
            if success:
                self.output_button.setText("Connecter")
    
    @Slot(str, str)
    def _handle_device_connected(self, port_name, direction):
        """Gère la connexion d'un périphérique MIDI"""
        # Mettre à jour les boutons
        if direction == "input" and port_name == self.midi_manager.input_port_name:
            self.input_button.setText("Déconnecter")
        elif direction == "output" and port_name == self.midi_manager.output_port_name:
            self.output_button.setText("Déconnecter")
        
        # Rafraîchir les listes
        self._refresh_device_lists()
    
    @Slot(str, str)
    def _handle_device_disconnected(self, port_name, direction):
        """Gère la déconnexion d'un périphérique MIDI"""
        # Mettre à jour les boutons
        if direction == "input":
            self.input_button.setText("Connecter")
        elif direction == "output":
            self.output_button.setText("Connecter")
        
        # Rafraîchir les listes
        self._refresh_device_lists()
    
    @Slot(list)
    def _handle_midi_message(self, message):
        """Gère un message MIDI reçu"""
        status, data1, data2 = message
        
        # Afficher le message
        status_type = status & 0xF0
        channel = status & 0x0F
        
        msg_type = ""
        if status_type == 0x90 and data2 > 0:
            msg_type = "Note On"
        elif status_type == 0x80 or (status_type == 0x90 and data2 == 0):
            msg_type = "Note Off"
        elif status_type == 0xB0:
            msg_type = "Control Change"
        elif status_type == 0xE0:
            msg_type = "Pitch Bend"
        else:
            msg_type = f"Status: {status_type:02X}"
        
        self.last_message_label.setText(f"{msg_type} | Canal: {channel+1} | Data: {data1}, {data2}")
        
        # Mettre à jour l'indicateur d'activité
        self.activity_indicator.setValue(data2 if data2 > 0 else data1)
        self.activity_timer.start(500)  # Réinitialiser après 500ms
        
        # Traiter le mappage MIDI (pour les CC uniquement)
        if status_type == 0xB0:  # Control Change
            cc = data1
            value = data2
            
            # Mode d'apprentissage
            if self.learn_checkbox.isChecked() and hasattr(self, "learning_param"):
                self._complete_learn(cc)
                return
            
            # Appliquer le mappage
            for mapped_cc, param in self.midi_mapping.items():
                if mapped_cc == cc:
                    # Normaliser la valeur selon le paramètre
                    if param == "pitch":
                        # -12 à +12 demi-tons
                        norm_value = (value / 127.0) * 24 - 12
                        self.pitch_slider.setValue(int(norm_value))
                    elif param == "speed":
                        # 0.5 à 2.0
                        norm_value = (value / 127.0) * 1.5 + 0.5
                        self.speed_slider.setValue(int(norm_value * 100))
                    elif param == "volume":
                        # 0.0 à 2.0
                        norm_value = (value / 127.0) * 2.0
                        self.volume_slider.setValue(int(norm_value * 100))
    
    def _toggle_learn_mode(self, enabled):
        """Active ou désactive le mode d'apprentissage"""
        if not enabled and hasattr(self, "learning_param"):
            delattr(self, "learning_param")
            self.current_param_label.setText("Aucun paramètre sélectionné")
    
    def _start_learn(self, param):
        """Démarre l'apprentissage d'un paramètre"""
        self.learn_checkbox.setChecked(True)
        self.learning_param = param
        self.current_param_label.setText(f"Attendant un contrôleur pour: {param}")
    
    def _complete_learn(self, cc):
        """Complète l'apprentissage avec le contrôleur spécifié"""
        if hasattr(self, "learning_param"):
            param = self.learning_param
            
            # Supprimer les mappages existants pour ce CC et ce paramètre
            for mapped_cc in list(self.midi_mapping.keys()):
                if mapped_cc == cc or self.midi_mapping[mapped_cc] == param:
                    del self.midi_mapping[mapped_cc]
            
            # Ajouter le nouveau mappage
            self.midi_mapping[cc] = param
            
            # Mettre à jour l'interface
            self.current_param_label.setText(f"CC {cc} assigné à {param}")
            
            # Désactiver le mode d'apprentissage
            self.learn_checkbox.setChecked(False)
            delattr(self, "learning_param")
    
    def _clear_mapping(self, param):
        """Efface le mappage pour un paramètre"""
        for cc in list(self.midi_mapping.keys()):
            if self.midi_mapping[cc] == param:
                del self.midi_mapping[cc]
        
        # Désactiver le mode d'apprentissage
        if hasattr(self, "learning_param") and self.learning_param == param:
            self.learn_checkbox.setChecked(False)
    
    def _update_parameter(self, param, value):
        """Met à jour un paramètre et son affichage"""
        if param == "pitch":
            self.pitch_value.setText(str(value))
        elif param == "speed":
            self.speed_value.setText(f"{value:.2f}")
        elif param == "volume":
            self.volume_value.setText(f"{value:.2f}")
        
        # Émettre le signal de changement de paramètre
        self.midi_parameter_changed.emit(param, float(value))
    
    def closeEvent(self, event):
        """Gère la fermeture de l'onglet"""
        # Déconnecter les périphériques MIDI
        self.midi_manager.disconnect_input()
        self.midi_manager.disconnect_output()
        
        # Continuer avec l'événement normal
        super().closeEvent(event) 