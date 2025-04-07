"""
Voice synthesis application with MIDI interface.

This module is the main entry point of the application that provides
a graphical interface for voice synthesis with MIDI control.
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

# Import application modules
# Import English versions of modules when available
try:
    from gui.synthesis_tab_english import SynthesisTab
except ImportError:
    from gui.synthesis_tab import SynthesisTab

try:
    from gui.recording_tab_english import RecordingTab
except ImportError:
    from gui.recording_tab import RecordingTab

try:
    from gui.models_tab_english import ModelsTab
except ImportError:
    from gui.models_tab import ModelsTab

from gui.midi_tab import MidiTab
from utils.midi_device_manager import midi_manager
from core.voice_cloning import model_manager

# Logging configuration
def setup_logging(debug=False):
    """Configure the logging system"""
    log_level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("openvoice.log"),
            logging.StreamHandler()
        ]
    )
    
    # Configure third-party library logs
    if not debug:
        # Reduce verbosity of third-party libraries
        logging.getLogger("matplotlib").setLevel(logging.WARNING)
        logging.getLogger("PIL").setLevel(logging.WARNING)
        logging.getLogger("scipy").setLevel(logging.WARNING)
        logging.getLogger("torch").setLevel(logging.WARNING)
        logging.getLogger("tensorflow").setLevel(logging.WARNING)
        logging.getLogger("rtmidi").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# The logger will be initialized later
logger = None


class PreloaderThread(QObject):
    """Thread for preloading modules and models"""
    
    progress = Signal(int, str)
    
    def __init__(self, debug=False):
        super().__init__()
        self.modules_loaded = False
        self.debug = debug
    
    def run(self):
        """Execute preloading"""
        try:
            # TTS modules initialization
            self.progress.emit(10, "Initializing TTS modules...")
            self._init_tts_modules()
            
            # Loading voice models
            self.progress.emit(30, "Loading voice models...")
            self._load_voice_models()
            
            # Preparing synthesis engine
            self.progress.emit(60, "Preparing synthesis engine...")
            self._prepare_synthesis_engine()
            
            # MIDI interfaces initialization
            self.progress.emit(80, "Initializing MIDI interfaces...")
            self._init_midi()
            
            # Finalization
            self.progress.emit(100, "Ready!")
            self.modules_loaded = True
            
        except Exception as e:
            logger.error(f"Error during preloading: {e}", exc_info=self.debug)
            self.progress.emit(100, f"Error: {str(e)}")
    
    def _init_tts_modules(self):
        """Initialize TTS modules"""
        try:
            # Check if CUDA is available
            is_cuda_available = torch.cuda.is_available()
            if is_cuda_available:
                logger.info(f"CUDA available, number of GPUs: {torch.cuda.device_count()}")
                logger.info(f"GPU used: {torch.cuda.get_device_name(0)}")
            else:
                logger.info("CUDA not available, using CPU")
            
            # Preload common models
            # For Coqui TTS
            try:
                import TTS
                logger.info(f"Coqui TTS version: {TTS.__version__}")
                self.progress.emit(15, "Loading Coqui TTS...")
            except ImportError:
                logger.warning("Coqui TTS not available")
            
            # For Bark
            try:
                import bark
                self.progress.emit(20, "Loading Bark...")
                logger.info("Bark available")
            except ImportError:
                logger.warning("Bark not available")
            
            # For gTTS (fallback)
            try:
                import gtts
                self.progress.emit(25, "Loading gTTS...")
                logger.info(f"gTTS version: {gtts.__version__}")
            except ImportError:
                logger.warning("gTTS not available")
            
            logger.info("TTS modules initialized")
        except Exception as e:
            logger.error(f"Error during TTS modules initialization: {e}", exc_info=self.debug)
            raise
    
    def _load_voice_models(self):
        """Load voice models"""
        try:
            # Get the list of available models
            available_models = model_manager.get_available_models()
            logger.info(f"Available models: {list(available_models.keys())}")
            
            # Get the list of installed models
            installed_models = model_manager.get_installed_models()
            logger.info(f"Installed models: {list(installed_models.keys())}")
            
            # For each installed model, we can preload some resources
            for i, (model_id, model_info) in enumerate(installed_models.items()):
                progress = 30 + (i * 5) % 20  # Progress between 30-50%
                self.progress.emit(progress, f"Loading model {model_info.get('name', model_id)}...")
                
                # Here, we could preload specific resources for each model
                # For example, for Coqui TTS, we could load a basic model
                
            logger.info("Voice models loaded")
        except Exception as e:
            logger.error(f"Error during voice models loading: {e}", exc_info=self.debug)
            raise
    
    def _prepare_synthesis_engine(self):
        """Prepare synthesis engine"""
        try:
            # Initialize synthesis backends
            # This step may include preloading small models
            # or checking the availability of external APIs
            
            # Example: Load a small TTS model for quick responses
            try:
                from TTS.api import TTS
                self.progress.emit(55, "Preparing default TTS model...")
                # We don't actually load the model here to avoid slowing down startup
                # But we check that we can initialize it
                # tts = TTS("tts_models/fr/mai/tacotron2-DDC", verbose=False)
            except ImportError:
                pass
            
            # Example: Preload some parameters for gTTS
            try:
                from gtts import gTTS
                self.progress.emit(60, "Preparing gTTS...")
                # Create a small test to verify gTTS works
                # test_tts = gTTS("Test", lang="fr")
            except ImportError:
                pass
            
            # Simulate loading time
            time.sleep(0.5)
            
            logger.info("Synthesis engine ready")
        except Exception as e:
            logger.error(f"Error during synthesis engine preparation: {e}", exc_info=self.debug)
            raise
    
    def _init_midi(self):
        """Initialize MIDI interfaces"""
        try:
            # Check rtmidi version
            try:
                import rtmidi
                rtmidi_version = getattr(rtmidi, "__version__", "Unknown")
                logger.info(f"rtmidi version: {rtmidi_version}")
            except ImportError as e:
                logger.error(f"Error creating MIDI objects: {e}")
                rtmidi_version = "Not available"
            
            # Scan MIDI devices
            midi_manager.scan_devices()
            
            # Here, we could preload virtual MIDI instruments
            # or other resources for MIDI processing
            
            logger.info("MIDI interfaces initialized")
        except Exception as e:
            logger.error(f"Error during MIDI interfaces initialization: {e}", exc_info=self.debug)
            raise
            

class SplashScreen(QSplashScreen):
    """Startup screen with progress bar"""
    
    def __init__(self):
        # Create a base image for the splash screen
        pixmap = QPixmap(QSize(600, 300))
        pixmap.fill(Qt.transparent)
        
        # Apply a gradient as background
        painter = QPainter(pixmap)
        gradient = QLinearGradient(0, 0, 0, 300)
        gradient.setColorAt(0, QColor(40, 40, 80))
        gradient.setColorAt(1, QColor(20, 20, 40))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, 0, 600, 300)
        painter.end()
        
        super().__init__(pixmap)
        
        # Appearance configuration
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Central widget
        self.content = QWidget(self)
        self.content.setGeometry(0, 0, 600, 300)
        self.content.setLayout(layout)
        
        # Title
        title_label = QLabel("Voice Synthesis with MIDI")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Space
        layout.addStretch(1)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        # Progress bar
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
        
        # Space
        layout.addStretch(1)
    
    def update_progress(self, value, message):
        """Update progress bar and message"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self.repaint()  # Force interface refresh


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, args):
        super().__init__()
        
        # Window configuration
        self.setWindowTitle("OpenVoice Voice Synthesis (English)")
        self.setMinimumSize(800, 600)
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create tabs
        self.synthesis_tab = SynthesisTab()
        self.recording_tab = RecordingTab()
        self.models_tab = ModelsTab()
        
        # Try to create MIDI tab safely
        try:
            self.midi_tab = MidiTab()
            # Connect MIDI signals
            self._safe_connect(self.midi_tab, "midi_note_on", self.on_midi_note_on)
            self._safe_connect(self.midi_tab, "midi_control_change", self.on_midi_control_change)
        except Exception as e:
            logger.error(f"Error creating MIDI tab: {e}")
            # Create error placeholder
            midi_error_widget = QWidget()
            midi_layout = QVBoxLayout(midi_error_widget)
            error_label = QLabel(f"MIDI Tab Error: {str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            midi_layout.addWidget(error_label)
            self.midi_tab = midi_error_widget
        
        # Safely connect signals
        self._safe_connect(self.recording_tab, "voice_cloned", self.on_voice_cloned)
        
        # Add tabs to tab widget in the requested order
        self.tabs.addTab(self.recording_tab, "Recording")
        self.tabs.addTab(self.synthesis_tab, "Synthesis")
        self.tabs.addTab(self.models_tab, "Models")
        self.tabs.addTab(self.midi_tab, "MIDI")
        
        # Check command line arguments
        if args.tab:
            self._select_tab_by_name(args.tab)
            
        # Setup status bar
        self.statusBar().showMessage("Ready")
        
        # Show window
        self.show()
        
    def _safe_connect(self, source, signal_name, slot):
        """Safely connect a signal to a slot, with fallback for attribute errors"""
        if not hasattr(source, signal_name):
            logger.warning(f"Object {type(source).__name__} has no signal {signal_name}")
            return False
            
        # Check for the new connect_signal method
        if hasattr(source, "connect_signal") and callable(source.connect_signal):
            try:
                success = source.connect_signal(signal_name, slot)
                if success:
                    logger.info(f"Connected {signal_name} using connect_signal method")
                    return True
            except Exception as e:
                logger.warning(f"Error using connect_signal method: {e}")
        
        # Use custom connect method if available (legacy)
        if hasattr(source, "connect") and callable(source.connect):
            try:
                source.connect(signal_name, slot)
                logger.info(f"Connected {signal_name} using connect method")
                return True
            except Exception as e:
                logger.warning(f"Error using custom connect method: {e}")
                
        # Try direct connection
        try:
            signal = getattr(source, signal_name)
            signal.connect(slot)
            logger.info(f"Connected {signal_name} using direct signal.connect")
            return True
        except AttributeError:
            logger.warning(f"Signal {signal_name} has no connect attribute")
        except Exception as e:
            logger.warning(f"Error connecting signal {signal_name}: {e}")
            
        return False

    def _select_tab_by_name(self, tab_name):
        """Select a tab by name"""
        tab_name = tab_name.lower()
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i).lower() == tab_name:
                self.tabs.setCurrentIndex(i)
                return True
        return False
    
    def on_voice_cloned(self, model_id):
        """Handle voice cloning completion"""
        logger.info(f"Voice cloned with model ID: {model_id}")
        
        # Refresh models in the models tab
        if hasattr(self.models_tab, "refresh_models") and callable(self.models_tab.refresh_models):
            self.models_tab.refresh_models()
            
        # Switch to synthesis tab
        self.tabs.setCurrentIndex(1)  # Synthesis tab
        
        # Update status
        self.statusBar().showMessage(f"Voice cloned successfully. Model ID: {model_id}")
    
    def on_midi_note_on(self, note, velocity):
        """Handle MIDI note on event"""
        logger.info(f"MIDI Note On: {note} velocity: {velocity}")
        # Forward to synthesis tab if needed
        
    def on_midi_control_change(self, controller, value):
        """Handle MIDI control change event"""
        logger.info(f"MIDI CC: {controller} value: {value}")
        # Forward to synthesis tab if needed


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Voice synthesis application with MIDI control")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with more logs")
    parser.add_argument("--check-midi", action="store_true", help="Check MIDI devices and exit")
    parser.add_argument("--check-models", action="store_true", help="Check available models and exit")
    parser.add_argument("--tab", help="Select a specific tab to open")
    return parser.parse_args()


