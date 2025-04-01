from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                            QPushButton, QTextEdit, QLabel, QMessageBox)
from PySide6.QtCore import Qt
from datetime import datetime
import os

class HistoryDialog(QDialog):
    def __init__(self, tts_engine, parent=None):
        super().__init__(parent)
        self.tts_engine = tts_engine
        self.setWindowTitle("Historique des conversions")
        self.setMinimumSize(800, 600)
        
        # Layout principal
        layout = QVBoxLayout(self)
        
        # Liste des entrées d'historique
        self.history_list = QListWidget()
        self.history_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.history_list)
        
        # Zone de texte pour afficher les détails
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        layout.addWidget(self.details_text)
        
        # Boutons
        button_layout = QHBoxLayout()
        
        self.play_button = QPushButton("Jouer")
        self.play_button.clicked.connect(self._play_audio)
        button_layout.addWidget(self.play_button)
        
        self.save_button = QPushButton("Sauvegarder l'audio")
        self.save_button.clicked.connect(self._save_audio)
        button_layout.addWidget(self.save_button)
        
        self.clear_button = QPushButton("Effacer l'historique")
        self.clear_button.clicked.connect(self._clear_history)
        button_layout.addWidget(self.clear_button)
        
        layout.addLayout(button_layout)
        
        # Charger l'historique
        self._load_history()
        
    def _load_history(self):
        """Charge l'historique des conversions."""
        self.history_list.clear()
        history_files = self.tts_engine.get_history()
        
        for file in history_files:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extraire la date du nom de fichier
                date_str = file.stem.split('_')[1]
                date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                self.history_list.addItem(f"{date.strftime('%d/%m/%Y %H:%M:%S')}")
                
    def _on_selection_changed(self, current, previous):
        """Met à jour les détails lors de la sélection d'une entrée."""
        if not current:
            return
            
        index = self.history_list.row(current)
        history_files = self.tts_engine.get_history()
        if index < len(history_files):
            with open(history_files[index], 'r', encoding='utf-8') as f:
                self.details_text.setText(f.read())
                
    def _play_audio(self):
        """Joue l'audio sélectionné."""
        current_item = self.history_list.currentItem()
        if not current_item:
            return
            
        index = self.history_list.row(current_item)
        history_files = self.tts_engine.get_history()
        if index < len(history_files):
            history_file = history_files[index]
            # Construire le chemin du fichier audio correspondant
            audio_file = history_file.parent / f"output_{history_file.stem.split('_')[1]}.wav"
            if audio_file.exists():
                try:
                    self.tts_engine.play_audio(str(audio_file))
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", str(e))
                    
    def _save_audio(self):
        """Sauvegarde l'audio sélectionné."""
        current_item = self.history_list.currentItem()
        if not current_item:
            return
            
        index = self.history_list.row(current_item)
        history_files = self.tts_engine.get_history()
        if index < len(history_files):
            history_file = history_files[index]
            audio_file = history_file.parent / f"output_{history_file.stem.split('_')[1]}.wav"
            if audio_file.exists():
                from PySide6.QtWidgets import QFileDialog
                target_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Sauvegarder l'audio",
                    "",
                    "Fichiers WAV (*.wav)"
                )
                if target_path:
                    try:
                        self.tts_engine.save_audio(str(audio_file), target_path)
                        QMessageBox.information(self, "Succès", "Audio sauvegardé avec succès!")
                    except Exception as e:
                        QMessageBox.critical(self, "Erreur", str(e))
                        
    def _clear_history(self):
        """Efface l'historique des conversions."""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Êtes-vous sûr de vouloir effacer tout l'historique ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.tts_engine.clear_history():
                self._load_history()
                self.details_text.clear()
                QMessageBox.information(self, "Succès", "Historique effacé avec succès!")
            else:
                QMessageBox.critical(self, "Erreur", "Impossible d'effacer l'historique") 