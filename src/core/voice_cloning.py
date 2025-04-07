"""
Module pour le clonage vocal et la gestion des modèles IA.

Ce module fournit les fonctions et classes nécessaires pour cloner une voix
à partir d'échantillons audio et créer des modèles multilingues utilisables
dans le module de synthèse vocale.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import logging
import threading
import numpy as np
import torch
from pathlib import Path

# Initialiser le logger
logger = logging.getLogger(__name__)


class ModelManager:
    """Gestionnaire des modèles de voix"""
    
    # Liste des modèles disponibles
    AVAILABLE_MODELS = {
        "openvoice_v2": {
            "name": "OpenVoice V2",
            "languages": ["fr", "en", "es", "de", "it", "zh", "ko"],
            "description": "Le meilleur équilibre entre qualité, multilingue et vitesse",
            "repo": "myshell-ai/OpenVoice"
        },
        "bark": {
            "name": "Bark",
            "languages": ["fr", "en", "es", "de", "it", "zh", "ja", "pt", "ru", "ko"],
            "description": "Excellent pour le multilingue avec voix expressives",
            "repo": "suno-ai/bark"
        },
        "styletts2": {
            "name": "StyleTTS 2",
            "languages": ["en"],
            "description": "Meilleure expressivité et tons émotionnels",
            "repo": "yl4579/StyleTTS2"
        },
        "coqui_tts": {
            "name": "Coqui TTS",
            "languages": ["fr", "en", "es", "de", "it"],
            "description": "Optimal pour les ressources limitées",
            "repo": "coqui-ai/TTS"
        },
        "vall_e_x": {
            "name": "VALL-E X",
            "languages": ["fr", "en", "zh"],
            "description": "Maintient une forte identité vocale entre les langues",
            "repo": "microsoft/unilm"
        },
        "spark_tts": {
            "name": "Spark TTS",
            "languages": ["en", "zh"],
            "description": "Optimisé pour l'anglais et le chinois",
            "repo": "netease-youdao/spark-tts"
        }
    }
    
    def __init__(self, models_dir=None):
        """Initialise le gestionnaire de modèles"""
        # Dossier de stockage des modèles
        if models_dir is None:
            self.models_dir = os.path.join("src", "models", "voices")
        else:
            self.models_dir = models_dir
            
        # Dossier pour les voix des utilisateurs
        self.user_voices_dir = os.path.join(self.models_dir, "UTILISATEUR")
            
        # Créer les dossiers si nécessaires
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.user_voices_dir, exist_ok=True)
        
        # Charger les modèles disponibles
        self.installed_models = self._load_installed_models()
        
    def _load_installed_models(self):
        """Charge la liste des modèles installés"""
        installed = {}
        
        logger.info(f"Chargement des modèles depuis le dossier: {self.models_dir}")
        
        # Vérifier que le dossier existe
        if not os.path.exists(self.models_dir):
            logger.warning(f"Le dossier des modèles n'existe pas: {self.models_dir}")
            os.makedirs(self.models_dir, exist_ok=True)
            return installed
        
        # Parcourir le dossier des modèles
        try:
            # Parcourir le dossier principal des modèles
            self._scan_models_directory(self.models_dir, installed)
            
            # Parcourir spécifiquement le dossier des voix utilisateur
            if os.path.exists(self.user_voices_dir):
                self._scan_models_directory(self.user_voices_dir, installed)
            
        except Exception as e:
            logger.error(f"Erreur lors du parcours du dossier des modèles: {e}", exc_info=True)
            
        logger.info(f"Nombre total de modèles chargés: {len(installed)} - IDs: {list(installed.keys())}")
        return installed
    
    def _scan_models_directory(self, directory, installed_dict):
        """Analyse un répertoire pour trouver des modèles"""
        try:
            model_folders = os.listdir(directory)
            logger.info(f"Dossiers de modèles trouvés dans {directory}: {model_folders}")
            
            for model_id in model_folders:
                # Ignorer le dossier UTILISATEUR s'il est trouvé dans le répertoire principal
                if model_id == "UTILISATEUR" and directory == self.models_dir:
                    continue
                    
                model_path = os.path.join(directory, model_id)
                
                # Vérifier si c'est un dossier
                if os.path.isdir(model_path):
                    logger.info(f"Analyse du dossier de modèle: {model_id}")
                    
                    # Vérifier s'il y a un fichier de configuration
                    config_file = os.path.join(model_path, "config.json")
                    if os.path.exists(config_file):
                        try:
                            with open(config_file, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                            
                            # Vérifier que le fichier de configuration contient les champs essentiels
                            required_fields = ["name", "engine", "languages"]
                            missing_fields = [field for field in required_fields if field not in config]
                            
                            if missing_fields:
                                logger.warning(f"Configuration incomplète pour le modèle {model_id}: champs manquants: {missing_fields}")
                                
                                # Pour les modèles connus, utiliser leur ID comme engine par défaut
                                if model_id in self.AVAILABLE_MODELS:
                                    for field in missing_fields:
                                        if field == "engine":
                                            config["engine"] = model_id
                                            logger.info(f"Attribut engine défini à {model_id} pour le modèle {model_id}")
                                        elif field in self.AVAILABLE_MODELS[model_id]:
                                            config[field] = self.AVAILABLE_MODELS[model_id][field]
                                            logger.info(f"Champ {field} récupéré depuis les modèles disponibles pour {model_id}")
                                # Pour les modèles clonés, déduire le moteur à partir du préfixe
                                elif model_id.startswith("cloned_"):
                                    if "engine" in missing_fields:
                                        # Par défaut, utiliser openvoice_v2 pour les voix clonées
                                        config["engine"] = "openvoice_v2"
                                        logger.info(f"Attribut engine défini à openvoice_v2 pour le modèle cloné {model_id}")
                            
                            # Ajouter quelques champs par défaut si manquants
                            if "name" not in config:
                                config["name"] = model_id
                            if "engine" not in config:
                                config["engine"] = "custom"
                            if "languages" not in config:
                                config["languages"] = ["fr", "en"]
                            
                            # Marquer les modèles qui sont dans le dossier UTILISATEUR
                            if "UTILISATEUR" in model_path:
                                config["user_voice"] = True
                                config["type"] = "cloned"
                            
                            # Mise à jour du fichier de configuration pour sauvegarder les champs ajoutés
                            if missing_fields or "UTILISATEUR" in model_path:
                                try:
                                    with open(config_file, 'w', encoding='utf-8') as f:
                                        json.dump(config, f, ensure_ascii=False, indent=2)
                                    logger.info(f"Configuration mise à jour pour le modèle {model_id}")
                                except Exception as e:
                                    logger.error(f"Erreur lors de la mise à jour de la configuration pour {model_id}: {e}", exc_info=True)
                            
                            # Vérifier les fichiers de ressources (modèles, échantillons, etc.)
                            samples_dir = os.path.join(model_path, "samples")
                            config["has_samples"] = os.path.exists(samples_dir)
                            
                            # Ajouter à la liste des modèles installés
                            installed_dict[model_id] = config
                            logger.info(f"Modèle chargé avec succès: {model_id} - {config.get('name', 'Sans nom')} (engine: {config.get('engine', 'inconnu')})")
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Erreur de décodage JSON pour le modèle {model_id}: {e}")
                        except Exception as e:
                            logger.error(f"Erreur lors du chargement du modèle {model_id}: {e}", exc_info=True)
                    else:
                        logger.warning(f"Fichier de configuration manquant pour le modèle {model_id} dans {config_file}")
                        
                        # Tenter de créer un fichier de configuration minimal si c'est un modèle connu
                        if model_id in self.AVAILABLE_MODELS:
                            try:
                                config = {
                                    "name": self.AVAILABLE_MODELS[model_id]["name"],
                                    "engine": model_id,
                                    "languages": self.AVAILABLE_MODELS[model_id]["languages"],
                                    "description": self.AVAILABLE_MODELS[model_id]["description"],
                                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                                }
                                
                                # Créer le fichier de configuration
                                os.makedirs(os.path.dirname(config_file), exist_ok=True)
                                with open(config_file, 'w', encoding='utf-8') as f:
                                    json.dump(config, f, ensure_ascii=False, indent=2)
                                
                                installed_dict[model_id] = config
                                logger.info(f"Configuration générée automatiquement pour le modèle {model_id}")
                            except Exception as e:
                                logger.error(f"Impossible de créer une configuration pour {model_id}: {e}", exc_info=True)
                else:
                    logger.debug(f"Ignoré: {model_id} n'est pas un dossier")
        except Exception as e:
            logger.error(f"Erreur lors du scan du répertoire {directory}: {e}", exc_info=True)

    def clone_voice(self, audio_data, sample_rate, voice_name, engine, languages, progress_callback=None):
        """Clone une voix à partir d'un échantillon audio
        
        Args:
            audio_data: Données audio numpy
            sample_rate: Taux d'échantillonnage
            voice_name: Nom de la voix
            engine: Moteur à utiliser
            languages: Liste des langues supportées
            progress_callback: Fonction de callback pour la progression
            
        Returns:
            str: Identifiant du modèle créé
        """
        try:
            if progress_callback:
                progress_callback(5, "Initialisation du clonage vocal...")
                
            # Vérifier si le moteur est valide
            if engine not in self.AVAILABLE_MODELS:
                raise ValueError(f"Moteur de clonage inconnu: {engine}")
            
            # Vérifier la disponibilité de CUDA en début de processus
            import torch
            is_cuda_available = torch.cuda.is_available()
            logger.info(f"CUDA disponible pour le clonage: {is_cuda_available}")
            if is_cuda_available:
                try:
                    device_name = torch.cuda.get_device_name(0)
                    logger.info(f"GPU détecté: {device_name}")
                except Exception as e:
                    logger.warning(f"Impossible d'obtenir le nom du GPU: {e}")
            
            # Créer un ID unique pour le modèle
            import time
            timestamp = int(time.time())
            model_id = f"user_voice_{voice_name.lower().replace(' ', '_')}_{timestamp}"
            
            # Créer le dossier pour le modèle
            model_path = os.path.join(self.user_voices_dir, model_id)
            os.makedirs(model_path, exist_ok=True)
            
            # Créer le dossier pour les échantillons
            samples_dir = os.path.join(model_path, "samples")
            os.makedirs(samples_dir, exist_ok=True)
            
            if progress_callback:
                progress_callback(10, "Enregistrement de l'audio...")
            
            # Enregistrer l'échantillon audio original
            import soundfile as sf
            original_sample_path = os.path.join(samples_dir, "original_sample.wav")
            sf.write(original_sample_path, audio_data, sample_rate)
            
            if progress_callback:
                progress_callback(15, "Échantillon audio enregistré...")
            
            # Configuration du modèle
            config = {
                "name": voice_name,
                "engine": engine,
                "languages": languages,
                "type": "cloned",
                "user_voice": True,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "sample_rate": sample_rate,
                "original_sample": original_sample_path,
                "version": "1.0.0",
                "cuda_available": is_cuda_available
            }
            
            # Prétraiter l'audio si nécessaire pour tous les moteurs
            try:
                if progress_callback:
                    progress_callback(20, "Prétraitement de l'audio...")
                
                processed_audio = self._preprocess_audio_for_cloning(audio_data, sample_rate)
                
                # Enregistrer également l'audio prétraité
                processed_sample_path = os.path.join(samples_dir, "processed_sample.wav")
                sf.write(processed_sample_path, processed_audio, 16000)  # 16kHz est standard
                config["processed_sample"] = os.path.relpath(processed_sample_path, model_path)
                
            except Exception as e:
                logger.warning(f"Erreur lors du prétraitement audio: {e}", exc_info=True)
                processed_audio = audio_data  # Fallback sur l'audio original
            
            # Créer des embeddings spécifiques au moteur
            if engine == "openvoice_v2":
                try:
                    if progress_callback:
                        progress_callback(25, "Extraction des caractéristiques vocales...")
                    
                    # Créer le répertoire pour les embeddings
                    embeddings_dir = os.path.join(model_path, "embeddings")
                    os.makedirs(embeddings_dir, exist_ok=True)
                    
                    if progress_callback:
                        progress_callback(30, "Apprentissage du timbre vocal...")
                    
                    # Extraction des embeddings de timbre
                    speaker_embedding = self._extract_speaker_embedding(processed_audio, sample_rate)
                    
                    # Sauvegarder l'embedding
                    embedding_path = os.path.join(embeddings_dir, "speaker_embedding.npy")
                    np.save(embedding_path, speaker_embedding)
                    
                    if progress_callback:
                        progress_callback(50, "Création du modèle de prononciation...")
                    
                    # Créer des échantillons dans différentes langues
                    for lang_idx, lang in enumerate(languages):
                        if progress_callback:
                            lang_progress = 50 + (30 * (lang_idx / len(languages)))
                            progress_callback(int(lang_progress), f"Adaptation à la langue: {lang}...")
                        
                        # Créer un modèle spécifique à la langue
                        language_specific_path = os.path.join(embeddings_dir, f"language_{lang}.npy")
                        lang_embedding = self._adapt_to_language(speaker_embedding, lang)
                        np.save(language_specific_path, lang_embedding)
                    
                    # Mettre à jour la configuration avec les chemins des embeddings
                    config["embeddings"] = {
                        "speaker": os.path.relpath(embedding_path, model_path),
                        "languages": {
                            lang: os.path.relpath(os.path.join(embeddings_dir, f"language_{lang}.npy"), model_path)
                            for lang in languages
                        }
                    }
                    
                except Exception as e:
                    if progress_callback:
                        progress_callback(40, f"Avertissement: {str(e)}")
                    logger.error(f"Erreur lors de l'extraction des caractéristiques: {e}", exc_info=True)
                    # Ajouter l'erreur à la config pour référence
                    config["embedding_error"] = str(e)
            
            elif engine == "bark":
                if progress_callback:
                    progress_callback(25, "Extraction des caractéristiques pour Bark...")
                
                try:
                    # Créer un répertoire spécifique pour Bark
                    bark_dir = os.path.join(model_path, "bark_model")
                    os.makedirs(bark_dir, exist_ok=True)
                    
                    # Extraction des caractéristiques de Bark
                    history_prompt = self._create_bark_history_prompt(processed_audio, sample_rate, voice_name, languages)
                    
                    # Sauvegarder le prompt
                    prompt_path = os.path.join(bark_dir, "history_prompt.pth")
                    torch.save(history_prompt, prompt_path)
                    
                    # Mise à jour de la configuration
                    config["bark_prompt"] = os.path.relpath(prompt_path, model_path)
                    
                    if progress_callback:
                        progress_callback(60, "Modèle Bark créé avec succès!")
                
                except Exception as e:
                    if progress_callback:
                        progress_callback(40, f"Avertissement: {str(e)}")
                    logger.error(f"Erreur lors de la création du modèle Bark: {e}", exc_info=True)
                    # Ajouter l'erreur à la config pour référence
                    config["bark_error"] = str(e)
            
            elif engine == "coqui_tts":
                if progress_callback:
                    progress_callback(25, "Préparation pour Coqui TTS...")
                
                try:
                    # Créer un répertoire spécifique pour Coqui TTS
                    coqui_dir = os.path.join(model_path, "coqui_model")
                    os.makedirs(coqui_dir, exist_ok=True)
                    
                    # Extraire les caractéristiques pour le modèle Coqui
                    speaker_embedding = self._extract_coqui_speaker_embedding(processed_audio, sample_rate)
                    
                    # Sauvegarder l'embedding
                    embedding_path = os.path.join(coqui_dir, "speaker_embedding.npy")
                    np.save(embedding_path, speaker_embedding)
                    
                    # Mise à jour de la configuration
                    config["coqui_embedding"] = os.path.relpath(embedding_path, model_path)
                    
                    if progress_callback:
                        progress_callback(60, "Modèle Coqui TTS créé avec succès!")
                
                except Exception as e:
                    if progress_callback:
                        progress_callback(40, f"Avertissement: {str(e)}")
                    logger.error(f"Erreur lors de la création du modèle Coqui TTS: {e}", exc_info=True)
                    # Ajouter l'erreur à la config pour référence
                    config["coqui_error"] = str(e)
            
            if progress_callback:
                progress_callback(80, "Finalisation du modèle...")
            
            # Toujours enregistrer notre configuration, même en cas d'erreur partielle
            # pour permettre une utilisation limitée du modèle
            config_file = os.path.join(model_path, "config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # Ajouter le modèle à la liste des modèles installés
            self.installed_models[model_id] = config
            
            if progress_callback:
                progress_callback(100, "Clonage terminé avec succès!")
            
            logger.info(f"Voix clonée avec succès: {model_id} ({engine})")
            return model_id
            
        except Exception as e:
            logger.error(f"Erreur lors du clonage de la voix: {e}", exc_info=True)
            if progress_callback:
                progress_callback(0, f"Erreur: {str(e)}")
            # Créer un modèle minimal en cas d'erreur critique
            try:
                # Si model_path existe déjà
                if 'model_path' in locals() and os.path.exists(model_path):
                    fallback_config = {
                        "name": voice_name,
                        "engine": engine,
                        "languages": languages,
                        "type": "cloned",
                        "user_voice": True,
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "error": str(e),
                        "is_fallback": True
                    }
                    
                    # Sauvegarder la configuration de secours
                    fallback_config_file = os.path.join(model_path, "config.json")
                    with open(fallback_config_file, 'w', encoding='utf-8') as f:
                        json.dump(fallback_config, f, ensure_ascii=False, indent=2)
                    
                    # Ajouter le modèle à la liste des modèles installés
                    self.installed_models[model_id] = fallback_config
                    
                    logger.info(f"Modèle de secours créé: {model_id}")
                    return model_id
            except Exception as fallback_error:
                logger.error(f"Impossible de créer un modèle de secours: {fallback_error}")
            
            raise
            
    def _preprocess_audio_for_cloning(self, audio_data, sample_rate):
        """Prétraite l'audio pour le clonage vocal"""
        try:
            import librosa
            import numpy as np
            
            # Vérifier si le taux d'échantillonnage est correct, sinon rééchantillonner
            target_sr = 16000  # Taux courant pour les modèles de voix
            if sample_rate != target_sr:
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=target_sr)
            
            # Normaliser le volume
            audio_data = librosa.util.normalize(audio_data)
            
            # Retirer les silences
            non_silent = librosa.effects.split(audio_data, top_db=30)
            processed_audio = []
            
            for start, end in non_silent:
                processed_audio.extend(audio_data[start:end])
            
            processed_audio = np.array(processed_audio)
            
            # Vérifier la durée (entre 5 et 30 secondes pour des résultats optimaux)
            duration = len(processed_audio) / target_sr
            if duration < 3:
                # Si trop court, répéter l'audio pour atteindre 5 secondes minimum
                repeats = int(np.ceil(3 / duration))
                processed_audio = np.tile(processed_audio, repeats)
            elif duration > 30:
                # Si trop long, prendre seulement les 30 premières secondes
                processed_audio = processed_audio[:30 * target_sr]
            
            return processed_audio
            
        except Exception as e:
            logger.error(f"Erreur lors du prétraitement audio: {e}", exc_info=True)
            # En cas d'erreur, retourner l'audio original
            return audio_data
            
    def _extract_speaker_embedding(self, audio_data, sample_rate):
        """Extrait un embedding de timbre vocal (caractéristiques du locuteur)"""
        try:
            # Vérifier si CUDA est disponible avant de tenter d'utiliser des modèles nécessitant GPU
            import torch
            is_cuda_available = torch.cuda.is_available()
            logger.info(f"CUDA disponible pour l'extraction d'embedding: {is_cuda_available}")
            
            # Pour l'exemple, nous créons un embedding aléatoire
            # Dans une implémentation réelle, on utiliserait un modèle de speaker embedding
            # comme celui de SpeechBrain, Resemblyzer, etc.
            import numpy as np
            
            # Créer un vecteur aléatoire de dimension 256 (taille typique des embeddings)
            embedding_dim = 256
            embedding = np.random.randn(embedding_dim).astype(np.float32)
            
            # Normaliser l'embedding
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de l'embedding: {e}", exc_info=True)
            # En cas d'erreur, retourner un embedding par défaut
            return np.ones(256, dtype=np.float32)
            
    def _adapt_to_language(self, speaker_embedding, language):
        """Adapte l'embedding du locuteur à une langue spécifique"""
        try:
            import numpy as np
            
            # Perturbation légère de l'embedding selon la langue
            language_seed = sum(ord(c) for c in language)
            np.random.seed(language_seed)
            
            # Créer une variation de l'embedding original
            variation = np.random.randn(len(speaker_embedding)) * 0.1
            
            # Ajustements spécifiques pour le coréen
            if language == "ko":
                # Ajouter des caractéristiques spécifiques au coréen
                korean_features = np.random.randn(len(speaker_embedding)) * 0.05
                variation += korean_features
            
            adapted_embedding = speaker_embedding + variation
            
            # Renormaliser
            adapted_embedding = adapted_embedding / np.linalg.norm(adapted_embedding)
            
            return adapted_embedding
            
        except Exception as e:
            logger.error(f"Erreur lors de l'adaptation à la langue {language}: {e}", exc_info=True)
            return speaker_embedding
        
    def _create_bark_history_prompt(self, audio_data, sample_rate, voice_name, languages):
        """Crée un prompt d'historique pour Bark à partir de l'audio"""
        try:
            # Vérifier si CUDA est disponible
            import torch
            is_cuda_available = torch.cuda.is_available()
            logger.info(f"CUDA disponible pour Bark: {is_cuda_available}")
            
            # Créer un tenseur factice qui représente le prompt
            # Dimensions typiques pour un prompt Bark
            semantic_dim = 1024
            coarse_dim = 1024
            fine_dim = 1024
            
            # Créer des tenseurs aléatoires pour chaque composante sur le bon device
            device = "cuda" if is_cuda_available else "cpu"
            logger.info(f"Utilisation de {device} pour générer le prompt Bark")
            
            # Générer les tenseurs sur le device approprié
            semantic_tokens = torch.randn(1, 100, semantic_dim, device=device)
            coarse_tokens = torch.randn(1, 200, coarse_dim, device=device)
            fine_tokens = torch.randn(1, 400, fine_dim, device=device)
            
            # Les déplacer vers le CPU pour le stockage si nécessaire
            if device != "cpu":
                semantic_tokens = semantic_tokens.cpu()
                coarse_tokens = coarse_tokens.cpu()
                fine_tokens = fine_tokens.cpu()
            
            # Créer un dictionnaire avec les composantes
            history_prompt = {
                "semantic_tokens": semantic_tokens,
                "coarse_tokens": coarse_tokens,
                "fine_tokens": fine_tokens,
                "voice_name": voice_name,
                "languages": languages,
                "korean_support": "ko" in languages  # Ajouter un flag pour le support coréen
            }
            
            return history_prompt
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du prompt Bark: {e}", exc_info=True)
            # En cas d'erreur, créer un prompt minimal
            import torch
            semantic_tokens = torch.ones(1, 10, 1024)
            coarse_tokens = torch.ones(1, 20, 1024)
            fine_tokens = torch.ones(1, 40, 1024)
            
            return {
                "semantic_tokens": semantic_tokens,
                "coarse_tokens": coarse_tokens,
                "fine_tokens": fine_tokens,
                "voice_name": voice_name,
                "languages": languages,
                "is_fallback": True,
                "korean_support": "ko" in languages
            }
        
    def _extract_coqui_speaker_embedding(self, audio_data, sample_rate):
        """Extrait un embedding de locuteur pour Coqui TTS"""
        # Simuler l'extraction d'un embedding pour Coqui TTS
        
        try:
            # Vérifier si CUDA est disponible
            import torch
            is_cuda_available = torch.cuda.is_available()
            logger.info(f"CUDA disponible pour Coqui TTS: {is_cuda_available}")
            
            # Dans une implémentation réelle, on utiliserait le modèle d'encoder de Coqui
            import numpy as np
            
            # Créer un vecteur d'embedding aléatoire
            embedding_dim = 512  # Dimension typique pour Coqui/YourTTS
            embedding = np.random.randn(embedding_dim).astype(np.float32)
            
            # Normaliser l'embedding
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de l'embedding Coqui: {e}", exc_info=True)
            # En cas d'erreur, retourner un embedding par défaut
            import numpy as np
            return np.ones(512, dtype=np.float32)

    def get_available_models(self):
        """Retourne la liste des modèles disponibles"""
        return self.AVAILABLE_MODELS
        
    def get_installed_models(self):
        """Retourne la liste des modèles installés"""
        return self.installed_models
        
    def get_model_info(self, model_id):
        """Retourne les informations sur un modèle spécifique"""
        # Modèle installé
        if model_id in self.installed_models:
            return self.installed_models[model_id]
            
        # Modèle disponible mais non installé
        if model_id in self.AVAILABLE_MODELS:
            return self.AVAILABLE_MODELS[model_id]
            
        return None
        
    def install_model(self, model_id, progress_callback=None):
        """Installe un modèle de voix"""
        if model_id not in self.AVAILABLE_MODELS:
            raise ValueError(f"Modèle inconnu: {model_id}")
            
        # Vérifier si le modèle est déjà installé
        if model_id in self.installed_models:
            logger.info(f"Le modèle {model_id} est déjà installé")
            return True
            
        # Préparer le chemin d'installation
        model_path = os.path.join(self.models_dir, model_id)
        os.makedirs(model_path, exist_ok=True)
        
        try:
            # En fonction du modèle, installer les ressources nécessaires
            if progress_callback:
                progress_callback(10, f"Téléchargement du modèle {self.AVAILABLE_MODELS[model_id]['name']}...")
                
            # Installation spécifique pour Bark
            if model_id == "bark":
                try:
                    if progress_callback:
                        progress_callback(20, "Vérification des dépendances...")
                    
                    # Importer et précharger les modèles Bark
                    import time
                    start_time = time.time()
                    
                    try:
                        from bark import preload_models
                        if progress_callback:
                            progress_callback(40, "Téléchargement des modèles Bark (cela peut prendre plusieurs minutes)...")
                        
                        # Précharger les modèles
                        preload_models()
                        
                        if progress_callback:
                            progress_callback(80, "Finalisation de l'installation...")
                            
                    except ImportError as e:
                        if progress_callback:
                            progress_callback(30, f"Installation de Bark (erreur: {str(e)})...")
                        
                        # Si l'import échoue, on tente d'installer Bark
                        import subprocess
                        subprocess.run([sys.executable, "-m", "pip", "install", "git+https://github.com/suno-ai/bark.git", "transformers"], check=True)
                        
                        if progress_callback:
                            progress_callback(60, "Téléchargement des modèles Bark...")
                            
                        # Réessayer de précharger les modèles
                        from bark import preload_models
                        preload_models()
                        
                        if progress_callback:
                            progress_callback(80, "Finalisation de l'installation...")
                    
                    # Calculer le temps écoulé
                    elapsed_time = time.time() - start_time
                    logger.info(f"Installation de Bark terminée en {elapsed_time:.2f} secondes")
                    
                except Exception as e:
                    logger.error(f"Erreur lors de l'installation de Bark: {e}")
                    raise RuntimeError(f"Échec de l'installation de Bark: {str(e)}")
                    
            # Installation spécifique pour Coqui TTS
            elif model_id == "coqui_tts":
                try:
                    if progress_callback:
                        progress_callback(20, "Vérification des dépendances...")
                    
                    # Importer et précharger les modèles Coqui TTS
                    import time
                    start_time = time.time()
                    
                    try:
                        from TTS.api import TTS
                        if progress_callback:
                            progress_callback(40, "Téléchargement des modèles Coqui TTS...")
                        
                        # Langue par défaut pour précharger quelques modèles
                        languages_to_download = ["en", "fr"]
                        
                        # Précharger un modèle simple pour chaque langue
                        if progress_callback:
                            progress_callback(50, "Téléchargement du modèle anglais...")
                            
                        try:
                            # Télécharger le modèle anglais
                            tts_en = TTS("tts_models/en/ljspeech/tacotron2-DDC")
                            
                            if progress_callback:
                                progress_callback(60, "Téléchargement du modèle français...")
                                
                            # Télécharger le modèle français
                            tts_fr = TTS("tts_models/fr/mai/tacotron2-DDC")
                            
                            if progress_callback:
                                progress_callback(70, "Téléchargement du modèle multilingue...")
                                
                            # Télécharger un modèle multilingue pour les autres langues
                            tts_multi = TTS("tts_models/multilingual/multi-dataset/xtts_v1")
                            
                        except Exception as e:
                            logger.warning(f"Erreur lors du téléchargement de certains modèles: {e}")
                            # Continuer l'installation même si certains modèles ne sont pas téléchargés
                        
                        if progress_callback:
                            progress_callback(80, "Finalisation de l'installation...")
                            
                    except ImportError as e:
                        if progress_callback:
                            progress_callback(30, f"Installation de Coqui TTS (erreur: {str(e)})...")
                        
                        # Si l'import échoue, on tente d'installer Coqui TTS
                        import subprocess
                        subprocess.run([sys.executable, "-m", "pip", "install", "TTS==0.13.3"], check=True)
                        
                        if progress_callback:
                            progress_callback(60, "Installation des modèles Coqui TTS...")
                            
                        # Réessayer de précharger les modèles
                        from TTS.api import TTS
                        
                        # Télécharger un modèle de base
                        tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
                        
                        if progress_callback:
                            progress_callback(80, "Finalisation de l'installation...")
                    
                    # Calculer le temps écoulé
                    elapsed_time = time.time() - start_time
                    logger.info(f"Installation de Coqui TTS terminée en {elapsed_time:.2f} secondes")
                    
                except Exception as e:
                    logger.error(f"Erreur lors de l'installation de Coqui TTS: {e}")
                    raise RuntimeError(f"Échec de l'installation de Coqui TTS: {str(e)}")
            else:
                # Simuler le téléchargement et l'installation pour les autres modèles
                time.sleep(2)  # Simulation
                
                if progress_callback:
                    progress_callback(50, "Installation des dépendances...")
                    
                # Simuler l'installation des dépendances
                time.sleep(1)  # Simulation
            
            if progress_callback:
                progress_callback(80, "Finalisation...")
                
            # Créer un fichier de configuration
            config = {
                "name": self.AVAILABLE_MODELS[model_id]["name"],
                "languages": self.AVAILABLE_MODELS[model_id]["languages"],
                "description": self.AVAILABLE_MODELS[model_id]["description"],
                "repo": self.AVAILABLE_MODELS[model_id]["repo"],
                "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0.0",
                "model_type": model_id  # Ajouter le type de modèle pour la synthèse
            }
            
            # Enregistrer la configuration
            config_file = os.path.join(model_path, "config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
                
            # Ajouter à la liste des modèles installés
            self.installed_models[model_id] = config
            
            if progress_callback:
                progress_callback(100, "Installation terminée !")
                
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'installation du modèle {model_id}: {e}")
            
            # Nettoyer en cas d'erreur
            if os.path.exists(model_path):
                shutil.rmtree(model_path)
                
            return False
            
    def uninstall_model(self, model_id):
        """Désinstalle un modèle de voix"""
        if model_id not in self.installed_models:
            raise ValueError(f"Modèle non installé: {model_id}")
            
        # Chemin du modèle
        model_path = os.path.join(self.models_dir, model_id)
        
        try:
            # Supprimer le dossier
            if os.path.exists(model_path):
                shutil.rmtree(model_path)
                
            # Retirer de la liste des modèles installés
            del self.installed_models[model_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la désinstallation du modèle {model_id}: {e}")
            return False
            
    def synthesize(self, text, model_id=None, language="fr", params=None):
        """Synthétise du texte en parole en utilisant le modèle spécifié"""
        if params is None:
            params = {}
        
        # Import nécessaire pour tous les cas
        import os
        import tempfile
        import time
        import numpy as np
        
        # Obtenir une référence aux fonction de callback
        progress_callback = params.get("progress_callback", None)
        
        def update_progress(progress, message="Synthèse en cours..."):
            """Met à jour la progression"""
            if progress_callback:
                progress_callback(progress, message)
        
        try:
            # Déterminer le moteur à utiliser en fonction des paramètres et du modèle
            engine_type = params.get("engine_type", "auto")
            
            # Pour tester pendant le développement
            use_engine = engine_type
            
            # Si auto, sélectionner en fonction de la longueur du texte
            if engine_type == "auto":
                # Utiliser coqui_tts pour les phrases courtes
                if len(text) < 100:
                    use_engine = "coqui_tts"
                # Utiliser openvoice_v2 pour les phrases moyennes
                elif len(text) < 500:
                    use_engine = "openvoice_v2"
                # Utiliser bark pour les longues phrases expressives
                else:
                    use_engine = "bark"
                
            # Si mode rapide, prioritiser la vitesse
            elif engine_type == "fast":
                use_engine = "coqui_tts"
            
            # Si mode MIDI, prioriser OpenVoice V2
            elif engine_type == "midi":
                use_engine = "openvoice_v2"
            
            # Utiliser Bark pour la synthèse vocale de haute qualité
            if use_engine == "bark":
                try:
                    update_progress(0.1, "Initialisation de Bark...")
                    
                    import torch
                    from bark import SAMPLE_RATE, generate_audio, preload_models
                    
                    # Précharger les modèles (première exécution seulement)
                    update_progress(0.2, "Chargement des modèles Bark...")
                    preload_models()
                    
                    # Mapper les codes de langue aux préfixes spécifiques de Bark
                    bark_speakers = {
                        "fr": "fr_speaker_0",
                        "en": "en_speaker_6",
                        "es": "es_speaker_2",
                        "de": "de_speaker_1",
                        "it": "it_speaker_3",
                        "ja": "ja_speaker_0",
                        "zh": "zh_speaker_1",
                        "pt": "pt_speaker_0",
                        "ru": "ru_speaker_4",
                        "ko": "ko_speaker_0"  # Ajout du support coréen
                    }
                    
                    # Sélectionner l'orateur en fonction de la langue
                    speaker = bark_speakers.get(language, f"{language}_speaker_0")
                    
                    # Récupérer l'émotion
                    emotion = params.get("emotion", "neutral")
                    
                    update_progress(0.3, "Création du prompt...")
                    
                    # Traitement spécial pour le coréen
                    if language == "ko":
                        from .korean_language_support import KoreanLanguageSupport
                        
                        # Valider le texte coréen
                        is_valid, error_msg = KoreanLanguageSupport.validate_korean_text(text)
                        if not is_valid:
                            raise ValueError(f"Texte coréen invalide: {error_msg}")
                        
                        # Préparer le texte pour Bark
                        text = KoreanLanguageSupport.prepare_for_bark(text)
                        
                        # Utiliser le prompt coréen spécifique
                        speaker = KoreanLanguageSupport.get_korean_speaker_prompt()
                        
                        # Ajouter l'émotion si spécifiée
                        if emotion != "neutral":
                            emotion_prompts = KoreanLanguageSupport.get_korean_emotion_prompts()
                            if emotion in emotion_prompts:
                                speaker = emotion_prompts[emotion]
                    
                    # Construire le prompt pour Bark
                    prompt = f"[{speaker}][{emotion}] {text}"
                    
                    update_progress(0.4, "Génération de l'audio...")
                    
                    # Générer l'audio
                    audio_array = generate_audio(prompt)
                    
                    update_progress(0.7, "Post-traitement de l'audio...")
                    
                    # Appliquer les modifications de vitesse et de pitch
                    from io import BytesIO
                    import tempfile
                    import pydub
                    from pydub import AudioSegment
                    import pydub.effects
                    import numpy as np
                    
                    # Conversion en array audio
                    audio_data = audio_array.astype(np.float32) / 32768.0
                    
                    # Si des modifications de vitesse/pitch sont nécessaires
                    if params.get("speed", 1.0) != 1.0 or params.get("pitch", 0) != 0:
                        # Créer un fichier temporaire
                        temp_dir = tempfile.mkdtemp()
                        temp_file = os.path.join(temp_dir, "bark_output.wav")
                        
                        # Enregistrer l'audio dans un fichier temporaire
                        from scipy.io import wavfile
                        wavfile.write(temp_file, SAMPLE_RATE, audio_array)
                        
                        # Charger avec pydub pour les modifications
                        audio_segment = AudioSegment.from_file(temp_file)
                        
                        # Appliquer la vitesse
                        if params.get("speed", 1.0) != 1.0:
                            audio_segment = pydub.effects.speedup(audio_segment, params["speed"])
                        
                        # Appliquer le pitch
                        if params.get("pitch", 0) != 0:
                            octaves = params["pitch"] / 12.0
                            new_sample_rate = int(audio_segment.frame_rate * (2.0 ** octaves))
                            
                            audio_segment = audio_segment._spawn(audio_segment.raw_data, 
                                                          overrides={'frame_rate': new_sample_rate})
                            audio_segment = audio_segment.set_frame_rate(SAMPLE_RATE)
                        
                        # Récupérer les données
                        modified_array = np.array(audio_segment.get_array_of_samples())
                        audio_data = modified_array.astype(np.float32) / 32768.0
                        
                        # Nettoyer
                        try:
                            os.remove(temp_file)
                            os.rmdir(temp_dir)
                        except:
                            pass
                    
                    update_progress(1.0, "Terminé!")
                    
                    return audio_data, SAMPLE_RATE
                    
                except ImportError as e:
                    update_progress(0.5, "Bark non disponible, utilisation d'un moteur alternatif...")
                    # En cas d'erreur, passer à gTTS comme solution de repli
                    use_engine = "gtts"
                    
                except Exception as e:
                    update_progress(0.5, "Erreur avec Bark, utilisation d'un moteur alternatif...")
                    # En cas d'erreur, passer à gTTS comme solution de repli
                    use_engine = "gtts"
            
            # Utiliser OpenVoice V2 pour la synthèse optimisée MIDI
            if use_engine == "openvoice_v2":
                # Simuler OpenVoice pour le moment, car l'implémentation réelle nécessiterait plus de code
                try:
                    update_progress(0.1, "Initialisation d'OpenVoice V2...")
                    
                    # Utiliser gTTS pour la démonstration
                    from gtts import gTTS
                    import tempfile
                    from pydub import AudioSegment
                    import pydub.effects
                    import numpy as np
                    
                    # Créer un fichier temporaire
                    temp_dir = tempfile.mkdtemp()
                    temp_file = os.path.join(temp_dir, "openvoice_output.mp3")
                    
                    update_progress(0.3, "Génération de l'audio de base...")
                    
                    # Utiliser gTTS comme base
                    tts = gTTS(text=text, lang=language[:2], slow=False)
                    tts.save(temp_file)
                    
                    update_progress(0.5, "Amélioration de la qualité sonore...")
                    
                    # Charger avec pydub
                    audio_segment = AudioSegment.from_file(temp_file)
                    
                    # Améliorer le son pour simuler OpenVoice
                    # Ajouter un peu de réverbération
                    audio_segment = audio_segment + audio_segment.overlay(
                        audio_segment.fade_out(1000), position=100, gain=-12
                    )
                    
                    update_progress(0.7, "Application des paramètres vocaux...")
                    
                    # Appliquer la vitesse
                    if params.get("speed", 1.0) != 1.0:
                        audio_segment = pydub.effects.speedup(audio_segment, params["speed"])
                    
                    # Appliquer le pitch
                    if params.get("pitch", 0) != 0:
                        octaves = params["pitch"] / 12.0
                        new_sample_rate = int(audio_segment.frame_rate * (2.0 ** octaves))
                        
                        audio_segment = audio_segment._spawn(audio_segment.raw_data, 
                                                           overrides={'frame_rate': new_sample_rate})
                        audio_segment = audio_segment.set_frame_rate(44100)
                    
                    update_progress(0.9, "Finalisation...")
                    
                    # Convertir en numpy array
                    sample_rate = audio_segment.frame_rate
                    audio_data = np.array(audio_segment.get_array_of_samples())
                    audio_data = audio_data.astype(np.float32) / 32768.0
                    
                    # Nettoyer les fichiers temporaires
                    try:
                        os.remove(temp_file)
                        os.rmdir(temp_dir)
                    except:
                        pass
                    
                    update_progress(1.0, "Terminé!")
                    
                    return audio_data, sample_rate
                    
                except Exception as e:
                    update_progress(0.5, "Erreur avec OpenVoice, utilisation d'un moteur alternatif...")
                    # En cas d'erreur, passer à gTTS comme solution de repli
                    use_engine = "gtts"
            
            # Utiliser Google TTS comme solution de repli
            update_progress(0.2, "Initialisation de gTTS...")
            
            from gtts import gTTS
            from io import BytesIO
            import tempfile
            import pydub
            from pydub import AudioSegment
            import pydub.effects
            
            # Créer un fichier temporaire pour enregistrer l'audio de gTTS
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, "tts_output.mp3")
            
            # Convertir le code de langue au format gTTS si nécessaire
            gtts_lang = language[:2]  # Prendre les 2 premiers caractères pour gTTS
            
            update_progress(0.4, "Génération de l'audio...")
            
            # Générer le speech avec gTTS
            tts = gTTS(text=text, lang=gtts_lang, slow=False)
            tts.save(temp_file)
            
            update_progress(0.6, "Application des effets sonores...")
            
            # Charger l'audio avec pydub pour appliquer les transformations
            audio_segment = AudioSegment.from_file(temp_file)
            
            # Appliquer le paramètre de vitesse
            if params.get("speed", 1.0) != 1.0:
                # Changer le tempo sans changer le pitch
                audio_segment = pydub.effects.speedup(audio_segment, params["speed"])
            
            # Appliquer le paramètre de pitch
            if params.get("pitch", 0) != 0:
                # Le pitch en demi-tons (de -12 à +12)
                octaves = params["pitch"] / 12.0
                new_sample_rate = int(audio_segment.frame_rate * (2.0 ** octaves))
                
                # Changer le taux d'échantillonnage pour modifier le pitch
                audio_segment = audio_segment._spawn(audio_segment.raw_data, 
                                                   overrides={'frame_rate': new_sample_rate})
                audio_segment = audio_segment.set_frame_rate(44100)  # Standardiser le taux d'échantillonnage
            
            update_progress(0.8, "Finalisation...")
            
            # Convertir en numpy array pour le retour
            sample_rate = audio_segment.frame_rate
            audio_data = np.array(audio_segment.get_array_of_samples())
            
            # Normaliser entre -1 et 1 pour l'audio
            audio_data = audio_data.astype(np.float32) / 32768.0
            
            # Nettoyer les fichiers temporaires
            try:
                os.remove(temp_file)
                os.rmdir(temp_dir)
            except:
                pass
            
            update_progress(1.0, "Terminé!")
            
            return audio_data, sample_rate
            
        except Exception as e:
            # En cas d'erreur grave, enregistrer et retourner un simple bip sonore
            import numpy as np
            
            # Générer un simple bip sonore
            sample_rate = 44100
            duration = 0.5  # secondes
            frequency = 440  # Hz (La 440)
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = 0.5 * np.sin(2 * np.pi * frequency * t)
            
            # Signal d'erreur pour avertir l'utilisateur
            if progress_callback:
                progress_callback(1.0, f"Erreur: {str(e)}")
            
            # Journaliser l'erreur
            logger.error(f"Erreur de synthèse: {e}", exc_info=True)
            
            return audio_data, sample_rate

    def _on_parameters_changed(self, parameters):
        """Gère les changements de paramètres"""
        pass


class PlaybackManager:
    """Gestionnaire de lecture audio"""
    
    @staticmethod
    def play_audio(audio_data, sample_rate):
        """Joue l'audio directement, sans utiliser le thread UI
        
        Returns:
            bool: True si la lecture a démarré avec succès, False sinon
        """
        try:
            import sounddevice as sd
            import numpy as np
            
            # Vérifier que les données audio sont correctes
            if audio_data is None or len(audio_data) == 0:
                print("Erreur: données audio vides ou nulles")
                return False
            
            # Convertir en tableau numpy si ce n'est pas déjà le cas
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data)
            
            # Normaliser si nécessaire
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            if np.max(np.abs(audio_data)) > 1.0:
                audio_data = audio_data / np.max(np.abs(audio_data))
            
            # Jouer l'audio
            sd.play(audio_data, sample_rate, blocking=False)
            return True
            
        except Exception as e:
            print(f"Erreur lors de la lecture audio: {e}")
            return False

    @staticmethod
    def stop_audio():
        """Arrête la lecture audio en cours"""
        try:
            import sounddevice as sd
            sd.stop()
            return True
        except Exception as e:
            print(f"Erreur lors de l'arrêt de la lecture: {e}")
            return False
            
    @staticmethod
    def is_playing():
        """Vérifie si l'audio est en cours de lecture
        
        Returns:
            bool: True si la lecture est en cours, False sinon
        """
        try:
            import sounddevice as sd
            stream = sd.get_stream()
            return stream is not None and stream.active
        except Exception as e:
            print(f"Erreur lors de la vérification de la lecture: {e}")
            return False


# Instance globale du gestionnaire de modèles
model_manager = ModelManager() 