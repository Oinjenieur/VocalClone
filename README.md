# VocalClone

Application de synthèse vocale et de clonage de voix avec interface graphique.

## Fonctionnalités

- Clonage de voix à partir d'échantillons audio
- Synthèse vocale avec contrôle des paramètres (hauteur, vitesse, etc.)
- Interface graphique conviviale (versions française et anglaise)
- Support MIDI pour contrôle externe
- Plusieurs modèles de synthèse vocale disponibles

## Prérequis

- Python 3.8 ou supérieur
- [ffmpeg](https://ffmpeg.org/download.html) (pour le traitement audio)
- Microphone pour l'enregistrement (optionnel)
- Périphérique MIDI pour le contrôle (optionnel)

## Structure du projet

```
VocalClone/
├── src/              # Code source principal
│   ├── core/         # Moteur de synthèse et clonage
│   ├── gui/          # Interface graphique
│   ├── utils/        # Utilitaires
│   ├── main.py       # Point d'entrée principal
│   ├── main_french.py # Version française
│   └── main_english.py # Version anglaise
├── requirements.txt  # Dépendances Python
└── README.md         # Ce fichier
```

## Installation

### Installation standard

1. Cloner le repository
   ```
   git clone https://github.com/Oinjenieur/VocalClone.git
   cd VocalClone
   ```

2. Créer un environnement virtuel Python (recommandé)
   ```
   python -m venv venv
   ```

3. Activer l'environnement virtuel
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. Installer les dépendances
   ```
   pip install -r requirements.txt
   ```

### Résolution des problèmes d'installation

Si vous rencontrez des problèmes de conflits de dépendances (notamment avec Python 3.8), essayez :

1. **Installer avec les versions compatibles de protobuf**
   ```
   pip install protobuf==3.20.0
   pip install -r requirements.txt
   ```

2. **Installation manuelle des composants principaux**
   ```
   pip install protobuf==3.20.0
   pip install onnx==1.14.0 onnxruntime==1.15.0
   pip install trainer==0.0.20
   pip install torch transformers==4.33.0
   pip install -r requirements.txt
   ```

3. **Si vous utilisez Python 3.8 spécifiquement**, utilisez cette commande :
   ```
   pip install -e .
   ```
   
## Démarrage de l'application

1. Lancer l'application
   ```
   python src/main.py
   ```

2. Options de lancement:
   - Version française: `python src/main.py --language fr`
   - Version anglaise: `python src/main.py --language en`
   - Mode debug: `python src/main.py --debug`

## Utilisation

L'interface se compose de plusieurs onglets:
1. **Recording** - Enregistrement et clonage de voix
2. **Synthesis** - Synthèse vocale avec voix clonées
3. **Models** - Gestion des modèles de voix
4. **MIDI** - Configuration du contrôle MIDI

Consultez la documentation dans le dossier `docs/` pour plus de détails.

## Résolution de problèmes

### Conflits de dépendances

Si vous rencontrez un message d'erreur concernant des conflits entre trainer, onnx et protobuf, suivez les instructions d'installation alternatives ci-dessus.

### Problèmes audio

- Assurez-vous que votre microphone est correctement configuré
- Vérifiez que ffmpeg est installé et accessible dans le PATH

## Contribution

Les contributions sont les bienvenues! Consultez le fichier CONTRIBUTING.md pour plus de détails.

## Licence

Ce projet est sous licence MIT - voir le fichier LICENSE pour plus de détails.
