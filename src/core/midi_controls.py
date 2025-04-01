"""
Module de contrôle MIDI pour la synthèse vocale.

Ce module fournit les classes et fonctions pour interpréter les messages
MIDI et les convertir en paramètres de synthèse vocale.
"""

import logging
import threading
import time
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Callable, Optional, Tuple, Any

# Configuration du logging
logger = logging.getLogger(__name__)

# Constants MIDI
MIDI_NOTE_ON = 0x90
MIDI_NOTE_OFF = 0x80
MIDI_CC = 0xB0
MIDI_PITCH_BEND = 0xE0
MIDI_PROGRAM_CHANGE = 0xC0

# Plage de données MIDI
MIDI_MIN = 0
MIDI_MAX = 127


class MidiMode(Enum):
    """Modes d'opération MIDI pour la synthèse vocale"""
    DIRECT = auto()  # Contrôle direct des paramètres
    PHRASES = auto()  # Déclenchement de phrases
    LIVE = auto()     # Modulation en temps réel


@dataclass
class MidiMapping:
    """Mappage entre un contrôleur MIDI et un paramètre de synthèse"""
    cc_number: int
    parameter: str
    min_value: float
    max_value: float
    curve: str = "linear"  # linear, log, exp
    
    def convert_value(self, midi_value: int) -> float:
        """Convertit une valeur MIDI (0-127) en valeur de paramètre"""
        # Normaliser la valeur MIDI à [0, 1]
        normalized = midi_value / MIDI_MAX
        
        # Appliquer la courbe
        if self.curve == "log":
            # Courbe logarithmique (plus de précision aux valeurs basses)
            if normalized == 0:
                normalized = 0.001  # Éviter log(0)
            normalized = max(0.001, normalized)
            value = (self.max_value - self.min_value) * (
                (self.min_value + normalized * (self.max_value - self.min_value)) / 
                self.max_value
            ) ** 2 + self.min_value
        elif self.curve == "exp":
            # Courbe exponentielle (plus de précision aux valeurs hautes)
            value = self.min_value + (self.max_value - self.min_value) * normalized ** 2
        else:  # linear
            # Interpolation linéaire
            value = self.min_value + (self.max_value - self.min_value) * normalized
            
        return value


class MidiNoteMapping:
    """Mappage entre des notes MIDI et des phrases ou phonèmes"""
    
    def __init__(self):
        self.note_map = {}  # {note: phrase/phonème}
        self.base_octave = 4
        self.current_notes = set()  # Notes actuellement enfoncées
        self.sustain_pedal = False
        
    def map_note(self, note: int, content: str) -> None:
        """Associe une note MIDI à un contenu textuel"""
        self.note_map[note] = content
        
    def get_content(self, note: int) -> Optional[str]:
        """Obtient le contenu associé à une note"""
        return self.note_map.get(note)
    
    def clear_mapping(self) -> None:
        """Efface tous les mappages"""
        self.note_map = {}
        
    def get_active_notes(self) -> List[int]:
        """Retourne la liste des notes actuellement actives"""
        return list(self.current_notes)
    
    def note_on(self, note: int) -> None:
        """Signale qu'une note a été enfoncée"""
        self.current_notes.add(note)
        
    def note_off(self, note: int) -> None:
        """Signale qu'une note a été relâchée"""
        if note in self.current_notes and not self.sustain_pedal:
            self.current_notes.remove(note)
    
    def set_sustain(self, value: bool) -> None:
        """Définit l'état de la pédale de sustain"""
        self.sustain_pedal = value


