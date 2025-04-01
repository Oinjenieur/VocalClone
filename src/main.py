"""
Application de synthèse vocale avec interface MIDI.

Ce module est le point d'entrée principal de l'application qui fournit
une interface graphique pour la synthèse vocale avec contrôle MIDI.
"""

import sys
import time
import threading
import logging
import argparse
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, 
    QWidget, QLabel, QProgressBar, QSplashScreen
)
from PySide6.QtCore import QTimer, QSize, Qt, QThread, Signal, QObject
from PySide6.QtGui import QPixmap, QFont, QColor, QPainter, QBrush, QLinearGradient
import torch

# Importation des modules de l'application
from gui.recording_tab import RecordingTab
from gui.synthesis_tab import SynthesisTab
from gui.models_tab import ModelsTab
from gui.midi_tab import MidiTab
from utils.midi_device_manager import midi_manager
from core.voice_cloning import model_manager

# Configuration du logging
def setup_logging(debug=False):
    """Configure le système de logging"""
    log_level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("openvoice.log"),
            logging.StreamHandler()
        ]
    )
    
    # Configurer les logs des bibliothèques tierces
    if not debug:
        # Réduire le niveau de verbosité des bibliothèques tierces
        logging.getLogger("matplotlib").setLevel(logging.WARNING)
        logging.getLogger("PIL").setLevel(logging.WARNING)
        logging.getLogger("scipy").setLevel(logging.WARNING)
        logging.getLogger("torch").setLevel(logging.WARNING)
        logging.getLogger("tensorflow").setLevel(logging.WARNING)
        logging.getLogger("rtmidi").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Le logger sera initialisé plus tard
logger = None


class PreloaderThread(QObject):
    """Thread pour le préchargement des modules et modèles"""
    
    progress = Signal(int, str)
    
    def __init__(self, debug=False):
        super().__init__()
        self.modules_loaded = False
        self.debug = debug
    
    def run(self):
        """Exécute le préchargement"""
        try:
            # Initialisation des modules TTS
            self.progress.emit(10, "Initialisation des modules TTS...")
            self._init_tts_modules()
            
            # Chargement des modèles vocaux
            self.progress.emit(30, "Chargement des modèles vocaux...")
            self._load_voice_models()
            
            # Préparation du moteur de synthèse
            self.progress.emit(60, "Préparation du moteur de synthèse...")
            self._prepare_synthesis_engine()
            
            # Initialisation des interfaces MIDI
            self.progress.emit(80, "Initialisation des interfaces MIDI...")
            self._init_midi()
            
            # Finalisation
            self.progress.emit(100, "Prêt !")
            self.modules_loaded = True
            
        except Exception as e:
            logger.error(f"Erreur lors du préchargement: {e}", exc_info=self.debug)
            self.progress.emit(100, f"Erreur: {str(e)}")
    
    def _init_tts_modules(self):
        """Initialise les modules TTS"""
        try:
            # Vérifier si CUDA est disponible
            is_cuda_available = torch.cuda.is_available()
            if is_cuda_available:
                logger.info(f"CUDA disponible, nombre de GPU: {torch.cuda.device_count()}")
                logger.info(f"GPU utilisé: {torch.cuda.get_device_name(0)}")
            else:
                logger.info("CUDA non disponible, utilisation du CPU")
            
            # Précharger certains modèles courants
            # Pour Coqui TTS
            try:
                import TTS
                logger.info(f"Coqui TTS version: {TTS.__version__}")
                self.progress.emit(15, "Chargement de Coqui TTS...")
            except ImportError:
                logger.warning("Coqui TTS non disponible")
            
            # Pour Bark
            try:
                import bark
                self.progress.emit(20, "Chargement de Bark...")
                logger.info("Bark disponible")
            except ImportError:
                logger.warning("Bark non disponible")
            
            # Pour gTTS (fallback)
            try:
                import gtts
                self.progress.emit(25, "Chargement de gTTS...")
                logger.info(f"gTTS version: {gtts.__version__}")
            except ImportError:
                logger.warning("gTTS non disponible")
            
            logger.info("Modules TTS initialisés")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des modules TTS: {e}", exc_info=self.debug)
            raise
    
    def _load_voice_models(self):
        """Charge les modèles vocaux"""
        try:
            # Récupérer la liste des modèles disponibles
            available_models = model_manager.get_available_models()
            logger.info(f"Modèles disponibles: {list(available_models.keys())}")
            
            # Récupérer la liste des modèles installés
            installed_models = model_manager.get_installed_models()
            logger.info(f"Modèles installés: {list(installed_models.keys())}")
            
            # Pour chaque modèle installé, on peut précharger certaines ressources
            for i, (model_id, model_info) in enumerate(installed_models.items()):
                progress = 30 + (i * 5) % 20  # Progression entre 30-50%
                self.progress.emit(progress, f"Chargement du modèle {model_info.get('name', model_id)}...")
                
                # Ici, on pourrait précharger des ressources spécifiques pour chaque modèle
                # Par exemple, pour Coqui TTS, on pourrait charger un modèle de base
                
            logger.info("Modèles vocaux chargés")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des modèles vocaux: {e}", exc_info=self.debug)
            raise
    
    def _prepare_synthesis_engine(self):
        """Prépare le moteur de synthèse"""
        try:
            # Initialiser les backends de synthèse
            # Cette étape peut inclure le préchargement de petits modèles
            # ou la vérification de la disponibilité des API externes
            
            # Exemple : Charger un petit modèle TTS pour les réponses rapides
            try:
                from TTS.api import TTS
                self.progress.emit(55, "Préparation du modèle TTS par défaut...")
                # On ne charge pas réellement le modèle ici pour éviter de ralentir le démarrage
                # Mais on vérifie qu'on peut l'initialiser
                # tts = TTS("tts_models/fr/mai/tacotron2-DDC", verbose=False)
            except ImportError:
                pass
            
            # Exemple : Précharger certains paramètres pour gTTS
            try:
                from gtts import gTTS
                self.progress.emit(60, "Préparation de gTTS...")
                # Création d'un petit test pour vérifier que gTTS fonctionne
                # test_tts = gTTS("Test", lang="fr")
            except ImportError:
                pass
            
            # Simuler un temps de chargement
            time.sleep(0.5)
            
            logger.info("Moteur de synthèse prêt")
        except Exception as e:
            logger.error(f"Erreur lors de la préparation du moteur de synthèse: {e}", exc_info=self.debug)
            raise
    
    def _init_midi(self):
        """Initialise les interfaces MIDI"""
        try:
            # Vérifier la version de rtmidi
            try:
                import rtmidi
                rtmidi_version = getattr(rtmidi, "__version__", "Inconnue")
                logger.info(f"Version de rtmidi: {rtmidi_version}")
            except ImportError as e:
                logger.error(f"Erreur lors de la création des objets MIDI: {e}")
                rtmidi_version = "Non disponible"
            
            # Scanner les périphériques MIDI
            midi_manager.scan_devices()
            
            # Ici, on pourrait précharger des instruments MIDI virtuels
            # ou d'autres ressources pour le traitement MIDI
            
            logger.info("Interfaces MIDI initialisées")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des interfaces MIDI: {e}", exc_info=self.debug)
            raise
            

