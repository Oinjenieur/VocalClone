"""
Module de support pour la langue coréenne dans Bark TTS.
"""

import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

class KoreanLanguageSupport:
    """Classe pour gérer le support de la langue coréenne dans Bark"""
    
    # Dictionnaire de correspondance des phonèmes coréens
    KOREAN_PHONEMES = {
        # Consonnes initiales
        'ㄱ': 'k', 'ㄴ': 'n', 'ㄷ': 't', 'ㄹ': 'l', 'ㅁ': 'm',
        'ㅂ': 'p', 'ㅅ': 's', 'ㅇ': '', 'ㅈ': 'ch', 'ㅊ': 'ch',
        'ㅋ': 'k', 'ㅌ': 't', 'ㅍ': 'p', 'ㅎ': 'h',
        
        # Voyelles
        'ㅏ': 'a', 'ㅑ': 'ya', 'ㅓ': 'eo', 'ㅕ': 'yeo', 'ㅗ': 'o',
        'ㅛ': 'yo', 'ㅜ': 'u', 'ㅠ': 'yu', 'ㅡ': 'eu', 'ㅣ': 'i',
        
        # Consonnes finales
        'ㄱ': 'k', 'ㄴ': 'n', 'ㄷ': 't', 'ㄹ': 'l', 'ㅁ': 'm',
        'ㅂ': 'p', 'ㅅ': 't', 'ㅇ': 'ng', 'ㅈ': 't', 'ㅊ': 't',
        'ㅋ': 'k', 'ㅌ': 't', 'ㅍ': 'p', 'ㅎ': 't'
    }
    
    # Règles de liaison phonétique
    LIAISON_RULES = {
        'ㄱㅇ': 'g', 'ㄴㅇ': 'n', 'ㄷㅇ': 'd', 'ㄹㅇ': 'r',
        'ㅁㅇ': 'm', 'ㅂㅇ': 'b', 'ㅅㅇ': 's', 'ㅈㅇ': 'j',
        'ㅊㅇ': 'ch', 'ㅋㅇ': 'k', 'ㅌㅇ': 't', 'ㅍㅇ': 'p',
        'ㅎㅇ': 'h'
    }
    
    @staticmethod
    def convert_to_romanization(text: str) -> str:
        """Convertit le texte coréen en romanisation"""
        try:
            # Nettoyer le texte
            text = text.strip()
            
            # Convertir chaque caractère
            romanized = []
            for char in text:
                if char in KoreanLanguageSupport.KOREAN_PHONEMES:
                    romanized.append(KoreanLanguageSupport.KOREAN_PHONEMES[char])
                else:
                    romanized.append(char)
            
            return ''.join(romanized)
            
        except Exception as e:
            logger.error(f"Erreur lors de la romanisation: {e}", exc_info=True)
            return text
    
    @staticmethod
    def apply_liaison_rules(text: str) -> str:
        """Applique les règles de liaison phonétique"""
        try:
            # Convertir en liste de caractères
            chars = list(text)
            result = []
            
            # Appliquer les règles de liaison
            i = 0
            while i < len(chars) - 1:
                pair = chars[i] + chars[i + 1]
                if pair in KoreanLanguageSupport.LIAISON_RULES:
                    result.append(KoreanLanguageSupport.LIAISON_RULES[pair])
                    i += 2
                else:
                    result.append(chars[i])
                    i += 1
            
            # Ajouter le dernier caractère si nécessaire
            if i < len(chars):
                result.append(chars[i])
            
            return ''.join(result)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'application des règles de liaison: {e}", exc_info=True)
            return text
    
    @staticmethod
    def prepare_for_bark(text: str) -> str:
        """Prépare le texte coréen pour Bark"""
        try:
            # Convertir en romanisation
            romanized = KoreanLanguageSupport.convert_to_romanization(text)
            
            # Appliquer les règles de liaison
            with_liaison = KoreanLanguageSupport.apply_liaison_rules(romanized)
            
            # Ajouter des marqueurs de prosodie
            prosody_markers = re.sub(r'([.!?])', r' \1 ', with_liaison)
            prosody_markers = re.sub(r'\s+', ' ', prosody_markers)
            
            return prosody_markers.strip()
            
        except Exception as e:
            logger.error(f"Erreur lors de la préparation pour Bark: {e}", exc_info=True)
            return text
    
    @staticmethod
    def get_korean_speaker_prompt() -> str:
        """Retourne le prompt pour un locuteur coréen"""
        return "[ko_speaker_0]"
    
    @staticmethod
    def get_korean_emotion_prompts() -> Dict[str, str]:
        """Retourne les prompts d'émotion en coréen"""
        return {
            "happy": "[ko_speaker_0][happy]",
            "sad": "[ko_speaker_0][sad]",
            "angry": "[ko_speaker_0][angry]",
            "neutral": "[ko_speaker_0][neutral]",
            "surprised": "[ko_speaker_0][surprised]",
            "fearful": "[ko_speaker_0][fearful]",
            "disgusted": "[ko_speaker_0][disgusted]"
        }
    
    @staticmethod
    def validate_korean_text(text: str) -> Tuple[bool, str]:
        """Valide le texte coréen et retourne un message d'erreur si nécessaire"""
        try:
            # Vérifier si le texte est vide
            if not text.strip():
                return False, "Le texte ne peut pas être vide"
            
            # Vérifier si le texte contient des caractères coréens
            korean_pattern = re.compile(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F\uA960-\uA97F\uD7B0-\uD7FF]')
            if not korean_pattern.search(text):
                return False, "Le texte doit contenir des caractères coréens"
            
            # Vérifier la longueur maximale
            if len(text) > 1000:
                return False, "Le texte est trop long (maximum 1000 caractères)"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation du texte coréen: {e}", exc_info=True)
            return False, f"Erreur de validation: {str(e)}" 