class MidiControlEngine:
    """Moteur de contrôle MIDI pour la synthèse vocale"""
    
    def __init__(self):
        # Mappages des contrôleurs
        self.cc_mappings: Dict[int, MidiMapping] = {}
        
        # État des paramètres
        self.parameters: Dict[str, float] = {
            "pitch": 0.0,       # Pitch en demi-tons (-12 à +12)
            "speed": 1.0,       # Vitesse de lecture (0.5 à 2.0)
            "volume": 1.0,      # Volume (0.0 à 2.0)
            "modulation": 0.0,  # Modulation (0.0 à 1.0)
            "expression": 1.0,  # Expression (0.0 à 1.0)
        }
        
        # Mappages des notes
        self.note_mapping = MidiNoteMapping()
        
        # Mode de fonctionnement
        self.mode = MidiMode.DIRECT
        
        # Callbacks
        self.parameter_callbacks: Dict[str, List[Callable[[str, float], None]]] = {}
        self.note_callbacks: List[Callable[[int, bool, int], None]] = []
        
        # Thread de modulation automatique
        self.modulation_thread = None
        self.modulation_stop_event = threading.Event()
    
    def set_mode(self, mode: MidiMode) -> None:
        """Définit le mode de fonctionnement MIDI"""
        self.mode = mode
        
    def add_cc_mapping(self, mapping: MidiMapping) -> None:
        """Ajoute un mappage de contrôleur MIDI"""
        self.cc_mappings[mapping.cc_number] = mapping
        
    def remove_cc_mapping(self, cc_number: int) -> None:
        """Supprime un mappage de contrôleur MIDI"""
        if cc_number in self.cc_mappings:
            del self.cc_mappings[cc_number]
    
    def handle_midi_message(self, message: List[int]) -> None:
        """Traite un message MIDI"""
        if not message or len(message) < 3:
            return
            
        status, data1, data2 = message
        
        # Type de message (4 bits de poids fort)
        msg_type = status & 0xF0
        
        # Canal MIDI (4 bits de poids faible)
        channel = status & 0x0F
        
        if msg_type == MIDI_NOTE_ON and data2 > 0:
            # Note activée
            self._handle_note_on(data1, data2, channel)
            
        elif msg_type == MIDI_NOTE_OFF or (msg_type == MIDI_NOTE_ON and data2 == 0):
            # Note désactivée
            self._handle_note_off(data1, data2, channel)
            
        elif msg_type == MIDI_CC:
            # Contrôleur continu
            cc_number = data1
            cc_value = data2
            self._handle_cc(cc_number, cc_value, channel)
            
        elif msg_type == MIDI_PITCH_BEND:
            # Pitch bend
            lsb = data1
            msb = data2
            value = (msb << 7) | lsb
            self._handle_pitch_bend(value, channel)
    
    def _handle_note_on(self, note: int, velocity: int, channel: int) -> None:
        """Traite l'activation d'une note"""
        # Mettre à jour l'état des notes
        self.note_mapping.note_on(note)
        
        # Exécuter les callbacks
        for callback in self.note_callbacks:
            callback(note, True, velocity)
        
        if self.mode == MidiMode.PHRASES:
            # Déclencher une phrase si mappée
            content = self.note_mapping.get_content(note)
            if content:
                logger.info(f"Note {note} déclenchant: {content}")
                self._trigger_parameter("content", content)
    
    def _handle_note_off(self, note: int, velocity: int, channel: int) -> None:
        """Traite la désactivation d'une note"""
        # Mettre à jour l'état des notes
        self.note_mapping.note_off(note)
        
        # Exécuter les callbacks
        for callback in self.note_callbacks:
            callback(note, False, velocity)
    
    def _handle_cc(self, cc_number: int, cc_value: int, channel: int) -> None:
        """Traite un message de contrôleur continu"""
        # Cas spéciaux
        if cc_number == 64:  # Sustain pedal
            self.note_mapping.set_sustain(cc_value >= 64)
            return
            
        # Mappage standard
        if cc_number in self.cc_mappings:
            mapping = self.cc_mappings[cc_number]
            value = mapping.convert_value(cc_value)
            
            # Mettre à jour le paramètre
            self.parameters[mapping.parameter] = value
            
            # Déclencher les callbacks
            self._trigger_parameter(mapping.parameter, value)
    
    def _handle_pitch_bend(self, value: int, channel: int) -> None:
        """Traite un message de pitch bend"""
        # Convertir la valeur (0-16383) en pitch (-2 à +2 tons)
        normalized = (value / 8192.0) - 1.0  # -1.0 à +1.0
        pitch_value = normalized * 2.0  # -2.0 à +2.0 tons
        
        # Convertir les tons en demi-tons
        semitones = pitch_value * 12.0
        
        # Mettre à jour le paramètre
        self.parameters["pitch"] = semitones
        
        # Déclencher les callbacks
        self._trigger_parameter("pitch", semitones)
    
    def register_parameter_callback(self, parameter: str, callback: Callable[[str, float], None]) -> None:
        """Enregistre un callback pour un changement de paramètre"""
        if parameter not in self.parameter_callbacks:
            self.parameter_callbacks[parameter] = []
            
        self.parameter_callbacks[parameter].append(callback)
    
    def register_note_callback(self, callback: Callable[[int, bool, int], None]) -> None:
        """Enregistre un callback pour les événements de notes"""
        self.note_callbacks.append(callback)
    
    def _trigger_parameter(self, parameter: str, value: Any) -> None:
        """Déclenche les callbacks pour un paramètre"""
        # Callbacks spécifiques au paramètre
        if parameter in self.parameter_callbacks:
            for callback in self.parameter_callbacks[parameter]:
                callback(parameter, value)
                
        # Callbacks généraux (pour tous les paramètres)
        if "*" in self.parameter_callbacks:
            for callback in self.parameter_callbacks["*"]:
                callback(parameter, value)
    
    def get_parameter(self, parameter: str) -> float:
        """Obtient la valeur actuelle d'un paramètre"""
        return self.parameters.get(parameter, 0.0)
    
    def set_parameter(self, parameter: str, value: float) -> None:
        """Définit la valeur d'un paramètre et déclenche les callbacks"""
        self.parameters[parameter] = value
        self._trigger_parameter(parameter, value)
    
    def start_lfo(self, parameter: str, min_value: float, max_value: float, 
                 frequency: float, waveform: str = "sine") -> None:
        """Démarre un LFO (Low Frequency Oscillator) sur un paramètre"""
        if self.modulation_thread and self.modulation_thread.is_alive():
            # Arrêter l'ancien LFO
            self.stop_lfo()
            
        # Réinitialiser l'événement d'arrêt
        self.modulation_stop_event.clear()
        
        # Démarrer le thread LFO
        self.modulation_thread = threading.Thread(
            target=self._lfo_thread,
            args=(parameter, min_value, max_value, frequency, waveform),
            daemon=True
        )
        self.modulation_thread.start()
    
    def stop_lfo(self) -> None:
        """Arrête le LFO en cours"""
        if self.modulation_thread and self.modulation_thread.is_alive():
            self.modulation_stop_event.set()
            self.modulation_thread.join(timeout=1.0)
            self.modulation_thread = None
    
    def _lfo_thread(self, parameter: str, min_value: float, max_value: float, 
                   frequency: float, waveform: str) -> None:
        """Thread de génération LFO"""
        import math
        
        # Calculer la période en secondes
        period = 1.0 / frequency
        
        # Amplitude et offset
        amplitude = (max_value - min_value) / 2.0
        offset = min_value + amplitude
        
        # Boucle de modulation
        start_time = time.time()
        while not self.modulation_stop_event.is_set():
            # Calculer le temps relatif dans la période
            current_time = time.time()
            relative_time = ((current_time - start_time) % period) / period
            
            # Calculer la valeur selon la forme d'onde
            if waveform == "sine":
                value = offset + amplitude * math.sin(relative_time * 2 * math.pi)
            elif waveform == "triangle":
                if relative_time < 0.5:
                    # Phase montante
                    normalized = relative_time * 2
                else:
                    # Phase descendante
                    normalized = 2 - relative_time * 2
                value = min_value + (max_value - min_value) * normalized
            elif waveform == "saw":
                value = min_value + (max_value - min_value) * relative_time
            elif waveform == "square":
                value = max_value if relative_time < 0.5 else min_value
            else:
                # Par défaut: sinusoïdale
                value = offset + amplitude * math.sin(relative_time * 2 * math.pi)
            
            # Mettre à jour le paramètre
            self.set_parameter(parameter, value)
            
            # Pause courte
            time.sleep(0.01)  # 10ms de pas, suffisant pour une modulation fluide


# Créer une instance singleton
midi_control_engine = MidiControlEngine() 