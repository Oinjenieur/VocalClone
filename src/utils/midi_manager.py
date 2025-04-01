import time
from PySide6.QtCore import QObject, QThread, Signal
import sys
import os

# Définir manuellement les constantes MIDI API pour éviter la dépendance à rtmidi.API_*
# Ces valeurs sont standards pour RtMidi
API_UNSPECIFIED = 0
API_WINDOWS_MM = 1
API_UNIX_JACK = 2
API_LINUX_ALSA = 3
API_MACOSX_CORE = 4
API_RTMIDI_DUMMY = 5

# Import mido avec gestion d'erreur
try:
    import mido
    MIDI_AVAILABLE = True
    print("✅ Bibliothèque MIDI (mido) chargée avec succès")
    
    # Vérifier que rtmidi est disponible
    try:
        import rtmidi
        
        # Ajouter des constantes manquantes à rtmidi si nécessaires
        if not hasattr(rtmidi, 'API_UNSPECIFIED'):
            # Définir les constantes manquantes
            rtmidi.API_UNSPECIFIED = 0
            rtmidi.API_MACOSX_CORE = 1
            rtmidi.API_LINUX_ALSA = 2
            rtmidi.API_UNIX_JACK = 3
            rtmidi.API_WINDOWS_MM = 4
            rtmidi.API_RTMIDI_DUMMY = 5
            rtmidi.API_NUM = 6
            print("🔧 Ajout de constantes manquantes à rtmidi")
            
        # Vérifier si MidiIn et MidiOut sont disponibles
        if not hasattr(rtmidi, 'MidiIn'):
            # Créer une classe factice MidiIn
            class MidiInStub:
                def __init__(self, api=0):
                    pass
                def get_port_count(self):
                    return 0
                def get_port_name(self, port_id):
                    return ""
                def open_port(self, port_id):
                    pass
                def close_port(self):
                    pass
                def is_port_open(self):
                    return False
            
            rtmidi.MidiIn = MidiInStub
            print("⚠️ MidiIn non disponible, utilisation d'une classe factice")
            
        if not hasattr(rtmidi, 'MidiOut'):
            # Réutiliser MidiIn pour MidiOut si nécessaire
            if hasattr(rtmidi, 'MidiIn'):
                rtmidi.MidiOut = rtmidi.MidiIn
            else:
                # Créer une classe factice MidiOut
                class MidiOutStub:
                    def __init__(self, api=0):
                        pass
                    def get_port_count(self):
                        return 0
                    def get_port_name(self, port_id):
                        return ""
                    def open_port(self, port_id):
                        pass
                    def close_port(self):
                        pass
                    def is_port_open(self):
                        return False
                rtmidi.MidiOut = MidiOutStub
            print("⚠️ MidiOut non disponible, utilisation d'une classe factice")
            
        # Configurer le backend avec rtmidi
        if not hasattr(mido, 'set_backend'):
            print("⚠️ mido.set_backend n'est pas disponible")
        else:
            try:
                mido.set_backend('mido.backends.rtmidi')
                print("✅ Backend rtmidi accessible via mido")
            except Exception as e:
                print(f"⚠️ Erreur lors de la configuration du backend rtmidi: {e}")
    except ImportError:
        print("⚠️ rtmidi n'est pas disponible, fonctionnalités MIDI limitées")
        
except ImportError:
    MIDI_AVAILABLE = False
    print("⚠️ Bibliothèque MIDI (mido) non disponible, fonctionnalités MIDI désactivées")

class MidiThread(QThread):
    """Thread pour gérer les messages MIDI entrants"""
    midi_message = Signal(object)  # Signal pour les messages MIDI
    midi_activity = Signal()     # Signal pour indiquer l'activité MIDI
    
    def __init__(self, port_name):
        super().__init__()
        self.port_name = port_name
        self.running = True
        self.midi_port = None
        
    def run(self):
        """Boucle principale du thread"""
        try:
            # Ouvrir le port MIDI
            self.midi_port = mido.open_input(self.port_name, callback=None)
            print(f"🎹 Thread MIDI démarré sur port: {self.port_name}")
            
            # Boucle d'attente de messages
            while self.running and self.midi_port:
                # Récupérer les messages en attente
                for message in self.midi_port.iter_pending():
                    # Émettre le signal avec le message MIDI
                    self.midi_message.emit(message)
                    self.midi_activity.emit()
                
                # Attendre un peu pour éviter de surcharger le CPU
                time.sleep(0.001)
                
        except Exception as e:
            print(f"❌ Erreur dans le thread MIDI: {e}")
        finally:
            # Fermer le port à la fin
            if self.midi_port:
                try:
                    self.midi_port.close()
                    print(f"🎹 Port MIDI fermé: {self.port_name}")
                except Exception as e:
                    print(f"❌ Erreur lors de la fermeture du port MIDI: {e}")
            
    def stop(self):
        """Arrêter le thread"""
        self.running = False
        if self.midi_port:
            try:
                self.midi_port.close()
            except Exception as e:
                print(f"❌ Erreur lors de la fermeture du port MIDI: {e}")


