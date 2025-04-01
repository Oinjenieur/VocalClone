from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                              QListWidget, QListWidgetItem, QFileDialog, QProgressBar, QMessageBox,
                              QGroupBox, QGridLayout, QLineEdit)
from PySide6.QtCore import Qt, Signal, QSize, QThread
from PySide6.QtGui import QIcon
import os
import shutil
import soundfile as sf
import time

class CloneVoiceThread(QThread):
    """Thread pour le clonage de voix à partir d'un fichier audio"""
    finished = Signal(str)  # Signal avec le nom du modèle
    progress = Signal(int)  # Signal avec la progression (0-100)
    error = Signal(str)     # Signal avec le message d'erreur
    
    def __init__(self, tts_engine, audio_file, output_model, model_name):
        super().__init__()
        self.tts_engine = tts_engine
        self.audio_file = audio_file
        self.output_model = output_model
        self.model_name = model_name
        self.running = True
        
    def run(self):
        """Processus de clonage de voix"""
        try:
            print(f"\n🔄 Clonage de la voix à partir de {self.audio_file}...")
            print(f"📂 Dossier de sortie: {self.output_model}")
            
            # Vérifier si le moteur TTS a la fonction de clonage
            if hasattr(self.tts_engine, 'clone_voice') and callable(self.tts_engine.clone_voice):
                # Vérifier si le fichier audio existe
                if not os.path.exists(self.audio_file):
                    raise FileNotFoundError(f"Le fichier audio {self.audio_file} n'existe pas")
                
                # Vérifier si le dossier de sortie existe
                os.makedirs(os.path.dirname(self.output_model), exist_ok=True)
                
                # Tester que le fichier audio est valide
                try:
                    data, sample_rate = sf.read(self.audio_file)
                    duration = len(data) / sample_rate
                    print(f"✓ Fichier audio valide: {duration:.2f} secondes, {sample_rate} Hz")
                    
                    # Vérifier que l'audio est assez long
                    if duration < 3:
                        raise ValueError("L'enregistrement est trop court (minimum 3 secondes requis)")
                        
                    # Cloner la voix avec le moteur TTS
                    for i in range(10):  # Simuler la progression
                        if not self.running:
                            return
                        self.progress.emit((i+1) * 10)
                        time.sleep(0.5)  # Simuler un traitement
                        
                    success = self.tts_engine.clone_voice(self.audio_file, self.output_model)
                    
                    if success:
                        self.finished.emit(self.model_name)
                    else:
                        raise RuntimeError("Le clonage de voix a échoué")
                        
                except Exception as e:
                    raise ValueError(f"Erreur lors de la lecture du fichier audio: {str(e)}")
            else:
                # Implémentation simulée pour les tests
                print("🔄 Simulation du clonage de voix...")
                
                # Vérifier si le dossier de sortie existe
                os.makedirs(os.path.dirname(self.output_model), exist_ok=True)
                
                # Simuler un traitement long
                for i in range(10):
                    if not self.running:
                        return
                    time.sleep(0.5)
                    self.progress.emit((i+1) * 10)
                    print(f"Progression: {(i+1) * 10}%")
                
                # Copier le fichier audio comme modèle
                target_file = f"{self.output_model}.wav"
                shutil.copy(self.audio_file, target_file)
                
                print(f"✅ Modèle créé: {target_file}")
                self.finished.emit(self.model_name)
                
        except Exception as e:
            error_msg = f"Erreur lors du clonage de voix: {str(e)}"
            print(f"❌ {error_msg}")
            self.error.emit(error_msg)
            
    def stop(self):
        """Arrêter le thread"""
        self.running = False

class UserVoiceItem(QListWidgetItem):
    """Item de liste pour représenter une voix utilisateur"""
    
    def __init__(self, name, model_path, date=None):
        super().__init__(name)
        self.model_path = model_path
        self.date = date
        self.setIcon(QIcon("resources/icons/user_voice.png"))

