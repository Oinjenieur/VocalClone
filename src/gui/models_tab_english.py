"""
Module interface for voice model management.

This module provides a graphical interface for installing, managing,
and uninstalling different voice cloning models.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QListWidget, QListWidgetItem, QPushButton, 
                              QProgressBar, QComboBox, QMessageBox, QGroupBox,
                              QTextBrowser, QSplitter, QCheckBox, QLineEdit,
                              QFileDialog, QDialog, QGridLayout, QSpinBox,
                              QProgressDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread

import os
import sys
import threading
import logging
import time
import json

# Import the model manager
from core.voice_cloning import model_manager


class ModelDetailsWidget(QWidget):
    """Widget to display model details"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI configuration
        self.setup_ui()
        
        # Current model
        self.current_model_id = None
        
    def setup_ui(self):
        """Configure user interface"""
        layout = QVBoxLayout(self)
        
        # Model title
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # Model details
        self.details_browser = QTextBrowser()
        self.details_browser.setReadOnly(True)
        self.details_browser.setOpenExternalLinks(True)
        layout.addWidget(self.details_browser, 1)  # Stretch factor 1
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        self.install_button = QPushButton("Install")
        self.install_button.clicked.connect(self.install_model)
        buttons_layout.addWidget(self.install_button)
        
        self.uninstall_button = QPushButton("Uninstall")
        self.uninstall_button.clicked.connect(self.uninstall_model)
        buttons_layout.addWidget(self.uninstall_button)
        
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Progress message
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label) 

    def set_model(self, model_id):
        """Display model details"""
        self.current_model_id = model_id
        
        # Get model information
        model_info = model_manager.get_model_info(model_id)
        
        if model_info is None:
            self.title_label.setText("No model selected")
            self.details_browser.setText("Select a model from the list to view its details.")
            self.install_button.setEnabled(False)
            self.uninstall_button.setEnabled(False)
            return
            
        # Update interface
        self.title_label.setText(model_info.get("name", model_id))
        
        # Check if model is installed
        is_installed = model_id in model_manager.get_installed_models()
        
        # Prepare details text
        details = ""
        
        if is_installed:
            details += "<p><b>Status:</b> <span style='color: #4CAF50;'>Installed</span></p>"
            if "installed_at" in model_info:
                details += f"<p><b>Installed on:</b> {model_info['installed_at']}</p>"
        else:
            details += "<p><b>Status:</b> <span style='color: #F44336;'>Not installed</span></p>"
        
        if "description" in model_info:
            details += f"<p><b>Description:</b> {model_info['description']}</p>"
            
        if "languages" in model_info:
            languages = ", ".join(model_info["languages"])
            details += f"<p><b>Supported languages:</b> {languages}</p>"
            
        if "repo" in model_info:
            repo = model_info["repo"]
            details += f"<p><b>Repository:</b> <a href='https://github.com/{repo}'>{repo}</a></p>"
            
        if "version" in model_info:
            details += f"<p><b>Version:</b> {model_info['version']}</p>"
            
        if "type" in model_info and model_info["type"] == "cloned":
            details += "<p><b>Type:</b> Cloned voice</p>"
            if "model_name" in model_info:
                details += f"<p><b>Model used:</b> {model_info['model_name']}</p>"
            if "created_at" in model_info:
                details += f"<p><b>Created on:</b> {model_info['created_at']}</p>"
            
        # Update details text
        self.details_browser.setHtml(details)
        
        # Update buttons
        self.install_button.setEnabled(not is_installed)
        self.uninstall_button.setEnabled(is_installed)
        
    def install_model(self):
        """Install current model"""
        if self.current_model_id is None:
            return
            
        # Disable buttons during installation
        self.install_button.setEnabled(False)
        self.uninstall_button.setEnabled(False)
        
        # Show progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Preparing installation...")
        self.progress_label.setVisible(True)
        
        # Callback function for progress
        def progress_callback(value, message):
            self.progress_bar.setValue(value)
            self.progress_label.setText(message)
            
        # Function for installation
        def install_thread_func():
            try:
                success = model_manager.install_model(self.current_model_id, progress_callback)
                
                # Update interface after installation
                if success:
                    QMessageBox.information(self, "Installation successful", 
                                          f"Model {self.current_model_id} has been successfully installed.")
                    self.set_model(self.current_model_id)  # Refresh details
                else:
                    QMessageBox.critical(self, "Installation error", 
                                         f"Unable to install model {self.current_model_id}.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Installation error", 
                                    f"Error during model installation: {str(e)}")
                                    
            finally:
                # Hide progress bar
                self.progress_bar.setVisible(False)
                self.progress_label.setVisible(False)
                
                # Re-enable buttons
                self.set_model(self.current_model_id)  # Refresh details
                
        # Start installation thread
        thread = threading.Thread(target=install_thread_func)
        thread.daemon = True
        thread.start()
        
    def uninstall_model(self):
        """Uninstall current model"""
        if self.current_model_id is None:
            return
            
        # Ask for confirmation
        reply = QMessageBox.question(
            self, 
            "Confirmation",
            f"Are you sure you want to uninstall the model {self.current_model_id}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # Disable buttons during uninstallation
        self.install_button.setEnabled(False)
        self.uninstall_button.setEnabled(False)
        
        # Show progress
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Uninstalling...")
        self.progress_label.setVisible(True)
        
        # Function for uninstallation
        def uninstall_thread_func():
            try:
                success = model_manager.uninstall_model(self.current_model_id)
                
                # Update interface after uninstallation
                if success:
                    QMessageBox.information(self, "Uninstallation successful", 
                                          f"Model {self.current_model_id} has been successfully uninstalled.")
                    self.set_model(self.current_model_id)  # Refresh details
                else:
                    QMessageBox.critical(self, "Uninstallation error", 
                                         f"Unable to uninstall model {self.current_model_id}.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Uninstallation error", 
                                    f"Error during model uninstallation: {str(e)}")
                                    
            finally:
                # Hide progress bar
                self.progress_bar.setVisible(False)
                self.progress_label.setVisible(False)
                
                # Re-enable buttons
                self.set_model(self.current_model_id)  # Refresh details
                
        # Start uninstallation thread
        thread = threading.Thread(target=uninstall_thread_func)
        thread.daemon = True
        thread.start() 


class CloneVoiceDialog(QDialog):
    """Dialog for voice cloning configuration"""
    
    def __init__(self, audio_file=None, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Voice Cloning")
        self.setMinimumWidth(500)
        
        self.audio_file = audio_file
        
        # Available base models
        self.base_models = model_manager.get_base_cloning_models()
        
        # UI setup
        self.setup_ui()
        
        # Fill with default values
        if audio_file:
            self.audio_path_edit.setText(audio_file)
        
    def setup_ui(self):
        """Configure user interface"""
        layout = QVBoxLayout(self)
        
        # Audio file selection
        audio_group = QGroupBox("Voice Sample")
        audio_layout = QVBoxLayout(audio_group)
        
        # Description
        audio_layout.addWidget(QLabel("Select an audio file with a voice sample for cloning:"))
        
        # File selection
        file_layout = QHBoxLayout()
        
        self.audio_path_edit = QLineEdit()
        self.audio_path_edit.setReadOnly(True)
        file_layout.addWidget(self.audio_path_edit, 1)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_audio)
        file_layout.addWidget(browse_button)
        
        audio_layout.addLayout(file_layout)
        
        # Audio format requirements
        req_label = QLabel("Required format: WAV or MP3, 3-10 seconds, clear voice without background noise")
        req_label.setStyleSheet("color: #666; font-style: italic;")
        audio_layout.addWidget(req_label)
        
        layout.addWidget(audio_group)
        
        # Model parameters
        params_group = QGroupBox("Cloning Parameters")
        params_layout = QGridLayout(params_group)
        
        # Base model selection
        params_layout.addWidget(QLabel("Base Model:"), 0, 0)
        self.base_model_combo = QComboBox()
        
        # Add items to combobox
        for model_id, model_info in self.base_models.items():
            display_name = model_info.get("name", model_id)
            languages = ", ".join(model_info.get("languages", ["en"]))
            self.base_model_combo.addItem(f"{display_name} ({languages})", model_id)
            
        # Default to first item
        if self.base_model_combo.count() > 0:
            self.base_model_combo.setCurrentIndex(0)
            
        params_layout.addWidget(self.base_model_combo, 0, 1)
        
        # Voice name
        params_layout.addWidget(QLabel("Voice Name:"), 1, 0)
        self.voice_name_edit = QLineEdit()
        self.voice_name_edit.setPlaceholderText("My Custom Voice")
        params_layout.addWidget(self.voice_name_edit, 1, 1)
        
        # Gender selection
        params_layout.addWidget(QLabel("Gender:"), 2, 0)
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Male", "Female", "Other"])
        params_layout.addWidget(self.gender_combo, 2, 1)
        
        # Quality selection
        params_layout.addWidget(QLabel("Quality:"), 3, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Standard", "High", "Ultra"])
        self.quality_combo.setCurrentIndex(1)  # Default to High
        params_layout.addWidget(self.quality_combo, 3, 1)
        
        layout.addWidget(params_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def browse_audio(self):
        """Browse for audio file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Voice Sample",
            "",
            "Audio Files (*.wav *.mp3);;All Files (*.*)"
        )
        
        if file_path:
            # Check if file exists
            if not os.path.isfile(file_path):
                QMessageBox.warning(self, "File Error", "Selected file does not exist.")
                return
                
            # Check if it's a valid audio file (basic check)
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ('.wav', '.mp3'):
                QMessageBox.warning(self, "Format Error", "Selected file must be a WAV or MP3 file.")
                return
                
            # Update the field
            self.audio_file = file_path
            self.audio_path_edit.setText(file_path)
            
    def get_clone_config(self):
        """Get the cloning configuration"""
        if not self.audio_file:
            QMessageBox.warning(self, "Input Error", "Please select a voice sample file.")
            return None
            
        # Get voice name (generate one if empty)
        voice_name = self.voice_name_edit.text().strip()
        if not voice_name:
            # Generate a name based on the file
            base_name = os.path.basename(self.audio_file)
            name_part = os.path.splitext(base_name)[0]
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            voice_name = f"Voice_{name_part}_{timestamp}"
            
        # Get selected base model
        base_model = self.base_model_combo.currentData()
        if not base_model:
            QMessageBox.warning(self, "Model Error", "Please select a base model.")
            return None
            
        # Get gender
        gender = self.gender_combo.currentText().lower()
        
        # Get quality
        quality_map = {
            0: "standard",
            1: "high",
            2: "ultra"
        }
        quality = quality_map.get(self.quality_combo.currentIndex(), "high")
        
        # Return configuration
        return {
            "audio_file": self.audio_file,
            "voice_name": voice_name,
            "base_model": base_model,
            "gender": gender,
            "quality": quality
        } 


class ModelsTab(QWidget):
    """Tab for managing voice models"""
    
    model_changed = Signal(str)  # Signal emitted when a model is changed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI setup
        self.setup_ui()
        
        # Refresh models
        self.refresh_models()
        
    def setup_ui(self):
        """Configure user interface"""
        main_layout = QVBoxLayout(self)
        
        # Top buttons
        buttons_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh Models")
        self.refresh_button.clicked.connect(self.refresh_models)
        buttons_layout.addWidget(self.refresh_button)
        
        self.clone_button = QPushButton("Clone Voice")
        self.clone_button.clicked.connect(self.clone_voice)
        buttons_layout.addWidget(self.clone_button)
        
        self.import_button = QPushButton("Import Model")
        self.import_button.clicked.connect(self.import_model)
        buttons_layout.addWidget(self.import_button)
        
        buttons_layout.addStretch(1)
        
        main_layout.addLayout(buttons_layout)
        
        # Models view and details
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        # Models list (left)
        models_group = QGroupBox("Available Models")
        models_layout = QVBoxLayout(models_group)
        
        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search by name or language...")
        self.filter_edit.textChanged.connect(self.filter_models)
        filter_layout.addWidget(self.filter_edit)
        models_layout.addLayout(filter_layout)
        
        # List with categories
        self.models_list = QListWidget()
        self.models_list.setSelectionMode(QListWidget.SingleSelection)
        self.models_list.itemClicked.connect(self.select_model)
        models_layout.addWidget(self.models_list)
        
        # Type filter checkboxes
        type_layout = QHBoxLayout()
        self.show_standard = QCheckBox("Standard Models")
        self.show_standard.setChecked(True)
        self.show_standard.stateChanged.connect(self.refresh_models)
        type_layout.addWidget(self.show_standard)
        
        self.show_cloned = QCheckBox("Cloned Voices")
        self.show_cloned.setChecked(True)
        self.show_cloned.stateChanged.connect(self.refresh_models)
        type_layout.addWidget(self.show_cloned)
        
        self.show_experimental = QCheckBox("Experimental")
        self.show_experimental.setChecked(False)
        self.show_experimental.stateChanged.connect(self.refresh_models)
        type_layout.addWidget(self.show_experimental)
        
        models_layout.addLayout(type_layout)
        
        # Model details (right)
        self.details_widget = ModelDetailsWidget()
        
        # Add to splitter
        splitter.addWidget(models_group)
        splitter.addWidget(self.details_widget)
        
        # Set initial size of the models list (1/3 of width)
        splitter.setSizes([100, 200])
        
        main_layout.addWidget(splitter, 1)  # Stretch factor 1
        
    def refresh_models(self):
        """Refresh the list of models"""
        self.models_list.clear()
        
        # Get models from manager
        all_models = model_manager.get_available_models()
        installed_models = model_manager.get_installed_models()
        
        # Filter by type
        models_to_show = {}
        
        for model_id, model_info in all_models.items():
            # Check if it should be shown based on filters
            model_type = model_info.get("type", "standard")
            
            # Experimental models
            is_experimental = model_info.get("experimental", False)
            if is_experimental and not self.show_experimental.isChecked():
                continue
                
            # Cloned voices
            if model_type == "cloned" and not self.show_cloned.isChecked():
                continue
                
            # Standard models
            if model_type == "standard" and not self.show_standard.isChecked():
                continue
                
            # Add to filtered list
            models_to_show[model_id] = model_info
        
        # Create categories and sort models
        standard_models = []
        cloned_voices = []
        experimental_models = []
        
        for model_id, model_info in models_to_show.items():
            # Create item
            name = model_info.get("name", model_id)
            
            # Check if installed
            is_installed = model_id in installed_models
            
            # Add status indicator to name
            display_name = name
            if is_installed:
                display_name = f"✓ {name}"
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, model_id)  # Store model ID
            
            # Display in different color if installed
            if is_installed:
                item.setForeground(QColor(0, 128, 0))  # Green
            
            # Categorize
            model_type = model_info.get("type", "standard")
            is_experimental = model_info.get("experimental", False)
            
            if is_experimental:
                experimental_models.append(item)
            elif model_type == "cloned":
                cloned_voices.append(item)
            else:
                standard_models.append(item)
        
        # Add categories to list
        if cloned_voices and self.show_cloned.isChecked():
            self._add_category("Cloned Voices", cloned_voices)
            
        if standard_models and self.show_standard.isChecked():
            self._add_category("Standard Models", standard_models)
            
        if experimental_models and self.show_experimental.isChecked():
            self._add_category("Experimental Models", experimental_models)
            
        # Apply current filter
        self.filter_models(self.filter_edit.text())
        
        # Select first item if nothing is selected
        if self.models_list.currentItem() is None and self.models_list.count() > 0:
            # Find first real item (not a header)
            for i in range(self.models_list.count()):
                item = self.models_list.item(i)
                if item and item.data(Qt.UserRole) is not None:
                    self.models_list.setCurrentItem(item)
                    self.select_model(item)
                    break
    
    def _add_category(self, category_name, items):
        """Add a category with items to the list"""
        if not items:
            return
            
        # Add header item
        header = QListWidgetItem(f"--- {category_name.upper()} ---")
        header.setFlags(Qt.NoItemFlags)  # Not selectable
        header.setBackground(QColor(230, 230, 230))
        header.setForeground(QColor(80, 80, 80))
        self.models_list.addItem(header)
        
        # Add model items
        for item in items:
            self.models_list.addItem(item)
    
    def filter_models(self, filter_text):
        """Filter the models list based on text"""
        filter_text = filter_text.lower()
        
        for i in range(self.models_list.count()):
            item = self.models_list.item(i)
            
            # Headers are always shown
            if item.flags() == Qt.NoItemFlags:
                item.setHidden(False)
                continue
                
            # Get model info
            model_id = item.data(Qt.UserRole)
            if not model_id:
                continue
                
            model_info = model_manager.get_model_info(model_id)
            if not model_info:
                continue
                
            # Search in various fields
            name = model_info.get("name", "").lower()
            description = model_info.get("description", "").lower()
            languages = [lang.lower() for lang in model_info.get("languages", [])]
            
            # Show if any field matches
            show = (filter_text in name or 
                    filter_text in description or
                    any(filter_text in lang for lang in languages))
                    
            item.setHidden(not show)
            
        # Hide empty categories
        for i in range(self.models_list.count()):
            item = self.models_list.item(i)
            
            # Check if this is a header
            if item.flags() == Qt.NoItemFlags:
                # Check if all items in this category are hidden
                all_hidden = True
                j = i + 1
                
                while j < self.models_list.count():
                    next_item = self.models_list.item(j)
                    
                    # Stop if we reach another header
                    if next_item.flags() == Qt.NoItemFlags:
                        break
                        
                    if not next_item.isHidden():
                        all_hidden = False
                        break
                        
                    j += 1
                    
                # Hide header if all items are hidden
                item.setHidden(all_hidden)
    
    def select_model(self, item):
        """Handle model selection from the list"""
        if not item or item.flags() == Qt.NoItemFlags:
            return  # Ignore headers
            
        model_id = item.data(Qt.UserRole)
        if model_id:
            self.details_widget.set_model(model_id)
            
    def clone_voice(self):
        """Launch voice cloning process"""
        dialog = CloneVoiceDialog(parent=self)
        
        if dialog.exec():
            # Get configuration
            config = dialog.get_clone_config()
            if not config:
                return
                
            # Show progress dialog
            progress = QProgressDialog("Cloning voice...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Voice Cloning")
            progress.setMinimumDuration(500)  # Show after 500ms
            progress.setWindowModality(Qt.WindowModal)
            
            # Callback for progress updates
            def update_progress(value, message):
                if progress.wasCanceled():
                    return False
                progress.setValue(value)
                progress.setLabelText(message)
                QApplication.processEvents()
                return True
                
            # Clone in a thread
            result = {"success": False, "model_id": None, "error": None}
            
            def clone_thread():
                try:
                    result["success"], result["model_id"] = model_manager.clone_voice(
                        config["audio_file"],
                        config["voice_name"],
                        config["base_model"],
                        quality=config["quality"],
                        progress_callback=update_progress
                    )
                except Exception as e:
                    result["error"] = str(e)
                    result["success"] = False
                
                # Close progress dialog
                progress.setValue(100)
                
            # Start thread
            thread = threading.Thread(target=clone_thread)
            thread.daemon = True
            thread.start()
            
            # Show progress dialog
            progress.exec()
            
            # Process result
            if result["success"]:
                QMessageBox.information(self, "Voice Cloning", 
                                      f"Voice successfully cloned with ID: {result['model_id']}")
                                      
                # Refresh and select the new model
                self.refresh_models()
                
                # Find and select the new model
                for i in range(self.models_list.count()):
                    item = self.models_list.item(i)
                    if item and item.data(Qt.UserRole) == result["model_id"]:
                        self.models_list.setCurrentItem(item)
                        self.select_model(item)
                        break
                        
                # Emit model changed signal
                self.model_changed.emit(result["model_id"])
            else:
                error_msg = result["error"] or "Unknown error during voice cloning"
                QMessageBox.critical(self, "Voice Cloning Error", error_msg)
    
    def import_model(self):
        """Import a model from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Voice Model",
            "",
            "Model Files (*.zip *.pth *.pt);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        # Ask for model name
        model_name, ok = QMessageBox.QInputDialog.getText(
            self, 
            "Model Name", 
            "Enter a name for the imported model:",
            text=os.path.basename(file_path).split('.')[0]
        )
        
        if not ok or not model_name:
            return
            
        # Show progress
        progress = QProgressDialog("Importing model...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Model Import")
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(10)
        
        # Import in a thread
        result = {"success": False, "model_id": None, "error": None}
        
        def import_thread():
            try:
                result["success"], result["model_id"] = model_manager.import_model(
                    file_path, model_name
                )
            except Exception as e:
                result["error"] = str(e)
                result["success"] = False
            
            # Close progress dialog
            progress.setValue(100)
            
        # Start thread
        thread = threading.Thread(target=import_thread)
        thread.daemon = True
        thread.start()
        
        # Show progress dialog
        progress.exec()
        
        # Process result
        if result["success"]:
            QMessageBox.information(self, "Model Import", 
                                  f"Model successfully imported with ID: {result['model_id']}")
                                  
            # Refresh models
            self.refresh_models()
        else:
            error_msg = result["error"] or "Unknown error during model import"
            QMessageBox.critical(self, "Import Error", error_msg) 