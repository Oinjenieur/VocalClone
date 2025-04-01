from TTS.api import TTS
import json
import os

class LanguageManager:
    def __init__(self):
        self.tts = TTS()
        self.language_models = self._load_language_models()
        
    def _load_language_models(self):
        """Charge les modèles disponibles par langue."""
        models = {}
        available_models = self.tts.list_models()
        model_names = available_models.list_models()
        
        for model in model_names:
            # Ne garder que les modèles TTS
            if not model.startswith('tts_models/'):
                continue
                
            # Extraction de la langue du nom du modèle
            parts = model.split('/')
            if len(parts) >= 3:  # Assurons-nous d'avoir tts_models/lang/dataset
                lang = parts[1]
                if lang not in models:
                    models[lang] = []
                # Ajout du modèle avec un nom plus lisible
                display_name = f"{parts[2].capitalize()} ({parts[3] if len(parts) > 3 else 'default'})"
                models[lang].append({
                    'name': model,
                    'display_name': display_name
                })
                
        return models
        
    def get_languages(self):
        """Retourne la liste des langues disponibles avec leurs noms en français."""
        lang_names = {
            'fr': 'Français',
            'en': 'Anglais',
            'es': 'Espagnol',
            'de': 'Allemand',
            'it': 'Italien',
            'multilingual': 'Multilingue'
        }
        languages = []
        for lang in sorted(self.language_models.keys()):
            languages.append(lang_names.get(lang, lang.capitalize()))
        return languages
        
    def get_voices(self, language):
        """Retourne la liste des voix disponibles pour une langue donnée."""
        # Convertir le nom français en code de langue
        lang_codes = {
            'Français': 'fr',
            'Anglais': 'en',
            'Espagnol': 'es',
            'Allemand': 'de',
            'Italien': 'it',
            'Multilingue': 'multilingual'
        }
        lang_code = lang_codes.get(language, language.lower())
        
        if lang_code in self.language_models:
            return [model['display_name'] for model in self.language_models[lang_code]]
        return []
        
    def get_model_name(self, display_name, language):
        """Retourne le nom du modèle à partir du nom d'affichage et de la langue."""
        lang_codes = {
            'Français': 'fr',
            'Anglais': 'en',
            'Espagnol': 'es',
            'Allemand': 'de',
            'Italien': 'it',
            'Multilingue': 'multilingual'
        }
        lang_code = lang_codes.get(language, language.lower())
        
        if lang_code in self.language_models:
            for model in self.language_models[lang_code]:
                if model['display_name'] == display_name:
                    return model['name']
        return None
        
    def get_voice_display_name(self, model_name):
        """Retourne le nom d'affichage pour un modèle donné."""
        for models in self.language_models.values():
            for model in models:
                if model['name'] == model_name:
                    return model['display_name']
        return model_name
        
    def get_model_info(self, model_name):
        """Retourne les informations sur un modèle spécifique."""
        try:
            model = self.tts.list_models().get_model(model_name)
            return {
                'name': model_name,
                'language': model_name.split('/')[1],
                'dataset': model_name.split('/')[2] if len(model_name.split('/')) > 2 else 'unknown',
                'type': model_name.split('/')[0]
            }
        except:
            return None
            
    def is_multilingual(self, model_name):
        """Vérifie si un modèle est multilingue."""
        return model_name.startswith('tts_models/multilingual/')
        
    def get_model_type(self, model_name):
        """Retourne le type de modèle (TTS, vocoder, etc.)."""
        return model_name.split('/')[0] 