#!/usr/bin/env python3
"""
OpenVoice - Application de synthèse vocale avec interface MIDI.

Ce fichier est le point d'entrée principal de l'application.
Il peut charger soit la version française, soit la version anglaise
selon les préférences de l'utilisateur.
"""

import sys
import os
import argparse

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Voice synthesis application with MIDI control")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with more logs")
    parser.add_argument("--check-midi", action="store_true", help="Check MIDI devices and exit")
    parser.add_argument("--check-models", action="store_true", help="Check available models and exit")
    parser.add_argument("--tab", help="Select a specific tab to open")
    parser.add_argument("--language", choices=["fr", "en"], default="en", 
                        help="Select language: fr (French) or en (English)")
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    
    # Determine which language version to use
    if args.language.lower() == "fr":
        print("Démarrage de la version française...")
        # Import and run French version
        try:
            from src.main_french import main as main_french
            main_french()
        except ImportError:
            # Try a relative import if we're already in the src directory
            try:
                from main_french import main as main_french
                main_french()
            except Exception as e:
                print(f"Erreur lors du chargement de la version française: {e}")
                sys.exit(1)
    else:
        print("Starting English version...")
        # Import and run English version
        try:
            from src.main_english import main as main_english
            main_english()
        except ImportError:
            # Try a relative import if we're already in the src directory
            try:
                from main_english import main as main_english
                main_english()
            except Exception as e:
                print(f"Error loading English version: {e}")
                sys.exit(1)

if __name__ == "__main__":
    main() 