"""
Module d'interface pour la gestion des modèles de voix.

Ce module fournit une interface graphique pour installer, gérer, 
et désinstaller les différents modèles de clonage vocal.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QListWidget, QListWidgetItem, QPushButton, 
                              QProgressBar, QComboBox, QMessageBox, QGroupBox,
                              QTextBrowser, QSplitter, QCheckBox, QLineEdit,
                              QFileDialog, QDialog, QGridLayout, QSpinBox,
                              QProgressDialog)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread

import os
import sys
import threading
import logging
import time
import json

# Importer le gestionnaire de modèles
from core.voice_cloning import model_manager


class ModelDetailsWidget(QWidget):
    """Widget pour afficher les détails d'un modèle"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration de l'interface
        self.setup_ui()
        
        # Modèle actuel
        self.current_model_id = None
        
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Titre du modèle
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # Détails du modèle
        self.details_browser = QTextBrowser()
        self.details_browser.setReadOnly(True)
        self.details_browser.setOpenExternalLinks(True)
        layout.addWidget(self.details_browser, 1)  # Stretch factor 1
        
        # Boutons d'action
        buttons_layout = QHBoxLayout()
        
        self.install_button = QPushButton("Installer")
        self.install_button.clicked.connect(self.install_model)
        buttons_layout.addWidget(self.install_button)
        
        self.uninstall_button = QPushButton("Désinstaller")
        self.uninstall_button.clicked.connect(self.uninstall_model)
        buttons_layout.addWidget(self.uninstall_button)
        
        layout.addLayout(buttons_layout)
        
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
        
    def set_model(self, model_id):
        """Affiche les détails d'un modèle"""
        self.current_model_id = model_id
        
        # Récupérer les informations sur le modèle
        model_info = model_manager.get_model_info(model_id)
        
        if model_info is None:
            self.title_label.setText("Aucun modèle sélectionné")
            self.details_browser.setText("Sélectionnez un modèle dans la liste pour voir ses détails.")
            self.install_button.setEnabled(False)
            self.uninstall_button.setEnabled(False)
            return
            
        # Mettre à jour l'interface
        self.title_label.setText(model_info.get("name", model_id))
        
        # Vérifier si le modèle est installé
        is_installed = model_id in model_manager.get_installed_models()
        
        # Préparer le texte des détails
        details = ""
        
        if is_installed:
            details += "<p><b>Statut:</b> <span style='color: #4CAF50;'>Installé</span></p>"
            if "installed_at" in model_info:
                details += f"<p><b>Installé le:</b> {model_info['installed_at']}</p>"
        else:
            details += "<p><b>Statut:</b> <span style='color: #F44336;'>Non installé</span></p>"
        
        if "description" in model_info:
            details += f"<p><b>Description:</b> {model_info['description']}</p>"
            
        if "languages" in model_info:
            languages = ", ".join(model_info["languages"])
            details += f"<p><b>Langues supportées:</b> {languages}</p>"
            
        if "repo" in model_info:
            repo = model_info["repo"]
            details += f"<p><b>Dépôt:</b> <a href='https://github.com/{repo}'>{repo}</a></p>"
            
        if "version" in model_info:
            details += f"<p><b>Version:</b> {model_info['version']}</p>"
            
        if "type" in model_info and model_info["type"] == "cloned":
            details += "<p><b>Type:</b> Voix clonée</p>"
            if "model_name" in model_info:
                details += f"<p><b>Modèle utilisé:</b> {model_info['model_name']}</p>"
            if "created_at" in model_info:
                details += f"<p><b>Créé le:</b> {model_info['created_at']}</p>"
            
        # Mettre à jour le texte des détails
        self.details_browser.setHtml(details)
        
        # Mettre à jour les boutons
        self.install_button.setEnabled(not is_installed)
        self.uninstall_button.setEnabled(is_installed)
        
    def install_model(self):
        """Installe le modèle actuel"""
        if self.current_model_id is None:
            return
            
        # Désactiver les boutons pendant l'installation
        self.install_button.setEnabled(False)
        self.uninstall_button.setEnabled(False)
        
        # Afficher la barre de progression
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Préparation de l'installation...")
        self.progress_label.setVisible(True)
        
        # Fonction de rappel pour la progression
        def progress_callback(value, message):
            self.progress_bar.setValue(value)
            self.progress_label.setText(message)
            
        # Fonction pour l'installation
        def install_thread_func():
            try:
                success = model_manager.install_model(self.current_model_id, progress_callback)
                
                # Mettre à jour l'interface après l'installation
                if success:
                    QMessageBox.information(self, "Installation réussie", 
                                          f"Le modèle {self.current_model_id} a été installé avec succès.")
                    self.set_model(self.current_model_id)  # Rafraîchir les détails
                else:
                    QMessageBox.critical(self, "Erreur d'installation", 
                                         f"Impossible d'installer le modèle {self.current_model_id}.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Erreur d'installation", 
                                    f"Erreur lors de l'installation du modèle: {str(e)}")
                                    
            finally:
                # Cacher la barre de progression
                self.progress_bar.setVisible(False)
                self.progress_label.setVisible(False)
                
                # Réactiver les boutons
                self.set_model(self.current_model_id)  # Rafraîchir les détails
                
        # Démarrer le thread d'installation
        thread = threading.Thread(target=install_thread_func)
        thread.daemon = True
        thread.start()
        
    def uninstall_model(self):
        """Désinstalle le modèle actuel"""
        if self.current_model_id is None:
            return
            
        # Demander confirmation
        reply = QMessageBox.question(
            self, 
            "Confirmation",
            f"Voulez-vous vraiment désinstaller le modèle {self.current_model_id} ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            # Désinstaller le modèle
            success = model_manager.uninstall_model(self.current_model_id)
            
            if success:
                QMessageBox.information(self, "Désinstallation réussie", 
                                      f"Le modèle {self.current_model_id} a été désinstallé avec succès.")
                self.set_model(self.current_model_id)  # Rafraîchir les détails
            else:
                QMessageBox.critical(self, "Erreur de désinstallation", 
                                   f"Impossible de désinstaller le modèle {self.current_model_id}.")
                                   
        except Exception as e:
            QMessageBox.critical(self, "Erreur de désinstallation", 
                               f"Erreur lors de la désinstallation du modèle: {str(e)}")


class CloneVoiceDialog(QDialog):
    """Dialogue pour cloner une voix"""
    
    def __init__(self, audio_file=None, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Cloner une voix")
        self.resize(500, 400)
        
        self.audio_file = audio_file
        self.setup_ui()
        
        # Configurer les valeurs initiales
        if self.audio_file:
            self.audio_path_input.setText(self.audio_file)
        
        # Logger
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialisation du dialogue de clonage vocal")
        
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        # Layout principal
        layout = QVBoxLayout(self)
        
        # Section du fichier audio
        audio_group = QGroupBox("Fichier Audio Source")
        audio_layout = QHBoxLayout(audio_group)
        
        self.audio_path_input = QLineEdit()
        self.audio_path_input.setReadOnly(True)
        audio_layout.addWidget(self.audio_path_input, 1)
        
        browse_button = QPushButton("Parcourir")
        browse_button.clicked.connect(self.browse_audio)
        audio_layout.addWidget(browse_button)
        
        layout.addWidget(audio_group)
        
        # Section de configuration du modèle
        model_group = QGroupBox("Configuration du Modèle")
        model_layout = QVBoxLayout(model_group)
        
        # Nom de la voix
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nom de la voix:"))
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_input)
        model_layout.addLayout(name_layout)
        
        # Sélection du moteur
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("Moteur de synthèse:"))
        self.engine_combo = QComboBox()
        
        # Ajouter les moteurs disponibles
        for engine_id, engine_info in model_manager.get_available_models().items():
            self.engine_combo.addItem(engine_info.get("name", engine_id), engine_id)
            
        engine_layout.addWidget(self.engine_combo)
        model_layout.addLayout(engine_layout)
        
        # Langues disponibles
        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel("Langue principale:"))
        self.language_combo = QComboBox()
        
        # Liste des langues
        self.languages = {
            "fr": "Français",
            "en": "Anglais",
            "es": "Espagnol",
            "de": "Allemand",
            "it": "Italien",
            "zh": "Chinois",
            "ja": "Japonais",
            "pt": "Portugais",
            "ru": "Russe"
        }
        
        # Ajouter les langues
        for lang_code, lang_name in self.languages.items():
            self.language_combo.addItem(lang_name, lang_code)
            
        # Sélectionner le français par défaut
        index = self.language_combo.findData("fr")
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
            
        language_layout.addWidget(self.language_combo)
        model_layout.addLayout(language_layout)
        
        # Options avancées
        advanced_layout = QGridLayout()
        
        # Qualité d'entraînement
        advanced_layout.addWidget(QLabel("Qualité d'entraînement:"), 0, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Standard", "standard")
        self.quality_combo.addItem("Haute", "high")
        advanced_layout.addWidget(self.quality_combo, 0, 1)
        
        # Durée minimale d'audio
        advanced_layout.addWidget(QLabel("Durée minimale (secondes):"), 1, 0)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 300)
        self.duration_spin.setValue(30)
        advanced_layout.addWidget(self.duration_spin, 1, 1)
        
        model_layout.addLayout(advanced_layout)
        layout.addWidget(model_group)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        self.clone_button = QPushButton("Cloner la voix")
        self.clone_button.clicked.connect(self.accept)
        self.clone_button.setEnabled(self.audio_file is not None)
        buttons_layout.addWidget(self.clone_button)
        
        layout.addLayout(buttons_layout)
        
    def browse_audio(self):
        """Ouvre un dialogue pour sélectionner un fichier audio"""
        try:
            self.logger.info("Ouverture du dialogue de sélection de fichier audio")
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Sélectionner un fichier audio",
                "",
                "Fichiers audio (*.wav *.mp3 *.ogg *.flac);;Tous les fichiers (*.*)"
            )
            
            if file_path:
                self.logger.info(f"Fichier audio sélectionné: {file_path}")
                self.audio_file = file_path
                self.audio_path_input.setText(file_path)
                self.clone_button.setEnabled(True)
                
                # Auto-remplir le nom de la voix à partir du nom du fichier
                import os
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                if not self.name_input.text():
                    self.name_input.setText(base_name)
                    self.logger.info(f"Nom de voix auto-rempli: {base_name}")
            else:
                self.logger.info("Aucun fichier audio sélectionné")
        except Exception as e:
            self.logger.error(f"Erreur lors de la sélection du fichier audio: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la sélection du fichier: {str(e)}")
    
    def get_clone_config(self):
        """Retourne la configuration pour le clonage de voix"""
        try:
            if not self.audio_file:
                self.logger.error("Tentative de récupération de configuration sans fichier audio")
                return None
                
            # Récupérer les valeurs
            name = self.name_input.text().strip()
            if not name:
                self.logger.warning("Nom de modèle vide, génération d'un nom par défaut")
                import os
                from datetime import datetime
                base_name = os.path.splitext(os.path.basename(self.audio_file))[0]
                name = f"{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
            engine_id = self.engine_combo.currentData()
            language = self.language_combo.currentData()
            quality = self.quality_combo.currentData()
            min_duration = self.duration_spin.value()
            
            self.logger.info(f"Configuration de clonage: name={name}, engine={engine_id}, language={language}, quality={quality}, min_duration={min_duration}")
            
            return {
                "name": name,
                "engine": engine_id,
                "audio_file": self.audio_file,
                "language": language,
                "quality": quality,
                "min_duration": min_duration,
                "type": "cloned",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            self.logger.error(f"Erreur lors de la création de la configuration de clonage: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Erreur de configuration: {str(e)}")
            return None


class ModelsTab(QWidget):
    """Onglet de gestion des modèles de voix"""
    
    model_changed = Signal(str)  # Signal émis quand un modèle est modifié
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configurer l'interface utilisateur
        self.setup_ui()
        
        # Charge la liste des modèles disponibles
        self.refresh_models()
        
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Titre
        title_label = QLabel("Gestion des Modèles de Voix")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Créer un splitter horizontal
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Panneau de gauche : modèles disponibles
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        available_label = QLabel("Modèles disponibles")
        available_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(available_label)
        
        # Liste des modèles disponibles
        self.available_model_list = QListWidget()
        self.available_model_list.itemClicked.connect(self._on_available_model_selected)
        left_layout.addWidget(self.available_model_list)
        
        # Boutons pour les modèles disponibles
        available_buttons = QHBoxLayout()
        
        self.refresh_button = QPushButton("Rafraîchir")
        self.refresh_button.clicked.connect(self.refresh_models)
        available_buttons.addWidget(self.refresh_button)
        
        self.install_button = QPushButton("Installer")
        self.install_button.setEnabled(False)
        self.install_button.clicked.connect(self._install_selected_model)
        available_buttons.addWidget(self.install_button)
        
        left_layout.addLayout(available_buttons)
        
        main_splitter.addWidget(left_panel)
        
        # Panneau central : modèles installés
        central_panel = QWidget()
        central_layout = QVBoxLayout(central_panel)
        
        installed_label = QLabel("Modèles installés")
        installed_label.setStyleSheet("font-weight: bold;")
        central_layout.addWidget(installed_label)
        
        # Liste des modèles installés
        self.installed_model_list = QListWidget()
        self.installed_model_list.itemClicked.connect(self._on_installed_model_selected)
        central_layout.addWidget(self.installed_model_list)
        
        # Boutons pour les modèles installés
        installed_buttons = QHBoxLayout()
        
        self.uninstall_button = QPushButton("Désinstaller")
        self.uninstall_button.setEnabled(False)
        self.uninstall_button.clicked.connect(self._uninstall_selected_model)
        installed_buttons.addWidget(self.uninstall_button)
        
        central_layout.addLayout(installed_buttons)
        
        main_splitter.addWidget(central_panel)
        
        # Panneau de droite : détails du modèle
        self.details_panel = ModelDetailsWidget()
        main_splitter.addWidget(self.details_panel)
        
        # Ajouter le splitter au layout principal
        layout.addWidget(main_splitter, 1)
        
        # Section d'entraînement de modèle
        training_group = QGroupBox("Entraînement de modèle vocal")
        training_layout = QVBoxLayout(training_group)
        
        # Description
        training_desc = QLabel("Entraînez un nouveau modèle vocal ou affinez un modèle existant")
        training_desc.setWordWrap(True)
        training_layout.addWidget(training_desc)
        
        # Options d'entraînement
        training_options = QGridLayout()
        
        # Modèle de base
        training_options.addWidget(QLabel("Modèle de base:"), 0, 0)
        self.base_model_combo = QComboBox()
        self.base_model_combo.addItem("Coqui TTS", "coqui_tts")
        self.base_model_combo.addItem("OpenVoice", "openvoice_v2")
        training_options.addWidget(self.base_model_combo, 0, 1)
        
        # Nombre d'époques
        training_options.addWidget(QLabel("Époques:"), 0, 2)
        self.epochs_spinner = QSpinBox()
        self.epochs_spinner.setRange(10, 1000)
        self.epochs_spinner.setValue(100)
        training_options.addWidget(self.epochs_spinner, 0, 3)
        
        # Dossier de données
        training_options.addWidget(QLabel("Dossier de données:"), 1, 0)
        self.data_path_layout = QHBoxLayout()
        self.data_path_edit = QLineEdit()
        self.data_path_edit.setReadOnly(True)
        self.data_path_layout.addWidget(self.data_path_edit)
        
        self.data_path_button = QPushButton("Parcourir")
        self.data_path_button.clicked.connect(self._select_data_folder)
        self.data_path_layout.addWidget(self.data_path_button)
        
        training_options.addLayout(self.data_path_layout, 1, 1, 1, 3)
        
        # Nom du modèle
        training_options.addWidget(QLabel("Nom du modèle:"), 2, 0)
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("Nom du modèle à entraîner")
        training_options.addWidget(self.model_name_edit, 2, 1, 1, 3)
        
        training_layout.addLayout(training_options)
        
        # Boutons d'entraînement
        training_buttons = QHBoxLayout()
        
        self.start_training_button = QPushButton("Démarrer l'entraînement")
        self.start_training_button.clicked.connect(self._start_training)
        training_buttons.addWidget(self.start_training_button)
        
        self.stop_training_button = QPushButton("Arrêter")
        self.stop_training_button.setEnabled(False)
        self.stop_training_button.clicked.connect(self._stop_training)
        training_buttons.addWidget(self.stop_training_button)
        
        training_layout.addLayout(training_buttons)
        
        # Barre de progression de l'entraînement
        self.training_progress = QProgressBar()
        self.training_progress.setRange(0, 100)
        self.training_progress.setValue(0)
        training_layout.addWidget(self.training_progress)
        
        # Ajouter la section d'entraînement au layout principal
        layout.addWidget(training_group)
        
        # Gestion des événements
        self.is_training = False
        self.training_thread = None
        
    def _select_data_folder(self):
        """Sélectionne le dossier contenant les données d'entraînement"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le dossier de données d'entraînement",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.data_path_edit.setText(folder)
            
    def _start_training(self):
        """Démarre l'entraînement du modèle"""
        # Vérifier les paramètres
        if not self.data_path_edit.text():
            QMessageBox.warning(self, "Dossier manquant", 
                              "Veuillez sélectionner un dossier de données d'entraînement")
            return
            
        model_name = self.model_name_edit.text().strip()
        if not model_name:
            QMessageBox.warning(self, "Nom manquant", 
                              "Veuillez saisir un nom pour le modèle")
            return
            
        # Récupérer les paramètres
        base_model = self.base_model_combo.currentData()
        epochs = self.epochs_spinner.value()
        data_folder = self.data_path_edit.text()
        
        # Désactiver les contrôles pendant l'entraînement
        self._set_training_controls_enabled(False)
        
        # Démarrer l'entraînement dans un thread séparé
        self.is_training = True
        self.training_thread = threading.Thread(
            target=self._training_thread_func,
            args=(base_model, model_name, data_folder, epochs),
            daemon=True
        )
        self.training_thread.start()
        
    def _training_thread_func(self, base_model, model_name, data_folder, epochs):
        """Fonction d'entraînement exécutée dans un thread séparé"""
        try:
            # Simuler l'entraînement
            for epoch in range(epochs):
                if not self.is_training:
                    break
                    
                # Mettre à jour la progression
                progress = int((epoch + 1) / epochs * 100)
                QTimer.singleShot(0, lambda p=progress: self.training_progress.setValue(p))
                
                # Simuler un temps de calcul
                time.sleep(0.1)
                
            # Créer le modèle entraîné
            if self.is_training:
                # Créer un ID unique pour le modèle
                model_id = f"trained_{model_name.lower().replace(' ', '_')}_{int(time.time())}"
                
                # Créer un dossier pour le modèle
                model_path = os.path.join(model_manager.models_dir, model_id)
                os.makedirs(model_path, exist_ok=True)
                
                # Créer un fichier de configuration
                config = {
                    "name": model_name,
                    "model_type": base_model,
                    "languages": ["fr", "en"],  # Supposer une prise en charge du français et de l'anglais
                    "description": f"Modèle personnalisé entraîné sur {data_folder}",
                    "repo": "local",
                    "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "version": "1.0.0",
                    "type": "trained"  # Marquer comme modèle entraîné
                }
                
                # Enregistrer la configuration
                config_file = os.path.join(model_path, "config.json")
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                    
                # Ajouter à la liste des modèles installés
                model_manager.installed_models[model_id] = config
                
                # Rafraîchir la liste des modèles
                QTimer.singleShot(0, self.refresh_models)
                
                # Informer l'utilisateur
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, 
                    "Entraînement terminé", 
                    f"Le modèle '{model_name}' a été entraîné avec succès."
                ))
                
            else:
                # Informer l'utilisateur que l'entraînement a été arrêté
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, 
                    "Entraînement arrêté", 
                    "L'entraînement a été arrêté."
                ))
                
        except Exception as e:
            # Afficher un message d'erreur
            QTimer.singleShot(0, lambda: QMessageBox.critical(
                self, 
                "Erreur d'entraînement", 
                f"Une erreur est survenue pendant l'entraînement:\n{str(e)}"
            ))
            
        finally:
            # Réactiver les contrôles
            self.is_training = False
            QTimer.singleShot(0, lambda: self._set_training_controls_enabled(True))
            
    def _set_training_controls_enabled(self, enabled):
        """Active ou désactive les contrôles d'entraînement"""
        self.base_model_combo.setEnabled(enabled)
        self.epochs_spinner.setEnabled(enabled)
        self.data_path_button.setEnabled(enabled)
        self.model_name_edit.setEnabled(enabled)
        self.start_training_button.setEnabled(enabled)
        self.stop_training_button.setEnabled(not enabled)
        
    def _stop_training(self):
        """Arrête l'entraînement en cours"""
        if self.is_training:
            self.is_training = False
            
            # Désactiver le bouton d'arrêt pendant l'arrêt
            self.stop_training_button.setEnabled(False)
            self.stop_training_button.setText("Arrêt en cours...")
        
    def refresh_models(self):
        """Rafraîchit la liste des modèles"""
        self.available_model_list.clear()
        self.installed_model_list.clear()
        
        # Ajouter les modèles installés
        installed_models = model_manager.get_installed_models()
        for model_id, model_info in installed_models.items():
            item = QListWidgetItem(model_info.get("name", model_id))
            item.setData(Qt.UserRole, model_id)
            
            # Style différent pour les voix clonées
            if model_info.get("type") == "cloned":
                item.setForeground(Qt.green)
                
            item.setToolTip(f"Modèle installé: {model_id}")
            self.installed_model_list.addItem(item)
            
        # Ajouter les modèles disponibles mais non installés
        available_models = model_manager.get_available_models()
        for model_id, model_info in available_models.items():
            if model_id not in installed_models:
                item = QListWidgetItem(model_info.get("name", model_id))
                item.setData(Qt.UserRole, model_id)
                item.setForeground(Qt.gray)
                item.setToolTip(f"Modèle disponible: {model_id}")
                self.available_model_list.addItem(item)
                
        # Aucun modèle sélectionné par défaut
        self.details_panel.set_model(None)
        
    def _on_available_model_selected(self, item):
        """Gère la sélection d'un modèle dans la liste des modèles disponibles"""
        model_id = item.data(Qt.UserRole)
        self.details_panel.set_model(model_id)
        
    def _on_installed_model_selected(self, item):
        """Gère la sélection d'un modèle dans la liste des modèles installés"""
        model_id = item.data(Qt.UserRole)
        self.details_panel.set_model(model_id)
        
    def _install_selected_model(self):
        """Installe le modèle sélectionné"""
        selected_item = self.available_model_list.currentItem()
        if selected_item:
            model_id = selected_item.data(Qt.UserRole)
            self.details_panel.set_model(model_id)
            
    def _uninstall_selected_model(self):
        """Désinstalle le modèle sélectionné"""
        selected_item = self.installed_model_list.currentItem()
        if selected_item:
            model_id = selected_item.data(Qt.UserRole)
            self.details_panel.set_model(model_id)
        
    def clone_voice(self, audio_file=None):
        """Ouvre le dialogue de clonage de voix"""
        logger = logging.getLogger(__name__)
        logger.info(f"Ouverture du dialogue de clonage de voix, fichier audio: {audio_file}")
        
        # Créer le dialogue
        dialog = CloneVoiceDialog(audio_file, self)
        
        # Afficher le dialogue
        if dialog.exec():
            # Récupérer la configuration
            config = dialog.get_clone_config()
            if not config:
                logger.error("Aucune configuration de clonage valide obtenue")
                return
                
            # Désactiver l'interface pendant le clonage
            self.setEnabled(False)
            
            # Créer la fenêtre de progression
            progress_dialog = QProgressDialog("Clonage de la voix en cours...", "Annuler", 0, 100, self)
            progress_dialog.setWindowTitle("Clonage vocal")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setAutoClose(False)
            progress_dialog.setAutoReset(False)
            progress_dialog.show()
            
            # Créer une classe de thread Qt pour le clonage
            class CloneVoiceThread(QThread):
                finished = Signal(bool, str, str)  # success, message, model_id
                progress = Signal(int, str)  # value, message
                
                def __init__(self, config, parent=None):
                    super().__init__(parent)
                    self.config = config
                    self.model_id = None
                    
                def run(self):
                    try:
                        logger.info(f"Début du clonage avec configuration: {self.config}")
                        
                        # Générer un identifiant unique pour le modèle
                        from datetime import datetime
                        
                        # Créer un identifiant unique basé sur le nom et la date
                        name_slug = self.config["name"].lower().replace(" ", "_")
                        self.model_id = f"cloned_{name_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        
                        # Créer le dossier pour le modèle
                        model_path = os.path.join(model_manager.models_dir, self.model_id)
                        os.makedirs(model_path, exist_ok=True)
                        logger.info(f"Dossier de modèle créé: {model_path}")
                        
                        # Créer le dossier pour les échantillons
                        samples_dir = os.path.join(model_path, "samples")
                        os.makedirs(samples_dir, exist_ok=True)
                        
                        # Copier le fichier audio dans le dossier des échantillons
                        import shutil
                        audio_filename = os.path.basename(self.config["audio_file"])
                        sample_path = os.path.join(samples_dir, audio_filename)
                        shutil.copy2(self.config["audio_file"], sample_path)
                        logger.info(f"Échantillon audio copié: {sample_path}")
                        
                        # Mettre à jour la progression
                        self.progress.emit(20, "Préparation du modèle...")
                        
                        # Ajouter des informations supplémentaires à la configuration
                        self.config["id"] = self.model_id
                        self.config["type"] = "cloned"
                        self.config["sample_path"] = sample_path
                        self.config["model_path"] = model_path
                        
                        # Simuler l'entraînement du modèle (à remplacer par l'implémentation réelle)
                        self.progress.emit(30, "Extraction des caractéristiques vocales...")
                        QThread.sleep(1)
                        
                        self.progress.emit(50, "Entraînement du modèle...")
                        QThread.sleep(1)
                        
                        self.progress.emit(70, "Optimisation...")
                        QThread.sleep(1)
                        
                        self.progress.emit(90, "Finalisation...")
                        
                        # Enregistrer la configuration
                        config_path = os.path.join(model_path, "config.json")
                        with open(config_path, 'w', encoding='utf-8') as f:
                            json.dump(self.config, f, ensure_ascii=False, indent=2)
                        logger.info(f"Configuration enregistrée: {config_path}")
                        
                        # Rafraîchir la liste des modèles
                        model_manager.installed_models = model_manager._load_installed_models()
                        
                        # Vérifier que le modèle est bien chargé
                        if self.model_id not in model_manager.installed_models:
                            logger.error(f"Le modèle {self.model_id} n'a pas été correctement chargé après la création")
                            
                            # Essayer de charger manuellement le modèle
                            try:
                                with open(config_path, 'r', encoding='utf-8') as f:
                                    model_config = json.load(f)
                                    model_manager.installed_models[self.model_id] = model_config
                                    logger.info(f"Modèle {self.model_id} chargé manuellement avec succès")
                            except Exception as e:
                                logger.error(f"Échec du chargement manuel du modèle {self.model_id}: {e}", exc_info=True)
                        
                        self.progress.emit(100, "Clonage terminé avec succès!")
                        self.finished.emit(True, "Clonage terminé avec succès", self.model_id)
                        
                    except Exception as e:
                        logger.error(f"Erreur lors du clonage de la voix: {e}", exc_info=True)
                        
                        # Si un dossier de modèle a été créé, le supprimer en cas d'erreur
                        if self.model_id:
                            try:
                                model_path = os.path.join(model_manager.models_dir, self.model_id)
                                if os.path.exists(model_path):
                                    shutil.rmtree(model_path)
                                    logger.info(f"Dossier de modèle supprimé après erreur: {model_path}")
                            except Exception as cleanup_error:
                                logger.error(f"Erreur lors du nettoyage du dossier du modèle: {cleanup_error}", exc_info=True)
                        
                        self.finished.emit(False, f"Erreur: {str(e)}", "")
            
            # Créer et démarrer le thread
            clone_thread = CloneVoiceThread(config, self)
            
            # Connecter les signaux
            clone_thread.progress.connect(lambda value, message: progress_dialog.setLabelText(message) or progress_dialog.setValue(value))
            
            clone_thread.finished.connect(lambda success, message, model_id: (
                progress_dialog.setLabelText(message),
                progress_dialog.setValue(100),
                self.setEnabled(True),
                self.model_changed.emit(model_id) if success else None,
                QTimer.singleShot(2000, progress_dialog.close)
            ))
            
            # Démarrer le thread
            clone_thread.start()
        else:
            logger.info("Dialogue de clonage annulé par l'utilisateur") 