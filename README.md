# VocalClone

Application de synthèse vocale avancée avec interface graphique et contrôle MIDI.

## Fonctionnalités

- 🎤 **Clonage Vocal** : Créez un clone numérique de n'importe quelle voix
- 🗣️ **Synthèse Vocale Multilingue** : Support de multiples langues
- 🎹 **Support MIDI** : Contrôle en temps réel via périphériques MIDI
- 📊 **Monitoring en Temps Réel** : Visualisation de l'audio pendant la synthèse
- 📝 **Gestion des Modèles** : Interface pour installer et gérer les modèles vocaux
- 🎨 **Interface Moderne** : Design intuitif avec onglets et contrôles avancés

## Installation

1. Cloner le repository :
```bash
git clone https://github.com/Oinjenieur/VocalClone.git
cd VocalClone
```

2. Créer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Configuration initiale :
```bash
python setup_models.py
```

## Utilisation

1. Lancer l'application :
```bash
python src/main.py
```

2. Pour enregistrer et cloner une voix :
   - Aller dans l'onglet "Enregistrement"
   - Enregistrer un échantillon de voix
   - Cliquer sur "Cloner la voix"

3. Pour synthétiser du texte :
   - Aller dans l'onglet "Synthèse"
   - Sélectionner un modèle vocal
   - Entrer le texte à synthétiser
   - Cliquer sur "Synthétiser"

4. Pour utiliser le contrôle MIDI :
   - Aller dans l'onglet "MIDI"
   - Sélectionner un périphérique MIDI
   - Configurer les associations de contrôleurs

## Configuration Requise

- Python 3.8 ou supérieur
- GPU CUDA (recommandé) pour les performances optimales
- Au moins 8GB de RAM (16GB recommandés)
- Périphériques audio (microphone et haut-parleurs)
- Périphérique MIDI (optionnel)

## Structure du Projet

```
VocalClone/
├── src/                # Code source principal
│   ├── core/           # Moteur de synthèse vocal
│   ├── gui/            # Interface graphique
│   └── utils/          # Utilitaires
├── models/             # Modèles pré-entraînés
├── recordings/         # Enregistrements audio
├── voices/             # Voix clonées
└── resources/          # Ressources (icônes, etc.)
```

## Développement

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les instructions sur la contribution au projet.

## Licence

[MIT License](LICENSE)

## Remerciements

Ce projet utilise plusieurs bibliothèques et technologies open source :
- [Torch](https://pytorch.org/) - Pour les modèles d'apprentissage profond
- [PySide6](https://www.qt.io/qt-for-python) - Pour l'interface graphique
- [TTS](https://github.com/coqui-ai/TTS) - Pour certains modèles de synthèse vocale