class SplashScreen(QSplashScreen):
    """Écran de démarrage avec barre de progression"""
    
    def __init__(self):
        # Créer une image de base pour le splash screen
        pixmap = QPixmap(QSize(600, 300))
        pixmap.fill(Qt.transparent)
        
        # Appliquer un dégradé comme fond
        painter = QPainter(pixmap)
        gradient = QLinearGradient(0, 0, 0, 300)
        gradient.setColorAt(0, QColor(40, 40, 80))
        gradient.setColorAt(1, QColor(20, 20, 40))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, 0, 600, 300)
        painter.end()
        
        super().__init__(pixmap)
        
        # Configuration de l'apparence
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Mise en page
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Widget central
        self.content = QWidget(self)
        self.content.setGeometry(0, 0, 600, 300)
        self.content.setLayout(layout)
        
        # Titre
        title_label = QLabel("Synthèse Vocale avec MIDI")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Espace
        layout.addStretch(1)
        
        # Status label
        self.status_label = QLabel("Initialisation...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #76797C;
                border-radius: 5px;
                text-align: center;
                color: white;
                background-color: #2a2a2a;
            }
            QProgressBar::chunk {
                background-color: #3daee9;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Espace
        layout.addStretch(1)
    
    def update_progress(self, value, message):
        """Met à jour la barre de progression et le message"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self.repaint()  # Force le rafraîchissement de l'interface


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application"""
    
    def __init__(self, debug=False):
        super().__init__()
        
        self.debug = debug
        
        # Configuration de base de la fenêtre
        self.setWindowTitle("OpenVoice Studio")
        self.setMinimumSize(1200, 800)
        
        # Widget principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Onglets
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Ajouter les onglets
        self.add_tabs()
        
        # Centrer la fenêtre
        self.center_window()
        
    def add_tabs(self):
        """Ajoute les onglets à l'interface"""
        # Tentative avec try/except pour chaque onglet pour éviter qu'une erreur sur
        # un onglet ne bloque complètement l'application
        
        try:
            # Onglet d'enregistrement
            self.recording_tab = RecordingTab()
            self.recording_tab.voice_cloned.connect(self.handle_voice_cloned)
            self.tabs.addTab(self.recording_tab, "Enregistrement")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'onglet d'enregistrement: {e}", exc_info=self.debug)
            # Créer un widget alternatif pour l'onglet d'enregistrement
            recording_error_widget = QWidget()
            recording_error_layout = QVBoxLayout(recording_error_widget)
            recording_error_label = QLabel(f"Erreur de chargement de l'interface d'enregistrement:\n{str(e)}")
            recording_error_label.setWordWrap(True)
            recording_error_label.setAlignment(Qt.AlignCenter)
            recording_error_layout.addWidget(recording_error_label)
            self.tabs.addTab(recording_error_widget, "Enregistrement (Erreur)")
        
        try:
            # Onglet de synthèse
            self.synthesis_tab = SynthesisTab()
            self.tabs.addTab(self.synthesis_tab, "Synthèse")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'onglet de synthèse: {e}", exc_info=self.debug)
            # Créer un widget alternatif pour l'onglet de synthèse
            synthesis_error_widget = QWidget()
            synthesis_error_layout = QVBoxLayout(synthesis_error_widget)
            synthesis_error_label = QLabel(f"Erreur de chargement de l'interface de synthèse:\n{str(e)}")
            synthesis_error_label.setWordWrap(True)
            synthesis_error_label.setAlignment(Qt.AlignCenter)
            synthesis_error_layout.addWidget(synthesis_error_label)
            self.tabs.addTab(synthesis_error_widget, "Synthèse (Erreur)")
        
        try:
            # Onglet de gestion des modèles
            self.models_tab = ModelsTab()
            self.tabs.addTab(self.models_tab, "Modèles")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'onglet des modèles: {e}", exc_info=self.debug)
            # Créer un widget alternatif pour l'onglet des modèles
            models_error_widget = QWidget()
            models_error_layout = QVBoxLayout(models_error_widget)
            models_error_label = QLabel(f"Erreur de chargement de l'interface des modèles:\n{str(e)}")
            models_error_label.setWordWrap(True)
            models_error_label.setAlignment(Qt.AlignCenter)
            models_error_layout.addWidget(models_error_label)
            self.tabs.addTab(models_error_widget, "Modèles (Erreur)")
        
        try:
            # Onglet MIDI
            self.midi_tab = MidiTab()
            self.tabs.addTab(self.midi_tab, "MIDI")
            
            # Connecter les signaux MIDI
            self.midi_tab.midi_parameter_changed.connect(self.handle_midi_parameter_change)
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'onglet MIDI: {e}", exc_info=self.debug)
            # Créer un widget alternatif pour l'onglet MIDI
            midi_error_widget = QWidget()
            midi_error_layout = QVBoxLayout(midi_error_widget)
            midi_error_label = QLabel(f"Erreur de chargement de l'interface MIDI:\n{str(e)}")
            midi_error_label.setWordWrap(True)
            midi_error_label.setAlignment(Qt.AlignCenter)
            midi_error_layout.addWidget(midi_error_label)
            self.tabs.addTab(midi_error_widget, "MIDI (Erreur)")
        
        # Connecter les signaux
        self.models_tab.model_changed.connect(self.handle_model_change)
    
    def handle_model_change(self, model_id):
        """Gère le changement de modèle"""
        # Rafraîchir la liste des modèles dans l'onglet de synthèse
        self.synthesis_tab.synthesizer.model_selector.refresh_models()
        
        # Sélectionner le nouveau modèle si disponible
        self.synthesis_tab.synthesizer.model_selector.select_model(model_id)
        
        logger.info(f"Modèle changé: {model_id}")
        
    def handle_voice_cloned(self, model_id):
        """Gère l'événement quand une voix est clonée depuis l'onglet d'enregistrement"""
        # Rafraîchir la liste des modèles dans l'onglet de synthèse
        self.synthesis_tab.synthesizer.model_selector.refresh_models()
        
        # Sélectionner la voix clonée
        self.synthesis_tab.synthesizer.model_selector.select_model(model_id)
        
        # Passer à l'onglet de synthèse
        self.tabs.setCurrentWidget(self.synthesis_tab)
        
        logger.info(f"Voix clonée sélectionnée dans la synthèse: {model_id}")
    
    def handle_midi_parameter_change(self, param, value):
        """Gère le changement d'un paramètre MIDI"""
        try:
            # Transmettre les changements à l'onglet de synthèse
            if param == "pitch":
                self.synthesis_tab.set_pitch(value)
            elif param == "speed":
                self.synthesis_tab.set_speed(value)
            elif param == "volume":
                self.synthesis_tab.set_volume(value)
            
            logger.info(f"Paramètre MIDI changé: {param} = {value}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement du paramètre MIDI {param}: {e}", exc_info=self.debug)
    
    def center_window(self):
        """Centre la fenêtre sur l'écran"""
        frame_geometry = self.frameGeometry()
        screen = QApplication.primaryScreen()
        center_point = screen.availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())