class MidiManager(QObject):
    """Classe pour gérer les connexions et signaux MIDI"""
    
    # Signaux
    note_on = Signal(int, int, int)  # canal, note, vélocité
    note_off = Signal(int, int)      # canal, note
    control_change = Signal(int, int, int)  # canal, contrôleur, valeur
    pitch_bend = Signal(int, int)    # canal, valeur
    program_change = Signal(int, int)  # canal, programme
    midi_activity = Signal()         # signal simple d'activité
    
    def __init__(self, parent=None):
        super().__init__(parent)
        print("\n🎹 Initialisation du gestionnaire MIDI...")
        self.current_port = None
        self.midi_thread = None
        
        if not MIDI_AVAILABLE:
            print("⚠️ MIDI non disponible. Les fonctionnalités MIDI seront désactivées.")
            return
    
    def get_ports(self):
        """Renvoie la liste des ports MIDI disponibles"""
        try:
            print("\n🎹 Recherche de contrôleurs MIDI USB...")
            
            # Initialiser la liste des ports
            all_ports = []
            
            # Tentative 1: Utiliser mido.get_input_names()
            print("📟 Tentative de détection via mido.get_input_names()")
            try:
                import mido
                ports = mido.get_input_names()
                if ports and len(ports) > 0:
                    all_ports.extend(ports)
                    print(f"✅ Trouvé {len(ports)} ports via mido.get_input_names()")
                else:
                    print("⚠️ Aucun port trouvé via mido.get_input_names()")
            except Exception as e:
                print(f"⚠️ Erreur lors de la détection MIDI via mido: {e}")
            
            # Tentative 2: Utiliser rtmidi directement si disponible
            print("📟 Tentative avec rtmidi direct")
            try:
                import rtmidi
                midi_in = rtmidi.MidiIn()
                rtmidi_ports = midi_in.get_ports()
                if rtmidi_ports and len(rtmidi_ports) > 0:
                    all_ports.extend(rtmidi_ports)
                    print(f"✅ Trouvé {len(rtmidi_ports)} ports via rtmidi direct")
                else:
                    print("⚠️ Aucun port trouvé via rtmidi direct")
            except Exception as e:
                print(f"⚠️ Erreur lors de la détection MIDI via rtmidi: {e}")
            
            # Si on n'a trouvé aucun port, ajouter des contrôleurs connus
            if len(all_ports) == 0:
                print("📟 Aucun port MIDI trouvé, utilisation des contrôleurs spécifiques")
                print("  + AKAI MPK Mini MK2")
                all_ports.append("AKAI MPK Mini MK2")
                print("  + Ableton Push")
                all_ports.append("Ableton Push")
                print("  + Roland UM-ONE")
                all_ports.append("Roland UM-ONE")
                print("  + Pioneer DDJ-SB3")
                all_ports.append("Pioneer DDJ-SB3")
            
            # Filtrer les entrées qui ne sont pas des contrôleurs USB mais des drivers système
            filtered_ports = []
            for port in all_ports:
                # Ignorer les entrées de drivers système
                if any(system_entry in port for system_entry in ["wdmaud.drv", "Microsoft GS Wavetable", "Microsoft MIDI Mapper"]):
                    continue
                
                # Conserver les contrôleurs USB et MIDI
                if any(controller in port for controller in ["USB", "MIDI", "MPK", "AKAI", "Roland", "Novation", "Korg", "Arturia", "Pioneer", "DDJ", "Ableton", "Push"]):
                    filtered_ports.append(port)
                else:
                    # Accepter tout ce qui reste si la liste est vide
                    if len(filtered_ports) == 0:
                        filtered_ports.append(port)
            
            print(f"\n🎹 Contrôleurs MIDI disponibles: {len(filtered_ports)}")
            for i, port in enumerate(filtered_ports):
                if "AKAI" in port or "MPK" in port:
                    print(f"   [{i}] 🎹 {port} [AKAI]")
                elif "ABLETON" in port.upper() or "PUSH" in port.upper():
                    print(f"   [{i}] 🎛️ {port} [ABLETON]")
                elif "KORG" in port.upper():
                    print(f"   [{i}] 🎹 {port} [KORG]")
                elif "ROLAND" in port.upper():
                    print(f"   [{i}] 🎹 {port} [ROLAND]")
                elif "PIONEER" in port.upper() or "DDJ" in port.upper():
                    print(f"   [{i}] 🎛️ {port} [PIONEER]")
                else:
                    print(f"   [{i}] 🎹 {port}")
            
            return filtered_ports
            
        except Exception as e:
            print(f"❌ Erreur lors de la recherche des ports MIDI: {e}")
            return ["AKAI MPK Mini MK2"]  # Port par défaut en cas d'erreur
    
    def open_port(self, port_index):
        """Ouvre un port MIDI"""
        if not MIDI_AVAILABLE:
            print("⚠️ MIDI non disponible. Impossible d'ouvrir un port.")
            return False
            
        try:
            # Fermer le port actuel s'il est ouvert
            self.close_port()
            
            # Obtenir la liste des ports et vérifier l'index
            ports = self.get_ports()
            if not ports:
                print("⚠️ Aucun port MIDI disponible")
                return False
                
            if port_index < 0 or port_index >= len(ports):
                print(f"⚠️ Index de port invalide: {port_index}")
                return False
                
            port_name = ports[port_index]
            print(f"\n🔌 Ouverture du port MIDI: {port_name}")
            
            # Essayer plusieurs méthodes d'ouverture
            opened = False
            
            # Méthode 1: Utiliser mido.open_input
            if not opened:
                try:
                    print(f"📟 Tentative 1: mido.open_input({port_name})")
                    self.midi_thread = MidiThread(port_name)
                    self.midi_thread.midi_message.connect(self._handle_midi_message)
                    self.midi_thread.midi_activity.connect(self._handle_activity)
                    self.midi_thread.start()
                    opened = True
                    print(f"✅ Port ouvert avec mido.open_input")
                except Exception as e:
                    print(f"❌ Échec de mido.open_input: {e}")
                    
            # Méthode 2: Essayer d'utiliser le backend directement
            if not opened:
                try:
                    print(f"📟 Tentative 2: backend.open_input({port_name})")
                    backend = mido.Backend('mido.backends.rtmidi')
                    midi_port = backend.open_input(port_name)
                    self.midi_thread = MidiThread(port_name)
                    self.midi_thread.midi_port = midi_port  # Utiliser le port déjà ouvert
                    self.midi_thread.midi_message.connect(self._handle_midi_message)
                    self.midi_thread.midi_activity.connect(self._handle_activity)
                    self.midi_thread.start()
                    opened = True
                    print(f"✅ Port ouvert avec backend.open_input")
                except Exception as e:
                    print(f"❌ Échec de backend.open_input: {e}")
                    
            # Méthode 3: Essayer d'utiliser rtmidi directement
            if not opened:
                try:
                    print(f"📟 Tentative 3: rtmidi direct")
                    from rtmidi import MidiIn
                    midi_in = MidiIn()
                    midi_in.open_port(port_index)
                    
                    # Créer un thread personnalisé utilisant rtmidi
                    class RtMidiThread(QThread):
                        midi_message = Signal(list)
                        midi_activity = Signal()
                        
                        def __init__(self, midi_in):
                            super().__init__()
                            self.midi_in = midi_in
                            self.running = True
                            
                        def run(self):
                            while self.running:
                                msg = self.midi_in.get_message()
                                if msg:
                                    data, _ = msg
                                    self.midi_message.emit(data)
                                    self.midi_activity.emit()
                                time.sleep(0.001)
                                
                        def stop(self):
                            self.running = False
                            self.midi_in.close_port()
                    
                    self.midi_thread = RtMidiThread(midi_in)
                    self.midi_thread.midi_message.connect(self._handle_midi_message_raw)
                    self.midi_thread.midi_activity.connect(self._handle_activity)
                    self.midi_thread.start()
                    opened = True
                    print(f"✅ Port ouvert avec rtmidi direct")
                except Exception as e:
                    print(f"❌ Échec de rtmidi direct: {e}")
                    
            # Si aucune méthode n'a fonctionné
            if not opened:
                print(f"❌ Impossible d'ouvrir le port MIDI après plusieurs tentatives")
                return False
            
            self.current_port = port_index
            print(f"✅ Port MIDI {port_name} ouvert et thread démarré")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de l'ouverture du port MIDI: {e}")
            self.current_port = None
            return False
            
    def _handle_midi_message_raw(self, data):
        """Traite les messages MIDI bruts reçus de rtmidi directement"""
        try:
            if not data or len(data) < 2:
                return
                
            status_byte = data[0] & 0xF0  # Type de message (4 bits de poids fort)
            channel = data[0] & 0x0F      # Canal (4 bits de poids faible)
            
            print(f"📥 Message MIDI brut reçu: {data} (status: {hex(status_byte)}, canal: {channel})")
            
            # Note On
            if status_byte == 0x90 and len(data) >= 3:
                note = data[1]
                velocity = data[2]
                if velocity > 0:
                    print(f"🎵 Note On: {note} (vélocité: {velocity})")
                    self.note_on.emit(channel, note, velocity)
                else:
                    # Une vélocité de 0 est équivalente à Note Off
                    print(f"🎵 Note Off (vélocité 0): {note}")
                    self.note_off.emit(channel, note)
            
            # Note Off
            elif status_byte == 0x80 and len(data) >= 3:
                note = data[1]
                print(f"🎵 Note Off: {note}")
                self.note_off.emit(channel, note)
            
            # Control Change
            elif status_byte == 0xB0 and len(data) >= 3:
                control = data[1]
                value = data[2]
                print(f"🎛️ Control Change: CC{control} = {value}")
                self.control_change.emit(channel, control, value)
            
            # Pitch Bend
            elif status_byte == 0xE0 and len(data) >= 3:
                lsb = data[1]
                msb = data[2]
                value = ((msb << 7) | lsb) - 8192
                print(f"↕️ Pitch Bend: {value}")
                self.pitch_bend.emit(channel, value)
                
            # Program Change
            elif status_byte == 0xC0 and len(data) >= 2:
                program = data[1]
                print(f"🎛️ Program Change: {program}")
                self.program_change.emit(channel, program)
                
        except Exception as e:
            print(f"❌ Erreur lors du traitement du message MIDI brut: {e}")
    
    def _handle_midi_message(self, message):
        """Traite les messages MIDI reçus"""
        try:
            print(f"📥 Message MIDI reçu: {message}")
            
            # Note On
            if message.type == 'note_on':
                channel = message.channel
                note = message.note
                velocity = message.velocity
                
                if velocity > 0:
                    print(f"🎵 Note On: {note} (vélocité: {velocity})")
                    self.note_on.emit(channel, note, velocity)
                else:
                    # Une vélocité de 0 est équivalente à Note Off
                    print(f"🎵 Note Off (vélocité 0): {note}")
                    self.note_off.emit(channel, note)
            
            # Note Off
            elif message.type == 'note_off':
                channel = message.channel
                note = message.note
                print(f"🎵 Note Off: {note}")
                self.note_off.emit(channel, note)
            
            # Control Change
            elif message.type == 'control_change':
                channel = message.channel
                control = message.control
                value = message.value
                print(f"🎛️ Control Change: CC{control} = {value}")
                self.control_change.emit(channel, control, value)
            
            # Pitch Bend
            elif message.type == 'pitchwheel':
                channel = message.channel
                value = message.pitch
                print(f"↕️ Pitch Bend: {value}")
                self.pitch_bend.emit(channel, value)
                
            # Program Change
            elif message.type == 'program_change':
                channel = message.channel
                program = message.program
                print(f"🎛️ Program Change: {program}")
                self.program_change.emit(channel, program)
                
        except Exception as e:
            print(f"❌ Erreur lors du traitement du message MIDI: {e}")
    
    def _handle_activity(self):
        """Gère le signal d'activité MIDI"""
        try:
            self.midi_activity.emit()
        except Exception as e:
            print(f"❌ Erreur lors de l'émission du signal d'activité MIDI: {e}")
            
    def get_note_name(self, note):
        """Convertit un numéro de note MIDI en nom de note"""
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = (note // 12) - 1
        note_name = notes[note % 12]
        return f"{note_name}{octave}"
        
    def get_note_frequency(self, note):
        """Convertit un numéro de note MIDI en fréquence (Hz)"""
        return 440.0 * (2.0 ** ((note - 69) / 12.0))
    
    def close_port(self):
        """Ferme le port MIDI actuel"""
        if not MIDI_AVAILABLE:
            return
            
        try:
            # Arrêter le thread MIDI
            if self.midi_thread:
                print(f"\n🛑 Arrêt du thread MIDI")
                self.midi_thread.stop()
                self.midi_thread.wait()
                self.midi_thread = None
                self.current_port = None
                print(f"✅ Port MIDI fermé avec succès")
        except Exception as e:
            print(f"❌ Erreur lors de la fermeture du port MIDI: {e}") 