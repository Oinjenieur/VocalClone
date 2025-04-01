"""
Module pour l'affichage des signaux MIDI entrants avec retour visuel.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QRadialGradient, QPainterPath
import math

class MidiActivityIndicator(QWidget):
    """Widget pour afficher l'activité MIDI avec animation fluide"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(20, 20)
        self.setMaximumSize(20, 20)
        self._activity = 0.0  # 0.0 à 1.0
        
        # Timer pour faire diminuer progressivement l'activité
        self.decay_timer = QTimer()
        self.decay_timer.timeout.connect(self._decay_activity)
        self.decay_timer.setInterval(50)  # 50ms (20 fps)
        self.decay_timer.start()
        
    def setActivity(self, level=1.0):
        """Définit le niveau d'activité de l'indicateur"""
        self._activity = min(1.0, max(0.0, level))
        self.update()
        
    def _decay_activity(self):
        """Diminue progressivement le niveau d'activité"""
        if self._activity > 0.01:
            self._activity *= 0.9  # Diminution exponentielle
            self.update()
        elif self._activity > 0:
            self._activity = 0
            self.update()
            
    def paintEvent(self, event):
        """Dessine l'indicateur avec un effet de lueur basé sur l'activité"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        size = min(self.width(), self.height())
        radius = size / 2 - 2
        
        # Créer un dégradé radial pour l'effet de lueur
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # Couleur de base: vert avec intensité variable
        base_color = QColor(0, 255, 0)
        dim_color = QColor(0, 100, 0)
        
        # Interpoler entre les couleurs en fonction de l'activité
        r = int(dim_color.red() + self._activity * (base_color.red() - dim_color.red()))
        g = int(dim_color.green() + self._activity * (base_color.green() - dim_color.green()))
        b = int(dim_color.blue() + self._activity * (base_color.blue() - dim_color.blue()))
        
        active_color = QColor(r, g, b)
        
        # Créer le dégradé
        gradient = QRadialGradient(center_x, center_y, radius * 1.2)
        gradient.setColorAt(0, active_color)
        gradient.setColorAt(0.7, active_color.darker(100 + int(50 * (1 - self._activity))))
        gradient.setColorAt(1, QColor(0, 30, 0))
        
        # Dessiner l'indicateur
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(0, 0, 0, 100), 1))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # Ajouter un reflet
        if self._activity > 0.3:
            highlight = QPainterPath()
            highlight_radius = radius * 0.4
            highlight.addEllipse(center_x - highlight_radius + radius * 0.3, 
                               center_y - highlight_radius - radius * 0.1, 
                               highlight_radius * 2, highlight_radius * 0.8)
            
            highlight_color = QColor(255, 255, 255, int(100 * self._activity))
            painter.setBrush(highlight_color)
            painter.setPen(Qt.NoPen)
            painter.drawPath(highlight)

class NoteDisplay(QWidget):
    """Widget pour afficher une note MIDI avec sa vélocité"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(25)
        self.setMaximumHeight(25)
        
        self.note_number = None
        self.velocity = 0
        self.frequency = 0
        self._active = False
        
        # Animation pour le fondu
        self.opacity = 0.0
        self.animation = QPropertyAnimation(self, b"customOpacity")
        self.animation.setDuration(300)  # 300ms
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
    def setCustomOpacity(self, opacity):
        """Setter pour la propriété customOpacity utilisée par l'animation"""
        self.opacity = opacity
        self.update()
        
    def customOpacity(self):
        """Getter pour la propriété customOpacity utilisée par l'animation"""
        return self.opacity
        
    # Définition de la propriété pour l'animation
    customOpacity = Property(float, customOpacity, setCustomOpacity)
    
    def setNote(self, note_number, velocity):
        """Définit la note à afficher et sa vélocité"""
        self.note_number = note_number
        self.velocity = velocity
        
        if note_number is not None:
            # Calculer la fréquence de la note
            self.frequency = 440.0 * (2.0 ** ((note_number - 69) / 12.0))
            
            # Animer l'apparition si la note est active
            if velocity > 0 and not self._active:
                self._active = True
                self.animation.setStartValue(0.0)
                self.animation.setEndValue(1.0)
                self.animation.start()
            # Animer la disparition si la note est relâchée
            elif velocity == 0 and self._active:
                self._active = False
                self.animation.setStartValue(1.0)
                self.animation.setEndValue(0.0)
                self.animation.start()
        else:
            self.frequency = 0
            self._active = False
            self.opacity = 0.0
            
        self.update()
        
    def paintEvent(self, event):
        """Dessine la note avec sa vélocité"""
        if self.note_number is None or self.opacity <= 0:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Définir l'opacité
        painter.setOpacity(self.opacity)
        
        # Paramètres de dessin
        width = self.width()
        height = self.height()
        
        # Couleur basée sur la vélocité (du jaune au rouge)
        hue = max(0, 60 - (self.velocity / 127) * 60)
        color = QColor.fromHsv(hue, 255, 255, 255)
        
        # Dessiner le fond de la note
        painter.setBrush(color.darker(150))
        painter.setPen(QPen(Qt.black, 1))
        
        # Rectangle arrondi pour le fond
        painter.drawRoundedRect(2, 2, width - 4, height - 4, 5, 5)
        
        # Dessiner le nom de la note
        painter.setPen(QPen(Qt.white, 1))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        
        note_name = self._get_note_name(self.note_number)
        freq_text = f"{self.frequency:.1f} Hz"
        
        # Afficher le nom de la note et la fréquence
        painter.drawText(10, 0, width - 20, height, Qt.AlignLeft | Qt.AlignVCenter, note_name)
        painter.drawText(0, 0, width - 10, height, Qt.AlignRight | Qt.AlignVCenter, freq_text)
        
        # Barre d'intensité basée sur la vélocité
        if self.velocity > 0:
            intensity_width = (width - 20) * (self.velocity / 127)
            intensity_rect = QBrush(color.lighter(150))
            painter.setBrush(intensity_rect)
            painter.setPen(Qt.NoPen)
            painter.drawRect(10, height - 5, intensity_width, 3)
        
    def _get_note_name(self, note):
        """Convertit un numéro de note MIDI en nom de note"""
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = (note // 12) - 1
        note_name = notes[note % 12]
        return f"{note_name}{octave}"
        
    def sizeHint(self):
        """Taille préférée du widget"""
        return QSize(200, 25)

class MidiIndicator(QWidget):
    """Widget complet pour afficher l'activité MIDI et les notes jouées"""
    
    MAX_NOTES = 5  # Nombre maximum de notes à afficher simultanément
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 150)
        
        # Créer le layout principal
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
        # En-tête avec indicateur d'activité
        header_layout = QHBoxLayout()
        
        self.activity_indicator = MidiActivityIndicator()
        header_layout.addWidget(self.activity_indicator)
        
        self.status_label = QLabel("MIDI")
        self.status_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        self.device_label = QLabel("Aucun périphérique")
        self.device_label.setStyleSheet("color: gray; font-style: italic;")
        header_layout.addWidget(self.device_label)
        
        self.layout.addLayout(header_layout)
        
        # Ligne de séparation
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        separator.setStyleSheet("background-color: #3a3a3a;")
        self.layout.addWidget(separator)
        
        # Section pour les notes actives
        self.notes_layout = QVBoxLayout()
        self.layout.addLayout(self.notes_layout)
        
        # Créer des widgets pour les notes (réutilisables)
        self.note_displays = []
        for _ in range(self.MAX_NOTES):
            note_display = NoteDisplay()
            note_display.hide()  # Caché par défaut
            self.notes_layout.addWidget(note_display)
            self.note_displays.append(note_display)
            
        # Espace extensible en bas
        self.layout.addStretch()
        
        # Dictionnaire des notes actives {note: widget}
        self.active_notes = {}
        
    def setDeviceName(self, name):
        """Définit le nom du périphérique MIDI connecté"""
        if name:
            self.device_label.setText(name)
            self.device_label.setStyleSheet("color: #8aff8a;")
        else:
            self.device_label.setText("Aucun périphérique")
            self.device_label.setStyleSheet("color: gray; font-style: italic;")
            
    def handleNoteOn(self, channel, note, velocity):
        """Gère un événement Note On"""
        # Activer l'indicateur d'activité
        self.activity_indicator.setActivity(velocity / 127)
        
        # Ajouter la note aux notes actives
        if velocity > 0:
            # Réutiliser un widget existant ou le premier disponible
            display = self.active_notes.get(note)
            if not display:
                # Trouver un widget disponible
                for widget in self.note_displays:
                    if widget not in self.active_notes.values():
                        display = widget
                        self.active_notes[note] = display
                        break
                        
                # Si tous les widgets sont utilisés, réutiliser le premier
                if not display and self.note_displays:
                    # Trouver la note la plus ancienne
                    oldest_note = next(iter(self.active_notes))
                    display = self.active_notes[oldest_note]
                    del self.active_notes[oldest_note]
                    self.active_notes[note] = display
                    
            # Mettre à jour l'affichage de la note
            if display:
                display.setNote(note, velocity)
                display.show()
                
            # Mettre à jour le statut
            self.status_label.setText(f"MIDI Ch.{channel+1}")
            
    def handleNoteOff(self, channel, note, velocity):
        """Gère un événement Note Off"""
        # Désactiver progressivement l'indicateur d'activité
        self.activity_indicator.setActivity(0.5)  # Activité modérée sur relâchement
        
        # Marquer la note comme relâchée
        if note in self.active_notes:
            display = self.active_notes[note]
            display.setNote(note, 0)  # vélocité 0 pour indiquer note off
            
            # Supprimer la note après un court délai (pour l'animation)
            QTimer.singleShot(400, lambda: self._remove_note(note))
            
    def handleControlChange(self, channel, cc, value):
        """Gère un événement Control Change"""
        # Activer l'indicateur d'activité proportionnellement à la valeur
        self.activity_indicator.setActivity(value / 127)
        
        # Mettre à jour le statut
        self.status_label.setText(f"MIDI CC{cc} Ch.{channel+1}")
        
    def _remove_note(self, note):
        """Supprime une note de l'affichage après l'animation"""
        if note in self.active_notes:
            display = self.active_notes[note]
            del self.active_notes[note]
            
            # Cacher le widget si plus aucune note n'est active
            if not self.active_notes:
                display.hide()
                
    def clear(self):
        """Efface toutes les notes actives"""
        for note, display in self.active_notes.items():
            display.setNote(None, 0)
            display.hide()
            
        self.active_notes.clear()
        self.activity_indicator.setActivity(0) 