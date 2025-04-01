"""
Module pour l'affichage des formes d'onde audio.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont
from PySide6.QtCore import Qt, QRect, QSize, QTimer, QEasingCurve, QPropertyAnimation, QPoint, Property
import numpy as np


class WaveformDisplay(QWidget):
    """Widget d'affichage de forme d'onde audio"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.waveform_data = np.array([])
        self.setMinimumHeight(80)
        self.setMinimumWidth(200)
        
        # Couleurs et style
        self.bg_color = QColor(30, 30, 30)
        self.wave_gradient_start = QColor(0, 120, 255)  # Bleu
        self.wave_gradient_end = QColor(0, 200, 255)    # Bleu clair
        self.playback_position_color = QColor(255, 120, 0)  # Orange
        self.grid_color = QColor(80, 80, 80)
        
        # État de lecture
        self.is_playing = False
        self.playback_position = 0.0  # Position de lecture (0.0 à 1.0)
        
        # Animation de lecture
        self._highlight_opacity = 0.3
        self.highlight_timer = QTimer(self)
        self.highlight_timer.setInterval(50)  # 50ms (20fps)
        self.highlight_timer.timeout.connect(self._update_highlight)
        
        # Animation d'onde
        self._wave_offset = 0.0
        self.wave_timer = QTimer(self)
        self.wave_timer.setInterval(50)  # 50ms (20fps)
        self.wave_timer.timeout.connect(self._update_wave_animation)
        
    def set_waveform(self, data):
        """Définit les données de forme d'onde à afficher"""
        if isinstance(data, np.ndarray) and len(data) > 0:
            # Limiter la taille des données pour des raisons de performance
            if len(data) > 10000:
                # Sous-échantillonnage
                factor = len(data) // 10000 + 1
                self.waveform_data = data[::factor]
            else:
                self.waveform_data = data
                
            # Normaliser les données entre -1 et 1
            max_val = np.max(np.abs(self.waveform_data))
            if max_val > 0:
                self.waveform_data = self.waveform_data / max_val
                
            self.update()  # Déclencher le repaint
        else:
            self.clear()
            
    def clear(self):
        """Efface les données de forme d'onde"""
        self.waveform_data = np.array([])
        self.update()
        
    def set_playing(self, is_playing, position=None):
        """Définit l'état de lecture et la position"""
        self.is_playing = is_playing
        if position is not None:
            self.playback_position = position
        self.update()  # Forcer le rafraîchissement
        
    def set_playback_position(self, position):
        """Met à jour la position de lecture"""
        self.playback_position = position
        self.update()  # Forcer le rafraîchissement
        
    def _update_highlight(self):
        """Met à jour l'opacité du surligneur pour l'animation"""
        self._highlight_opacity = 0.3 + 0.2 * np.sin(QTimer.currentTime().msecsSinceStartOfDay() / 200.0)
        self.update()
        
    def _update_wave_animation(self):
        """Met à jour l'animation de l'onde pendant la lecture"""
        if self.is_playing:
            self._wave_offset += 0.05
            if self._wave_offset > 2.0:
                self._wave_offset = 0.0
        self.update()
        
    def paintEvent(self, event):
        """Dessine la forme d'onde"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Dimensions du widget
        width = self.width()
        height = self.height()
        center_y = height // 2
        
        # Dessiner l'arrière-plan
        painter.fillRect(event.rect(), self.bg_color)
        
        # Dessiner la grille
        self._draw_grid(painter, width, height, center_y)
        
        # Si pas de données, dessiner juste une ligne horizontale au centre
        if len(self.waveform_data) == 0:
            pen = QPen(self.grid_color)
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(0, center_y, width, center_y)
            
            # Afficher un texte si aucune donnée
            if not self.is_playing:
                painter.setPen(QColor(150, 150, 150))
                painter.setFont(QFont("Arial", 10))
                painter.drawText(
                    event.rect(), 
                    Qt.AlignCenter, 
                    "Aucun enregistrement"
                )
            return
            
        # Définir le dégradé pour la forme d'onde
        if self.is_playing:
            # Dégradé animé pendant la lecture
            gradient = QLinearGradient(0, 0, width, 0)
            gradient.setColorAt(0, QColor(0, 200, 100))
            gradient.setColorAt(0.5, QColor(0, 150, 255))
            gradient.setColorAt(1, QColor(100, 100, 255))
            
            # Décaler le dégradé pour l'animation
            gradient.setCoordinateMode(QLinearGradient.ObjectMode)
            offset = width * (self._wave_offset % 1.0)
            gradient.translate(offset, 0)
        else:
            # Dégradé normal
            gradient = QLinearGradient(0, 0, 0, height)
            gradient.setColorAt(0, self.wave_gradient_start)
            gradient.setColorAt(1, self.wave_gradient_end)
        
        # Calculer les points de la forme d'onde
        points_per_pixel = max(1, len(self.waveform_data) // width)
        
        # Dessiner la forme d'onde
        path_pen = QPen(QBrush(gradient), 2)
        painter.setPen(path_pen)
        
        for x in range(width):
            # Index dans les données audio
            start_idx = int((x / width) * len(self.waveform_data))
            end_idx = min(start_idx + points_per_pixel, len(self.waveform_data))
            
            if start_idx < len(self.waveform_data):
                # Prendre la valeur moyenne ou absolue maximum dans ce segment
                if end_idx > start_idx:
                    segment = self.waveform_data[start_idx:end_idx]
                    amplitude = np.max(np.abs(segment))
                else:
                    amplitude = abs(self.waveform_data[start_idx])
                
                # Hauteur proportionnelle à l'amplitude
                y_height = int(amplitude * center_y * 0.9)  # 90% de la moitié pour laisser une marge
                
                # Dessiner une ligne verticale pour ce point
                painter.drawLine(x, center_y - y_height, x, center_y + y_height)
        
        # Dessiner la position de lecture si en cours de lecture ou pause
        if self.playback_position > 0.0 or self.is_playing:
            pos_x = int(self.playback_position * width)
            
            # Ligne de position
            position_pen = QPen(self.playback_position_color)
            position_pen.setWidth(2)
            painter.setPen(position_pen)
            painter.drawLine(pos_x, 0, pos_x, height)
            
            # Cercle indicateur
            if self.is_playing:
                # Cercle animé
                pulse_size = 8 + int(4 * np.sin(QTimer.currentTime().msecsSinceStartOfDay() / 200.0))
                painter.setBrush(QBrush(QColor(255, 120, 0, 200)))
                painter.drawEllipse(QPoint(pos_x, center_y), pulse_size, pulse_size)
            else:
                # Cercle statique
                painter.setBrush(QBrush(QColor(255, 120, 0, 150)))
                painter.drawEllipse(QPoint(pos_x, center_y), 6, 6)
                
            # Texte de position
            duration_minutes = int(len(self.waveform_data) / 48000 / 60)
            duration_seconds = int((len(self.waveform_data) / 48000) % 60)
            
            current_minutes = int(duration_minutes * self.playback_position)
            current_seconds = int(duration_seconds * self.playback_position + 
                                (duration_minutes * 60 * self.playback_position) % 60)
            
            position_text = f"{current_minutes:02d}:{current_seconds:02d}"
            
            # Dessiner le texte avec un fond semi-transparent
            text_width = 60
            text_height = 20
            text_x = max(5, min(pos_x - text_width // 2, width - text_width - 5))
            text_y = height - text_height - 5
            
            painter.fillRect(
                text_x, text_y, text_width, text_height, 
                QColor(0, 0, 0, 150)
            )
            
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(
                text_x, text_y, text_width, text_height,
                Qt.AlignCenter, position_text
            )
            
        # Dessiner la surbrillance lors de la lecture
        if self.is_playing:
            # Rectangle semi-transparent qui pulse
            highlight_color = QColor(255, 200, 0, int(self._highlight_opacity * 40))
            painter.fillRect(0, 0, width, height, highlight_color)
            
            # Indicateur de lecture en haut
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 120, 0, 200))
            
            playback_indicator_width = 80
            playback_indicator_height = 20
            
            painter.drawRect(
                (width - playback_indicator_width) // 2,
                0,
                playback_indicator_width,
                playback_indicator_height
            )
            
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.drawText(
                (width - playback_indicator_width) // 2,
                0,
                playback_indicator_width,
                playback_indicator_height,
                Qt.AlignCenter,
                "LECTURE"
            )
            
    def _draw_grid(self, painter, width, height, center_y):
        """Dessine une grille de fond"""
        # Ligne horizontale au centre
        pen = QPen(self.grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(0, center_y, width, center_y)
        
        # Lignes verticales tous les 100 pixels
        dash_pen = QPen(self.grid_color)
        dash_pen.setStyle(Qt.DashLine)
        dash_pen.setWidth(1)
        painter.setPen(dash_pen)
        
        for x in range(100, width, 100):
            painter.drawLine(x, 0, x, height)
        
    def sizeHint(self):
        """Taille suggérée pour le widget"""
        return QSize(400, 100) 