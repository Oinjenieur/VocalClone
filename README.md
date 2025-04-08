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

### Option 1: Installation simplifiée (recommandée)

Utilisez les scripts d'installation fournis qui gèrent automatiquement les conflits de dépendances :

#### Windows
```
install_py38.bat
```

#### Linux/macOS
```
chmod +x install_py38.sh
./install_py38.sh
```

### Option 2: Installation minimale (en cas de problèmes)

Si vous rencontrez des problèmes avec l'installation standard, essayez l'installation minimale qui n'inclut que les dépendances essentielles :

#### Windows
```
install_minimal.bat
```

#### Linux/macOS
```
chmod +x install_minimal.sh
./install_minimal.sh
```

### Option 3: Installation manuelle standard

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

## Résolution des problèmes d'installation

### Erreur de conflit protobuf avec onnx/trainer

Si vous obtenez une erreur indiquant un conflit de dépendances impliquant protobuf, onnx et/ou trainer, utilisez les scripts de correction fournis :

#### Windows
```
fix_dependencies.bat
```

#### Linux/macOS
```
chmod +x fix_dependencies.sh
./fix_dependencies.sh
```

### Autres solutions de dépannage

1. **Installation manuelle dans un ordre spécifique**
   ```
   pip install protobuf==3.20.2
   pip install onnx==1.14.0
   pip install trainer==0.0.20 --no-deps
   pip install -r requirements.txt
   ```

2. **Pour Python 3.8 spécifiquement**
   ```
   pip install setuptools==65.5.0 wheel==0.38.0
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

## Résolution de problèmes courants

### Problèmes audio

- Assurez-vous que votre microphone est correctement configuré
- Vérifiez que ffmpeg est installé et accessible dans le PATH

### Erreurs à l'exécution

- Vérifiez que vous avez activé l'environnement virtuel
- En cas d'erreur liée à un module manquant, installez-le manuellement : `pip install <nom_du_module>`
- Pour les problèmes persistants, essayez l'installation minimale avec `install_minimal.bat` ou `install_minimal.sh`

## Contribution

Les contributions sont les bienvenues! Consultez le fichier CONTRIBUTING.md pour plus de détails.

## Licence

Ce projet est sous licence MIT - voir le fichier LICENSE pour plus de détails.