def main():
    """Main function"""
    # Check arguments
    check_models = "--check-models" in sys.argv
    debug_mode = "--debug" in sys.argv
    
    # Configure logging level
    global logger
    logger = setup_logging(debug=debug_mode)
    
    if debug_mode:
        logger.info("Starting application in DEBUG mode")
    else:
        logger.info("Starting application in NORMAL mode")
    
    # If we just want to check models
    if check_models:
        logger.info("Checking voice models...")
        available_models = model_manager.get_available_models()
        installed_models = model_manager.get_installed_models()
        
        logger.info(f"Available models: {list(available_models.keys())}")
        logger.info(f"Installed models: {list(installed_models.keys())}")
        
        return
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create and display a splash screen
    splash_pixmap = QPixmap(512, 512)
    splash_pixmap.fill(Qt.white)
    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    
    # Widget for splash content
    splash_content = QWidget()
    splash_layout = QVBoxLayout(splash_content)
    
    # Title
    title_label = QLabel("OpenVoice Studio")
    title_label.setFont(QFont("Arial", 24, QFont.Bold))
    title_label.setAlignment(Qt.AlignCenter)
    splash_layout.addWidget(title_label)
    
    # Loading message
    message_label = QLabel("Loading...")
    message_label.setAlignment(Qt.AlignCenter)
    splash_layout.addWidget(message_label)
    
    # Progress bar
    progress_bar = QProgressBar()
    progress_bar.setRange(0, 100)
    progress_bar.setValue(0)
    splash_layout.addWidget(progress_bar)
    
    # Version
    version_label = QLabel("Version 1.0.0")
    version_label.setAlignment(Qt.AlignRight)
    splash_layout.addWidget(version_label)
    
    # Apply layout to splash screen
    splash.setLayout(splash_layout)
    
    # Show splash screen
    splash.show()
    app.processEvents()
    
    # Create and run preloading thread
    preloader = PreloaderThread()
    
    # Variable to indicate when preloading is done
    preload_completed = threading.Event()
    
    # Connect progress signal
    def update_progress(value, message):
        progress_bar.setValue(value)
        message_label.setText(message)
        app.processEvents()
        
        # If value is 100, preloading is done
        if value == 100:
            preload_completed.set()
    
    preloader.progress.connect(update_progress)
    
    # Function to run preloading in a thread
    def run_preloader():
        preloader.run()
    
    # Start preloading in a separate thread
    preload_thread = threading.Thread(target=run_preloader, daemon=True)
    preload_thread.start()
    
    # Wait until preloading is done or a maximum of 30 seconds
    start_time = time.time()
    while not preload_completed.is_set() and time.time() - start_time < 30:
        app.processEvents()
        time.sleep(0.1)
    
    # Create main window
    args = parse_arguments()
    window = MainWindow(args)
    
    # Close splash screen and show main window
    splash.finish(window)
    window.show()
    
    # Log initialization
    logger.info("Application initialized")
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    sys.exit(main()) 