class UserVoiceManager(QWidget):
    """Widget pour gérer les voix utilisateur (importation et clonage)"""
    
    voice_selected = Signal(str, str)  # Nom, chemin du modèle
    voice_cloned = Signal(str, str)    # Nom, chemin du modèle
    voice_imported = Signal(str, str)  # Nom, chemin du modèle
    voice_deleted = Signal(str)        # Nom du modèle supprimé
    
    def __init__(self, tts_engine, parent=None):
        super().__init__(parent)
        self.tts_engine = tts_engine
        self.user_voices = {}  # Dictionnaire des voix utilisateur (nom -> chemin)
        
        # Chemin vers le dossier des modèles utilisateur
        self.user_models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "user")
        os.makedirs(self.user_models_dir, exist_ok=True)
        
        self._setup_ui()
        self._load_user_voices()
        
    def _setup_ui(self):
        """Initialisation de l'interface utilisateur"""
        main_layout = QVBoxLayout(self)
        
        # Titre
        title_label = QLabel("Mes Voix")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2ea043;")
        main_layout.addWidget(title_label)
        
        # Groupe pour la liste des voix
        voices_group = QGroupBox("Voix disponibles")
        voices_layout = QVBoxLayout(voices_group)
        
        # Liste des voix
        self.voices_list = QListWidget()
        self.voices_list.setMinimumHeight(150)
        self.voices_list.itemClicked.connect(self._on_voice_selected)
        
        # Boutons d'action pour les voix
        voices_buttons_layout = QHBoxLayout()
        self.select_voice_btn = QPushButton("Utiliser")
        self.select_voice_btn.setEnabled(False)
        self.select_voice_btn.clicked.connect(self._on_use_voice)
        
        self.delete_voice_btn = QPushButton("Supprimer")
        self.delete_voice_btn.setEnabled(False)
        self.delete_voice_btn.clicked.connect(self._on_delete_voice)
        
        voices_buttons_layout.addWidget(self.select_voice_btn)
        voices_buttons_layout.addWidget(self.delete_voice_btn)
        
        voices_layout.addWidget(self.voices_list)
        voices_layout.addLayout(voices_buttons_layout)
        
        # Groupe pour l'importation de voix
        import_group = QGroupBox("Importer un fichier audio")
        import_layout = QGridLayout(import_group)
        
        # Étiquette explicative
        import_info = QLabel("Importez un fichier audio pour créer un modèle de voix. " 
                           "Pour de meilleurs résultats, utilisez un fichier WAV ou FLAC "
                           "de haute qualité, avec une durée minimale de 10 secondes de parole claire.")
        import_info.setWordWrap(True)
        import_layout.addWidget(import_info, 0, 0, 1, 3)
        
        # Nom du modèle
        import_layout.addWidget(QLabel("Nom du modèle:"), 1, 0)
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("Nom pour votre modèle de voix")
        import_layout.addWidget(self.model_name_edit, 1, 1, 1, 2)
        
        # Sélection de fichier
        import_layout.addWidget(QLabel("Fichier audio:"), 2, 0)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("Sélectionnez un fichier audio")
        import_layout.addWidget(self.file_path_edit, 2, 1)
        
        self.browse_btn = QPushButton("Parcourir")
        self.browse_btn.clicked.connect(self._on_browse_file)
        import_layout.addWidget(self.browse_btn, 2, 2)
        
        # Bouton d'importation
        self.import_btn = QPushButton("Créer un modèle de voix")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._on_import_voice)
        import_layout.addWidget(self.import_btn, 3, 0, 1, 3)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        import_layout.addWidget(self.progress_bar, 4, 0, 1, 3)
        
        # Ajouter les groupes au layout principal
        main_layout.addWidget(voices_group)
        main_layout.addWidget(import_group)
        
    def _load_user_voices(self):
        """Charge la liste des voix utilisateur"""
        self.voices_list.clear()
        self.user_voices.clear()
        
        if not os.path.exists(self.user_models_dir):
            return
            
        for item in os.listdir(self.user_models_dir):
            item_path = os.path.join(self.user_models_dir, item)
            
            # Vérifier s'il s'agit d'un dossier ou d'un fichier WAV
            if os.path.isdir(item_path) or (os.path.isfile(item_path) and item.endswith(".wav")):
                # Formater le nom pour l'affichage
                if item.startswith("voice_clone_"):
                    display_name = item.replace("voice_clone_", "")
                    if "_" in display_name:
                        parts = display_name.split("_")
                        if len(parts) >= 2:
                            date_part = parts[0]
                            time_part = parts[1]
                            if len(date_part) == 8 and len(time_part) >= 4:
                                # Formater la date (YYYYMMDD_HHMMSS)
                                date_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}"
                                display_name = f"Voix du {date_str}"
                else:
                    display_name = item.replace("_", " ").replace(".wav", "")
                
                # Ajouter à la liste
                voice_item = UserVoiceItem(display_name, item_path)
                self.voices_list.addItem(voice_item)
                self.user_voices[display_name] = item_path
        
        # Mettre à jour l'interface
        has_voices = len(self.user_voices) > 0
        if not has_voices:
            self.voices_list.addItem("Aucune voix disponible")
            
    def _on_voice_selected(self, item):
        """Appelé quand une voix est sélectionnée dans la liste"""
        if isinstance(item, UserVoiceItem):
            self.select_voice_btn.setEnabled(True)
            self.delete_voice_btn.setEnabled(True)
        else:
            self.select_voice_btn.setEnabled(False)
            self.delete_voice_btn.setEnabled(False)
            
    def _on_use_voice(self):
        """Utilise la voix sélectionnée"""
        selected_items = self.voices_list.selectedItems()
        if selected_items and isinstance(selected_items[0], UserVoiceItem):
            item = selected_items[0]
            self.voice_selected.emit(item.text(), item.model_path)
            
    def _on_delete_voice(self):
        """Supprime la voix sélectionnée"""
        selected_items = self.voices_list.selectedItems()
        if selected_items and isinstance(selected_items[0], UserVoiceItem):
            item = selected_items[0]
            
            # Demander confirmation
            reply = QMessageBox.question(
                self, 
                "Supprimer la voix", 
                f"Êtes-vous sûr de vouloir supprimer la voix '{item.text()}'?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    # Supprimer le fichier ou le dossier
                    if os.path.isdir(item.model_path):
                        shutil.rmtree(item.model_path)
                    else:
                        os.remove(item.model_path)
                        
                    # Mettre à jour la liste
                    self.user_voices.pop(item.text(), None)
                    row = self.voices_list.row(item)
                    self.voices_list.takeItem(row)
                    
                    # Émettre le signal
                    self.voice_deleted.emit(item.text())
                    
                    # Mettre à jour l'interface
                    if self.voices_list.count() == 0:
                        self.voices_list.addItem("Aucune voix disponible")
                        self.select_voice_btn.setEnabled(False)
                        self.delete_voice_btn.setEnabled(False)
                        
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Erreur lors de la suppression: {str(e)}")
                    
    def _on_browse_file(self):
        """Ouvre un dialogue pour sélectionner un fichier audio"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier audio",
            "",
            "Fichiers audio (*.wav *.mp3 *.flac *.ogg);;Tous les fichiers (*.*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            
            # Extraire un nom par défaut du nom de fichier
            base_name = os.path.basename(file_path)
            name, _ = os.path.splitext(base_name)
            if not self.model_name_edit.text():
                self.model_name_edit.setText(name)
                
            # Activer le bouton d'importation
            self._update_import_button()
                
    def _update_import_button(self):
        """Met à jour l'état du bouton d'importation"""
        has_file = bool(self.file_path_edit.text() and os.path.exists(self.file_path_edit.text()))
        has_name = bool(self.model_name_edit.text())
        
        self.import_btn.setEnabled(has_file and has_name)
            
    def _on_import_voice(self):
        """Importe un fichier audio pour créer un modèle de voix"""
        file_path = self.file_path_edit.text()
        model_name = self.model_name_edit.text()
        
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un fichier audio valide.")
            return
            
        if not model_name:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un nom pour votre modèle.")
            return
            
        try:
            # Vérifier le format du fichier
            try:
                data, sample_rate = sf.read(file_path)
                duration = len(data) / sample_rate
                
                if duration < 3:
                    QMessageBox.warning(
                        self, 
                        "Fichier trop court", 
                        "L'enregistrement doit durer au moins 3 secondes. "
                        f"Durée actuelle: {duration:.1f} secondes."
                    )
                    return
                    
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Erreur de fichier", 
                    f"Impossible de lire le fichier audio: {str(e)}"
                )
                return
                
            # Créer un nom de fichier valide
            safe_name = model_name.replace(" ", "_").lower()
            model_dir = os.path.join(self.user_models_dir, f"user_{safe_name}")
            
            # Vérifier si le modèle existe déjà
            if os.path.exists(model_dir):
                reply = QMessageBox.question(
                    self,
                    "Modèle existant",
                    f"Un modèle nommé '{model_name}' existe déjà. Voulez-vous le remplacer?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    return
                    
                # Supprimer l'ancien modèle
                if os.path.isdir(model_dir):
                    shutil.rmtree(model_dir)
                elif os.path.exists(model_dir + ".wav"):
                    os.remove(model_dir + ".wav")
                    
            # Préparer l'interface
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.import_btn.setEnabled(False)
            self.browse_btn.setEnabled(False)
            
            # Lancer le clonage dans un thread
            self.clone_thread = CloneVoiceThread(
                self.tts_engine,
                file_path,
                model_dir,
                model_name
            )
            
            # Connexions
            self.clone_thread.progress.connect(self.progress_bar.setValue)
            self.clone_thread.finished.connect(self._on_import_finished)
            self.clone_thread.error.connect(self._on_import_error)
            
            # Démarrer
            self.clone_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'importation: {str(e)}")
            self.progress_bar.setVisible(False)
            self.import_btn.setEnabled(True)
            self.browse_btn.setEnabled(True)
            
    def _on_import_finished(self, model_name):
        """Appelé quand l'importation est terminée"""
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        
        QMessageBox.information(
            self,
            "Importation réussie",
            f"Le modèle '{model_name}' a été créé avec succès."
        )
        
        # Mettre à jour la liste des voix
        self._load_user_voices()
        
        # Réinitialiser les champs
        self.file_path_edit.clear()
        self.model_name_edit.clear()
        
        # Signal
        model_path = self.user_voices.get(model_name, "")
        if model_path:
            self.voice_imported.emit(model_name, model_path)
            
    def _on_import_error(self, error_message):
        """Appelé en cas d'erreur lors de l'importation"""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        
        QMessageBox.critical(
            self,
            "Erreur d'importation",
            f"Erreur lors de la création du modèle: {error_message}"
        ) 