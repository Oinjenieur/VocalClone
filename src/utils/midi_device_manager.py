"""
Gestionnaire de périphériques MIDI pour l'application.

Ce module fournit une interface pour gérer les périphériques MIDI,
détecter les entrées/sorties disponibles et traiter les événements MIDI.
"""

import logging
import time
from typing import List, Dict, Optional, Callable

# Configuration du logger
logger = logging.getLogger(__name__)

# Classe de remplacement pour simuler rtmidi si non disponible
class DummyMidiIn:
    """Classe simulant MidiIn lorsque rtmidi n'est pas disponible"""
    def __init__(self, *args, **kwargs):
        logger.warning("Utilisation de MidiIn simulé (rtmidi non disponible)")
    
    def get_ports(self):
        """Retourne une liste vide de ports"""
        return []
    
    def open_port(self, *args, **kwargs):
        """Simule l'ouverture d'un port"""
        logger.warning("Tentative d'ouverture d'un port MIDI simulé")
        return False
    
    def close_port(self):
        """Simule la fermeture d'un port"""
        pass
    
    def set_callback(self, callback):
        """Simule la définition d'un callback"""
        pass
    
    def cancel_callback(self):
        """Simule l'annulation d'un callback"""
        pass


class DummyMidiOut:
    """Classe simulant MidiOut lorsque rtmidi n'est pas disponible"""
    def __init__(self, *args, **kwargs):
        logger.warning("Utilisation de MidiOut simulé (rtmidi non disponible)")
    
    def get_ports(self):
        """Retourne une liste vide de ports"""
        return []
    
    def open_port(self, *args, **kwargs):
        """Simule l'ouverture d'un port"""
        logger.warning("Tentative d'ouverture d'un port MIDI simulé")
        return False
    
    def close_port(self):
        """Simule la fermeture d'un port"""
        pass
    
    def send_message(self, message):
        """Simule l'envoi d'un message"""
        logger.debug(f"Message MIDI simulé: {message}")
        pass


# Tentative d'importation de rtmidi
try:
    import rtmidi
    
    # Vérifier que les classes MidiIn et MidiOut sont disponibles
    if not hasattr(rtmidi, 'MidiIn') or not hasattr(rtmidi, 'MidiOut'):
        logger.error("La version de rtmidi ne contient pas les classes MidiIn/MidiOut")
        rtmidi.MidiIn = DummyMidiIn
        rtmidi.MidiOut = DummyMidiOut
        RTMIDI_AVAILABLE = False
    else:
        RTMIDI_AVAILABLE = True
        
except ImportError:
    # Créer un module rtmidi simulé
    logger.warning("Module rtmidi non disponible, utilisation de classes simulées")
    import types
    rtmidi = types.ModuleType('rtmidi')
    rtmidi.MidiIn = DummyMidiIn
    rtmidi.MidiOut = DummyMidiOut
    RTMIDI_AVAILABLE = False