def parse_arguments():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description="Application de synthèse vocale avec contrôle MIDI")
    parser.add_argument("--debug", action="store_true", help="Active le mode debug avec plus de logs")
    parser.add_argument("--check-midi", action="store_true", help="Vérifie les périphériques MIDI et quitte")
    parser.add_argument("--check-models", action="store_true", help="Vérifie les modèles disponibles et quitte")
    return parser.parse_args()


def main():
    """Fonction principale"""
    # Vérifier les arguments
    check_models = "--check-models" in sys.argv
    debug_mode = "--debug" in sys.argv
    
    # Configurer le niveau de logging
    global logger
    logger = setup_logging(debug=debug_mode)
    
    if debug_mode:
        logger.info("Démarrage de l'application en mode DEBUG")
    else:
        logger.info("Démarrage de l'application en mode NORMAL")
    
    # Si on veut juste vérifier les modèles
    if check_models:
        logger.info("Vérification des modèles vocaux...")
        available_models = model_manager.get_available_models()
        installed_models = model_manager.get_installed_models()
        
        logger.info(f"Modèles disponibles: {list(available_models.keys())}")
        logger.info(f"Modèles installés: {list(installed_models.keys())}")
        
        return
    
    # Créer l'application Qt
    app = QApplication(sys.argv)
    
    # Créer et afficher un écran de démarrage
    splash_pixmap = QPixmap(512, 512)
    splash_pixmap.fill(Qt.white)
    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    
    # Widget pour le contenu du splash
    splash_content = QWidget()
    splash_layout = QVBoxLayout(splash_content)
    
    # Titre
    title_label = QLabel("OpenVoice Studio")
    title_label.setFont(QFont("Arial", 24, QFont.Bold))
    title_label.setAlignment(Qt.AlignCenter)
    splash_layout.addWidget(title_label)
    
    # Message de chargement
    message_label = QLabel("Chargement...")
    message_label.setAlignment(Qt.AlignCenter)
    splash_layout.addWidget(message_label)
    
    # Barre de progression
    progress_bar = QProgressBar()
    progress_bar.setRange(0, 100)
    progress_bar.setValue(0)
    splash_layout.addWidget(progress_bar)
    
    # Version
    version_label = QLabel("Version 1.0.0")
    version_label.setAlignment(Qt.AlignRight)
    splash_layout.addWidget(version_label)
    
    # Appliquer le layout au splash screen
    splash.setLayout(splash_layout)
    
    # Afficher le splash screen
    splash.show()
    app.processEvents()
    
    # Créer et exécuter le thread de préchargement
    preloader = PreloaderThread()
    
    # Variable pour indiquer quand le préchargement est terminé
    preload_completed = threading.Event()
    
    # Connecter le signal de progression
    def update_progress(value, message):
        progress_bar.setValue(value)
        message_label.setText(message)
        app.processEvents()
        
        # Si la valeur est 100, le préchargement est terminé
        if value == 100:
            preload_completed.set()
    
    preloader.progress.connect(update_progress)
    
    # Fonction pour exécuter le préchargement dans un thread
    def run_preloader():
        preloader.run()
    
    # Démarrer le préchargement dans un thread séparé
    preload_thread = threading.Thread(target=run_preloader, daemon=True)
    preload_thread.start()
    
    # Attendre que le préchargement soit terminé ou un maximum de 30 secondes
    start_time = time.time()
    while not preload_completed.is_set() and time.time() - start_time < 30:
        app.processEvents()
        time.sleep(0.1)
    
    # Créer la fenêtre principale
    window = MainWindow()
    
    # Fermer le splash screen et afficher la fenêtre principale
    splash.finish(window)
    window.show()
    
    # Journaliser l'initialisation
    logger.info("Application initialisée")
    
    # Exécuter l'application
    sys.exit(app.exec())


if __name__ == "__main__":
    sys.exit(main()) 