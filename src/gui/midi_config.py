"""
Module pour la configuration des mappings MIDI.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QComboBox, QTableWidget, QTableWidgetItem, QTabWidget,
                               QGroupBox, QTextEdit, QGridLayout, QLineEdit, QMessageBox)
from PySide6.QtCore import Qt, Signal, Slot

from utils.midi_mapping import MidiMapping

class MidiConfigDialog(QDialog):
    """Boîte de dialogue pour la configuration MIDI"""
    
    mapping_updated = Signal()  # Signal émis quand le mapping est modifié
    phrases_updated = Signal()  # Signal émis quand les phrases sont modifiées
    
    def __init__(self, midi_mapping, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration MIDI")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        self.midi_mapping = midi_mapping
        self.current_learning = None
        
        self._setup_ui()
        self._load_mappings()
        self._load_phrases()
        
    def _setup_ui(self):
        """Initialise l'interface utilisateur"""
        main_layout = QVBoxLayout(self)
        
        # Créer les onglets
        tabs = QTabWidget()
        
        # Onglet pour les mappings
        mapping_tab = QWidget()
        mapping_layout = QVBoxLayout(mapping_tab)
        
        # Sélection de la catégorie et fonction
        function_layout = QHBoxLayout()
        function_layout.addWidget(QLabel("Catégorie:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(list(self.midi_mapping.CATEGORIES.values()))
        function_layout.addWidget(self.category_combo)
        
        function_layout.addWidget(QLabel("Fonction:"))
        self.function_combo = QComboBox()
        function_layout.addWidget(self.function_combo)
        
        self.learn_button = QPushButton("Apprendre")
        self.learn_button.setCheckable(True)
        function_layout.addWidget(self.learn_button)
        
        # Connecter les signaux
        self.category_combo.currentIndexChanged.connect(self._update_functions)
        self.learn_button.toggled.connect(self._toggle_learn_mode)
        
        mapping_layout.addLayout(function_layout)
        
        # Table des mappings
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(4)
        self.mapping_table.setHorizontalHeaderLabels(["Type", "Canal", "Contrôleur", "Fonction"])
        self.mapping_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.mapping_table.setEditTriggers(QTableWidget.NoEditTriggers)
        mapping_layout.addWidget(self.mapping_table)
        
        # Boutons de gestion
        mapping_buttons = QHBoxLayout()
        self.delete_button = QPushButton("Supprimer")
        self.clear_all_button = QPushButton("Effacer tout")
        mapping_buttons.addWidget(self.delete_button)
        mapping_buttons.addWidget(self.clear_all_button)
        mapping_layout.addLayout(mapping_buttons)
        
        # Connecter les signaux
        self.delete_button.clicked.connect(self._delete_mapping)
        self.clear_all_button.clicked.connect(self._clear_all_mappings)
        
        # Onglet pour les phrases
        phrases_tab = QWidget()
        phrases_layout = QVBoxLayout(phrases_tab)
        
        # Groupe pour chaque phrase
        for i in range(1, 6):
            trigger_id = f"trigger_{i}"
            phrase_group = QGroupBox(f"Phrase {i}")
            phrase_layout = QGridLayout(phrase_group)
            
            # Texte de la phrase
            phrase_layout.addWidget(QLabel("Texte:"), 0, 0)
            text_edit = QTextEdit()
            text_edit.setMaximumHeight(80)
            text_edit.setObjectName(f"text_{trigger_id}")
            phrase_layout.addWidget(text_edit, 0, 1, 1, 2)
            
            # Voix pour la phrase
            phrase_layout.addWidget(QLabel("Voix:"), 1, 0)
            voice_combo = QComboBox()
            voice_combo.setObjectName(f"voice_{trigger_id}")
            phrase_layout.addWidget(voice_combo, 1, 1)
            
            # Test de la phrase
            test_button = QPushButton("Tester")
            test_button.setObjectName(f"test_{trigger_id}")
            phrase_layout.addWidget(test_button, 1, 2)
            
            phrases_layout.addWidget(phrase_group)
            
            # Connecter le signal
            test_button.clicked.connect(lambda checked, tid=trigger_id: self._test_phrase(tid))
            
        # Bouton pour sauvegarder les phrases
        save_phrases_button = QPushButton("Enregistrer les phrases")
        save_phrases_button.clicked.connect(self._save_phrases)
        phrases_layout.addWidget(save_phrases_button)
        
        # Ajouter les onglets
        tabs.addTab(mapping_tab, "Mappings MIDI")
        tabs.addTab(phrases_tab, "Phrases")
        
        main_layout.addWidget(tabs)
        
        # Boutons de dialogue
        dialog_buttons = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Annuler")
        dialog_buttons.addWidget(ok_button)
        dialog_buttons.addWidget(cancel_button)
        
        main_layout.addLayout(dialog_buttons)
        
        # Connecter les signaux
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        # Initialiser les fonctions
        self._update_functions(0)
        
    def _update_functions(self, index):
        """Met à jour la liste des fonctions selon la catégorie sélectionnée"""
        self.function_combo.clear()
        
        # Récupérer la catégorie
        categories = list(self.midi_mapping.CATEGORIES.keys())
        if index < 0 or index >= len(categories):
            return
            
        category = categories[index]
        
        # Ajouter les fonctions
        functions = self.midi_mapping.FUNCTIONS.get(category, {})
        for function_id, function_name in functions.items():
            self.function_combo.addItem(function_name, userData=function_id)
            
    def _toggle_learn_mode(self, checked):
        """Active ou désactive le mode d'apprentissage"""
        if checked:
            # Commencer l'apprentissage
            category_index = self.category_combo.currentIndex()
            function_index = self.function_combo.currentIndex()
            
            if category_index < 0 or function_index < 0:
                self.learn_button.setChecked(False)
                return
                
            category = list(self.midi_mapping.CATEGORIES.keys())[category_index]
            function = self.function_combo.currentData()
            
            if not function:
                self.learn_button.setChecked(False)
                return
                
            self.current_learning = (category, function)
            self.midi_mapping.start_learning(category, function)
            self.learn_button.setText("Attente...")
            
        else:
            # Arrêter l'apprentissage
            self.current_learning = None
            self.midi_mapping.stop_learning()
            self.learn_button.setText("Apprendre")
            
    def _load_mappings(self):
        """Charge les mappings dans la table"""
        self.mapping_table.setRowCount(0)
        
        row = 0
        for midi_type, mappings in self.midi_mapping.mappings.items():
            for identifier, function_id in mappings.items():
                self.mapping_table.insertRow(row)
                
                # Type
                self.mapping_table.setItem(row, 0, QTableWidgetItem(self.midi_mapping.TYPES.get(midi_type, midi_type)))
                
                # Canal et contrôleur
                if ":" in identifier:
                    channel, controller = identifier.split(":", 1)
                else:
                    channel, controller = "0", identifier
                    
                self.mapping_table.setItem(row, 1, QTableWidgetItem(channel))
                self.mapping_table.setItem(row, 2, QTableWidgetItem(controller))
                
                # Fonction
                category, function = self.midi_mapping.parse_function(function_id)
                if category and function:
                    category_name = self.midi_mapping.CATEGORIES.get(category, category)
                    function_name = self.midi_mapping.FUNCTIONS.get(category, {}).get(function, function)
                    function_text = f"{category_name} - {function_name}"
                else:
                    function_text = function_id
                    
                self.mapping_table.setItem(row, 3, QTableWidgetItem(function_text))
                
                # Stocker les données pour la suppression
                self.mapping_table.item(row, 0).setData(Qt.UserRole, midi_type)
                self.mapping_table.item(row, 1).setData(Qt.UserRole, identifier)
                
                row += 1
                
        self.mapping_table.resizeColumnsToContents()
        
    def _delete_mapping(self):
        """Supprime le mapping sélectionné"""
        selected_rows = self.mapping_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        midi_type = self.mapping_table.item(row, 0).data(Qt.UserRole)
        identifier = self.mapping_table.item(row, 1).data(Qt.UserRole)
        
        if self.midi_mapping.clear_mapping(midi_type, identifier):
            self.mapping_table.removeRow(row)
            self.mapping_updated.emit()
            
    def _clear_all_mappings(self):
        """Supprime tous les mappings"""
        reply = QMessageBox.question(
            self, 
            "Confirmation", 
            "Êtes-vous sûr de vouloir supprimer tous les mappings ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.midi_mapping.clear_all_mappings()
            self._load_mappings()
            self.mapping_updated.emit()
            
    def _load_phrases(self):
        """Charge les phrases dans les champs de texte"""
        for i in range(1, 6):
            trigger_id = f"trigger_{i}"
            phrase = self.midi_mapping.get_phrase(trigger_id)
            
            text_edit = self.findChild(QTextEdit, f"text_{trigger_id}")
            if text_edit:
                text_edit.setText(phrase.get("text", ""))
                
            # Les voix seront chargées par une méthode externe
            
    def _save_phrases(self):
        """Enregistre les phrases"""
        for i in range(1, 6):
            trigger_id = f"trigger_{i}"
            
            text_edit = self.findChild(QTextEdit, f"text_{trigger_id}")
            voice_combo = self.findChild(QComboBox, f"voice_{trigger_id}")
            
            if text_edit:
                text = text_edit.toPlainText()
                voice = voice_combo.currentData() if voice_combo else None
                
                self.midi_mapping.set_phrase(trigger_id, text, voice)
                
        self.phrases_updated.emit()
        QMessageBox.information(self, "Succès", "Les phrases ont été enregistrées.")
        
    def _test_phrase(self, trigger_id):
        """Teste une phrase"""
        phrase = self.midi_mapping.get_phrase(trigger_id)
        text = phrase.get("text", "")
        voice = phrase.get("voice")
        
        if not text:
            QMessageBox.warning(self, "Erreur", "Aucun texte défini pour cette phrase.")
            return
            
        # Émettre un signal pour tester la phrase (sera capturé par MainWindow)
        self.phrases_updated.emit()
        QMessageBox.information(self, "Test", f"Phrase: {text}\nVoix: {voice or 'Par défaut'}")
        
    def set_available_voices(self, voices):
        """Définit les voix disponibles dans les combos"""
        for i in range(1, 6):
            trigger_id = f"trigger_{i}"
            voice_combo = self.findChild(QComboBox, f"voice_{trigger_id}")
            
            if voice_combo:
                current_voice = None
                phrase = self.midi_mapping.get_phrase(trigger_id)
                if phrase:
                    current_voice = phrase.get("voice")
                    
                voice_combo.clear()
                voice_combo.addItem("Voix par défaut", userData=None)
                
                current_index = 0
                for i, (voice_id, voice_name) in enumerate(voices.items(), 1):
                    voice_combo.addItem(voice_name, userData=voice_id)
                    if voice_id == current_voice:
                        current_index = i
                        
                voice_combo.setCurrentIndex(current_index)
                
    def handle_midi_event(self, midi_type, channel, control, value):
        """Gère un événement MIDI pour l'apprentissage"""
        if not self.current_learning or not self.midi_mapping.learning_mode:
            return False
            
        category, function = self.current_learning
        
        if midi_type == "note":
            if self.midi_mapping.assign_note(control, channel):
                self._learning_complete()
                return True
                
        elif midi_type == "cc":
            if self.midi_mapping.assign_cc(control, channel):
                self._learning_complete()
                return True
                
        elif midi_type == "pb":
            if self.midi_mapping.assign_pb(channel):
                self._learning_complete()
                return True
                
        elif midi_type == "pc":
            if self.midi_mapping.assign_pc(control, channel):
                self._learning_complete()
                return True
                
        return False
        
    def _learning_complete(self):
        """Appelé quand l'apprentissage est terminé avec succès"""
        self.learn_button.setChecked(False)
        self.learn_button.setText("Apprendre")
        self._load_mappings()
        self.mapping_updated.emit()
        
    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre"""
        self.midi_mapping.stop_learning()
        self.learn_button.setChecked(False)
        event.accept() 