class MidiDeviceManager:
    """Gestionnaire de périphériques MIDI"""
    
    def __init__(self):
        self.input_ports = []
        self.output_ports = []
        self.input_devices = {}
        self.output_devices = {}
        self.active_input = None
        self.active_output = None
        self.midi_callbacks = []
        self.rtmidi_available = RTMIDI_AVAILABLE
        
        if not self.rtmidi_available:
            logger.warning("RTMidi non disponible, fonctionnement en mode de compatibilité limité")
    
    def scan_devices(self) -> None:
        """Détecte les périphériques MIDI disponibles"""
        try:
            # Créer des objets pour détecter les ports
            midi_in = rtmidi.MidiIn()
            midi_out = rtmidi.MidiOut()
            
            # Récupérer les ports disponibles
            self.input_ports = midi_in.get_ports()
            self.output_ports = midi_out.get_ports()
            
            # Libérer les ressources
            del midi_in
            del midi_out
            
            logger.info(f"Ports MIDI d'entrée détectés: {self.input_ports}")
            logger.info(f"Ports MIDI de sortie détectés: {self.output_ports}")
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la détection des périphériques MIDI: {e}")
            self.input_ports = []
            self.output_ports = []
            return False
    
    def get_input_ports(self) -> List[str]:
        """Retourne la liste des ports d'entrée MIDI disponibles"""
        return self.input_ports
    
    def get_output_ports(self) -> List[str]:
        """Retourne la liste des ports de sortie MIDI disponibles"""
        return self.output_ports
    
    def open_input(self, port_name: str) -> bool:
        """Ouvre un port d'entrée MIDI spécifique"""
        try:
            # Vérifier si le port existe
            if port_name not in self.input_ports:
                logger.warning(f"Port d'entrée {port_name} non trouvé")
                return False
            
            # Fermer le port actif si nécessaire
            if self.active_input:
                self.close_input()
            
            # Ouvrir le nouveau port
            midi_in = rtmidi.MidiIn()
            port_index = self.input_ports.index(port_name)
            midi_in.open_port(port_index)
            
            # Configurer le callback
            midi_in.set_callback(self._handle_midi_input)
            
            # Enregistrer le périphérique actif
            self.active_input = port_name
            self.input_devices[port_name] = midi_in
            
            logger.info(f"Port d'entrée MIDI {port_name} ouvert")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ouverture du port d'entrée {port_name}: {e}")
            return False
    
    def close_input(self) -> bool:
        """Ferme le port d'entrée MIDI actif"""
        if not self.active_input or self.active_input not in self.input_devices:
            return False
        
        try:
            # Récupérer l'objet
            midi_in = self.input_devices[self.active_input]
            
            # Annuler le callback
            midi_in.cancel_callback()
            
            # Fermer le port
            midi_in.close_port()
            
            # Supprimer de la liste des périphériques actifs
            del self.input_devices[self.active_input]
            self.active_input = None
            
            logger.info("Port d'entrée MIDI fermé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture du port d'entrée: {e}")
            return False
    
    def open_output(self, port_name: str) -> bool:
        """Ouvre un port de sortie MIDI spécifique"""
        try:
            # Vérifier si le port existe
            if port_name not in self.output_ports:
                logger.warning(f"Port de sortie {port_name} non trouvé")
                return False
            
            # Fermer le port actif si nécessaire
            if self.active_output:
                self.close_output()
            
            # Ouvrir le nouveau port
            midi_out = rtmidi.MidiOut()
            port_index = self.output_ports.index(port_name)
            midi_out.open_port(port_index)
            
            # Enregistrer le périphérique actif
            self.active_output = port_name
            self.output_devices[port_name] = midi_out
            
            logger.info(f"Port de sortie MIDI {port_name} ouvert")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ouverture du port de sortie {port_name}: {e}")
            return False
    
    def close_output(self) -> bool:
        """Ferme le port de sortie MIDI actif"""
        if not self.active_output or self.active_output not in self.output_devices:
            return False
        
        try:
            # Récupérer l'objet
            midi_out = self.output_devices[self.active_output]
            
            # Fermer le port
            midi_out.close_port()
            
            # Supprimer de la liste des périphériques actifs
            del self.output_devices[self.active_output]
            self.active_output = None
            
            logger.info("Port de sortie MIDI fermé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture du port de sortie: {e}")
            return False
    
    def send_midi(self, message: List[int]) -> bool:
        """Envoie un message MIDI au port de sortie actif"""
        if not self.active_output or self.active_output not in self.output_devices:
            logger.warning("Aucun port de sortie MIDI actif pour envoyer le message")
            return False
        
        try:
            # Récupérer l'objet
            midi_out = self.output_devices[self.active_output]
            
            # Envoyer le message
            midi_out.send_message(message)
            
            logger.debug(f"Message MIDI envoyé: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message MIDI: {e}")
            return False
    
    def register_callback(self, callback: Callable) -> None:
        """Enregistre une fonction de callback pour les événements MIDI"""
        if callback not in self.midi_callbacks:
            self.midi_callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable) -> None:
        """Supprime une fonction de callback"""
        if callback in self.midi_callbacks:
            self.midi_callbacks.remove(callback)
    
    def _handle_midi_input(self, message, timestamp):
        """Gère les messages MIDI entrants et les transmet aux callbacks"""
        midi_data = message[0]
        logger.debug(f"Message MIDI reçu: {midi_data} à {timestamp}")
        
        # Transmettre le message à tous les callbacks enregistrés
        for callback in self.midi_callbacks:
            try:
                callback(midi_data, timestamp)
            except Exception as e:
                logger.error(f"Erreur dans le callback MIDI: {e}")
    
    def is_available(self) -> bool:
        """Vérifie si RTMIDI est disponible"""
        return self.rtmidi_available


# Instance singleton du gestionnaire MIDI
midi_manager = MidiDeviceManager() 