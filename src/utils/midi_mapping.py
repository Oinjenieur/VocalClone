"""
Module pour le mapping des contrôleurs MIDI.

Ce module gère l'association entre les événements MIDI (notes, CC, etc.)
et les fonctions de l'application, ainsi que le stockage et le chargement
de ces associations.
"""

import json
import os
from pathlib import Path


class MidiMapping:
    """Classe gérant le mapping des contrôleurs MIDI vers les fonctions de l'application"""
    
    # Catégories de fonctions disponibles
    CATEGORIES = {
        "modulation": "Modulation",
        "trigger": "Déclenchement",
        "transport": "Transport",
        "view": "Affichage"
    }
    
    # Fonctions disponibles par catégorie
    FUNCTIONS = {
        "modulation": {
            "pitch": "Hauteur",
            "formant": "Formant",
            "vibrato": "Vibrato",
            "tremolo": "Tremolo",
            "distortion": "Distorsion",
            "reset": "Réinitialiser"
        },
        "trigger": {
            "trigger_1": "Phrase 1",
            "trigger_2": "Phrase 2",
            "trigger_3": "Phrase 3",
            "trigger_4": "Phrase 4",
            "trigger_5": "Phrase 5"
        },
        "transport": {
            "play": "Lecture",
            "stop": "Arrêt",
            "record": "Enregistrement",
            "rewind": "Retour",
            "forward": "Avance"
        },
        "view": {
            "next_tab": "Onglet suivant",
            "prev_tab": "Onglet précédent",
            "zoom_in": "Zoom avant",
            "zoom_out": "Zoom arrière"
        }
    }
    
    # Types d'événements MIDI
    TYPES = {
        "note": "Note",
        "cc": "Contrôleur",
        "pb": "Pitch Bend",
        "pc": "Program Change"
    }
    
    def __init__(self, config_path=None):
        """
        Initialise le mapping MIDI
        
        Args:
            config_path (str, optional): Chemin vers le fichier de configuration
        """
        # Structure des mappings: {type: {identifiant: fonction}}
        # type: "note", "cc", "pb", "pc"
        # identifiant: "canal:valeur" ou "canal" pour pb
        # fonction: "categorie:fonction"
        self.mappings = {
            "note": {},
            "cc": {},
            "pb": {},
            "pc": {}
        }
        
        # Structure des phrases: {trigger_id: {text: "", voice: ""}}
        self.phrases = {
            "trigger_1": {"text": "", "voice": None},
            "trigger_2": {"text": "", "voice": None},
            "trigger_3": {"text": "", "voice": None},
            "trigger_4": {"text": "", "voice": None},
            "trigger_5": {"text": "", "voice": None}
        }
        
        # Mode d'apprentissage
        self.learning_mode = False
        self.learning_function = None
        
        # Charger la configuration si un chemin est spécifié
        self.config_path = config_path
        if config_path:
            self.load()
        else:
            # Chemin par défaut dans le dossier de l'utilisateur
            user_dir = str(Path.home())
            self.config_path = os.path.join(user_dir, ".midi_mappings.json")
            
    def load(self):
        """Charge les mappings depuis le fichier de configuration"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if "mappings" in data:
                        self.mappings = data["mappings"]
                        
                    if "phrases" in data:
                        self.phrases = data["phrases"]
                        
                print(f"✅ Mappings MIDI chargés depuis {self.config_path}")
                return True
                
        except Exception as e:
            print(f"❌ Erreur lors du chargement des mappings MIDI: {e}")
            
        return False
        
    def save(self):
        """Enregistre les mappings dans le fichier de configuration"""
        try:
            data = {
                "mappings": self.mappings,
                "phrases": self.phrases
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Mappings MIDI enregistrés dans {self.config_path}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement des mappings MIDI: {e}")
            
        return False
        
    def clear_all_mappings(self):
        """Efface tous les mappings"""
        self.mappings = {
            "note": {},
            "cc": {},
            "pb": {},
            "pc": {}
        }
        return True
        
    def clear_mapping(self, midi_type, identifier):
        """
        Efface un mapping spécifique
        
        Args:
            midi_type (str): Type d'événement MIDI ("note", "cc", "pb", "pc")
            identifier (str): Identifiant du contrôleur
            
        Returns:
            bool: True si le mapping a été effacé, False sinon
        """
        if midi_type in self.mappings and identifier in self.mappings[midi_type]:
            del self.mappings[midi_type][identifier]
            return True
            
        return False
        
    def start_learning(self, category, function):
        """
        Démarre le mode d'apprentissage pour une fonction spécifique
        
        Args:
            category (str): Catégorie de la fonction
            function (str): Identifiant de la fonction
            
        Returns:
            bool: True si le mode d'apprentissage a été démarré, False sinon
        """
        self.learning_mode = True
        self.learning_function = f"{category}:{function}"
        print(f"🎹 Mode d'apprentissage activé pour {self.learning_function}")
        return True
        
    def stop_learning(self):
        """Arrête le mode d'apprentissage"""
        if self.learning_mode:
            self.learning_mode = False
            self.learning_function = None
            print("🎹 Mode d'apprentissage désactivé")
            
    def assign_note(self, note, channel=0):
        """
        Assigne une note à la fonction en cours d'apprentissage
        
        Args:
            note (int): Numéro de note MIDI
            channel (int, optional): Canal MIDI
            
        Returns:
            bool: True si l'assignation a réussi, False sinon
        """
        if not self.learning_mode or not self.learning_function:
            return False
            
        identifier = f"{channel}:{note}"
        self.mappings["note"][identifier] = self.learning_function
        print(f"✅ Note {note} sur canal {channel} assignée à {self.learning_function}")
        
        self.save()
        return True
        
    def assign_cc(self, cc, channel=0):
        """
        Assigne un contrôleur à la fonction en cours d'apprentissage
        
        Args:
            cc (int): Numéro de contrôleur MIDI
            channel (int, optional): Canal MIDI
            
        Returns:
            bool: True si l'assignation a réussi, False sinon
        """
        if not self.learning_mode or not self.learning_function:
            return False
            
        identifier = f"{channel}:{cc}"
        self.mappings["cc"][identifier] = self.learning_function
        print(f"✅ CC {cc} sur canal {channel} assigné à {self.learning_function}")
        
        self.save()
        return True
        
    def assign_pb(self, channel=0):
        """
        Assigne le pitch bend à la fonction en cours d'apprentissage
        
        Args:
            channel (int, optional): Canal MIDI
            
        Returns:
            bool: True si l'assignation a réussi, False sinon
        """
        if not self.learning_mode or not self.learning_function:
            return False
            
        identifier = str(channel)
        self.mappings["pb"][identifier] = self.learning_function
        print(f"✅ Pitch Bend sur canal {channel} assigné à {self.learning_function}")
        
        self.save()
        return True
        
    def assign_pc(self, program, channel=0):
        """
        Assigne un changement de programme à la fonction en cours d'apprentissage
        
        Args:
            program (int): Numéro de programme MIDI
            channel (int, optional): Canal MIDI
            
        Returns:
            bool: True si l'assignation a réussi, False sinon
        """
        if not self.learning_mode or not self.learning_function:
            return False
            
        identifier = f"{channel}:{program}"
        self.mappings["pc"][identifier] = self.learning_function
        print(f"✅ Program Change {program} sur canal {channel} assigné à {self.learning_function}")
        
        self.save()
        return True
        
    def get_note_function(self, note, channel=0):
        """
        Récupère la fonction associée à une note
        
        Args:
            note (int): Numéro de note MIDI
            channel (int, optional): Canal MIDI
            
        Returns:
            str: Identifiant de la fonction ou None si aucune association
        """
        identifier = f"{channel}:{note}"
        return self.mappings["note"].get(identifier)
        
    def get_cc_function(self, cc, channel=0):
        """
        Récupère la fonction associée à un contrôleur
        
        Args:
            cc (int): Numéro de contrôleur MIDI
            channel (int, optional): Canal MIDI
            
        Returns:
            str: Identifiant de la fonction ou None si aucune association
        """
        identifier = f"{channel}:{cc}"
        return self.mappings["cc"].get(identifier)
        
    def get_pb_function(self, channel=0):
        """
        Récupère la fonction associée au pitch bend
        
        Args:
            channel (int, optional): Canal MIDI
            
        Returns:
            str: Identifiant de la fonction ou None si aucune association
        """
        identifier = str(channel)
        return self.mappings["pb"].get(identifier)
        
    def get_pc_function(self, program, channel=0):
        """
        Récupère la fonction associée à un changement de programme
        
        Args:
            program (int): Numéro de programme MIDI
            channel (int, optional): Canal MIDI
            
        Returns:
            str: Identifiant de la fonction ou None si aucune association
        """
        identifier = f"{channel}:{program}"
        return self.mappings["pc"].get(identifier)
        
    def parse_function(self, function_id):
        """
        Décompose un identifiant de fonction en catégorie et fonction
        
        Args:
            function_id (str): Identifiant de fonction au format "categorie:fonction"
            
        Returns:
            tuple: (catégorie, fonction) ou (None, None) si le format est invalide
        """
        if not function_id or ":" not in function_id:
            return None, None
            
        return function_id.split(":", 1)
        
    def set_phrase(self, trigger_id, text, voice=None):
        """
        Définit le texte et la voix pour une phrase
        
        Args:
            trigger_id (str): Identifiant de la phrase
            text (str): Texte de la phrase
            voice (str, optional): Identifiant de la voix
            
        Returns:
            bool: True si la phrase a été définie, False sinon
        """
        if trigger_id in self.phrases:
            self.phrases[trigger_id] = {
                "text": text,
                "voice": voice
            }
            
            self.save()
            return True
            
        return False
        
    def get_phrase(self, trigger_id):
        """
        Récupère une phrase
        
        Args:
            trigger_id (str): Identifiant de la phrase
            
        Returns:
            dict: Dictionnaire contenant le texte et la voix, ou {} si aucune phrase trouvée
        """
        return self.phrases.get(trigger_id, {}) 