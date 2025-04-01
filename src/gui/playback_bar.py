from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSlider
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QPainter, QColor, QPen, QLinearGradient

class PlaybackBar(QWidget):
    """Widget pour contrôler et afficher la progression de la lecture audio"""
    
    seek_position = Signal(float)  # Signal émis lorsque l'utilisateur cherche une position (0-1)
    play_clicked = Signal()        # Signal émis lorsque l'utilisateur clique sur Lecture
    pause_clicked = Signal()       # Signal émis lorsque l'utilisateur clique sur Pause
    stop_clicked = Signal()        # Signal émis lorsque l'utilisateur clique sur Stop
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 0          # Durée totale en secondes
        self.current_time = 0      # Temps actuel en secondes
        self.is_playing = False    # Indique si la lecture est en cours
        
        self._setup_ui()
        
        # Timer pour mettre à jour l'affichage du temps
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(50)  # 50ms (20fps)
        self.update_timer.timeout.connect(self._update_display)
        
    def _setup_ui(self):
        """Initialise l'interface utilisateur"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Layout pour les contrôles de lecture
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Boutons de contrôle
        self.play_button = QPushButton(QIcon("resources/icons/play.png"), "")
        self.play_button.setToolTip("Lecture")
        self.play_button.setFixedSize(30, 30)
        self.play_button.clicked.connect(self._on_play_clicked)
        
        self.stop_button = QPushButton(QIcon("resources/icons/stop.png"), "")
        self.stop_button.setToolTip("Arrêt")
        self.stop_button.setFixedSize(30, 30)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        
        # Affichage du temps
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_label.setMinimumWidth(100)
        self.time_label.setStyleSheet("color: #cccccc;")
        
        # Slider de progression
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)  # Utiliser 1000 pour une précision décimale
        self.progress_slider.setValue(0)
        self.progress_slider.setMinimumWidth(200)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #333;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2ea043;
                border: 1px solid #27ae60;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #2ea043, stop: 1 #3cb371);
                border-radius: 4px;
            }
        """)
        
        # Connexions
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.valueChanged.connect(self._on_slider_value_changed)
        
        # Ajout des widgets au layout
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.progress_slider, 1)  # Stretch
        controls_layout.addWidget(self.time_label)
        
        main_layout.addLayout(controls_layout)
        
    def _on_play_clicked(self):
        """Gère le clic sur le bouton lecture/pause"""
        if self.is_playing:
            self.set_playing(False)
            self.pause_clicked.emit()
        else:
            self.set_playing(True)
            self.play_clicked.emit()
    
    def _on_stop_clicked(self):
        """Gère le clic sur le bouton stop"""
        self.set_playing(False)
        self.set_position(0)
        self.stop_clicked.emit()
    
    def _on_slider_pressed(self):
        """Appelé quand l'utilisateur commence à déplacer le curseur"""
        if self.is_playing:
            self.update_timer.stop()
    
    def _on_slider_released(self):
        """Appelé quand l'utilisateur relâche le curseur"""
        position = self.progress_slider.value() / 1000.0  # Convertir en 0-1
        self.seek_position.emit(position)
        if self.is_playing:
            self.update_timer.start()
    
    def _on_slider_value_changed(self, value):
        """Appelé quand la valeur du slider change"""
        if not self.progress_slider.isSliderDown():
            position = value / 1000.0  # Convertir en 0-1
            self.current_time = position * self.duration
            self._update_time_label()
    
    def _update_display(self):
        """Met à jour l'affichage pendant la lecture"""
        if self.is_playing and self.duration > 0:
            self.current_time += 0.05  # 50ms
            if self.current_time >= self.duration:
                self.current_time = self.duration
                self.set_playing(False)
                self.stop_clicked.emit()
            
            # Mettre à jour le slider
            position = min(1.0, self.current_time / self.duration if self.duration > 0 else 0)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(int(position * 1000))
            self.progress_slider.blockSignals(False)
            
            self._update_time_label()
    
    def _update_time_label(self):
        """Met à jour l'affichage du temps"""
        current_min = int(self.current_time) // 60
        current_sec = int(self.current_time) % 60
        total_min = int(self.duration) // 60
        total_sec = int(self.duration) % 60
        
        time_text = f"{current_min:02d}:{current_sec:02d} / {total_min:02d}:{total_sec:02d}"
        self.time_label.setText(time_text)
    
    def set_duration(self, duration_seconds):
        """Définit la durée totale en secondes"""
        self.duration = max(0, duration_seconds)
        self._update_time_label()
    
    def set_position(self, position):
        """Définit la position actuelle (0-1)"""
        position = min(1.0, max(0.0, position))
        self.current_time = position * self.duration
        
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(int(position * 1000))
        self.progress_slider.blockSignals(False)
        
        self._update_time_label()
    
    def set_playing(self, playing):
        """Définit l'état de lecture et met à jour l'interface"""
        self.is_playing = playing
        
        if playing:
            self.play_button.setIcon(QIcon("resources/icons/pause.png"))
            self.play_button.setToolTip("Pause")
            self.update_timer.start()
        else:
            self.play_button.setIcon(QIcon("resources/icons/play.png"))
            self.play_button.setToolTip("Lecture")
            self.update_timer.stop()
            
    def reset(self):
        """Réinitialise le contrôle à l'état initial"""
        self.set_playing(False)
        self.set_position(0)
        self.set_duration(0) 