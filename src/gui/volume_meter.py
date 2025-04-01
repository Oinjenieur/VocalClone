from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QLinearGradient, QColor

class VolumeMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 20)
        self.level = 0.0  # Niveau entre 0 et 1
        
        # Configuration du gradient de couleurs
        self.gradient = QLinearGradient(0, 0, 1, 0)
        self.gradient.setCoordinateMode(QLinearGradient.ObjectMode)
        self.gradient.setStops([
            (0.0, QColor("#00ff00")),    # Vert
            (0.6, QColor("#ffff00")),    # Jaune
            (0.8, QColor("#ff8800")),    # Orange
            (1.0, QColor("#ff0000"))     # Rouge
        ])
    
    def set_level(self, level):
        """Définit le niveau actuel (entre 0 et 1)"""
        self.level = max(0.0, min(1.0, level))
        self.update()
    
    def paintEvent(self, event):
        """Dessine le vu-mètre"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calcul des dimensions
        width = self.width()
        height = self.height()
        padding = 2
        inner_height = height - 2 * padding
        
        # Fond sombre
        painter.fillRect(0, 0, width, height, QColor("#1a1a1a"))
        
        # Rectangle du niveau
        if self.level > 0:
            level_width = int(self.level * width)
            rect = QRectF(padding, padding, level_width - 2 * padding, inner_height)
            
            # Mise à jour des coordonnées du gradient
            self.gradient.setStart(0, 0)
            self.gradient.setFinalStop(width, 0)
            
            # Dessin du niveau avec le gradient
            painter.fillRect(rect, self.gradient)
        
        # Bordure
        painter.setPen(QColor("#333333"))
        painter.drawRect(0, 0, width - 1, height - 1)
        
        # Graduations
        painter.setPen(QColor("#666666"))
        for x in range(10, 100, 10):
            pos = int(width * x / 100)
            painter.drawLine(pos, 0, pos, height) 