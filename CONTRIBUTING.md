# Contribuer à VocalClone

Merci de votre intérêt pour contribuer à VocalClone ! Ce document contient les directives pour contribuer au projet.

## Comment contribuer

### Signalement de bugs

Si vous trouvez un bug :

1. Vérifiez d'abord que le bug n'a pas déjà été signalé dans les issues
2. Ouvrez une nouvelle issue avec un titre clair
3. Décrivez en détail :
   - Comment reproduire le bug
   - Le comportement attendu vs observé
   - Votre environnement (OS, version Python, etc.)
   - Si possible, ajoutez des captures d'écran

### Suggestions de fonctionnalités

1. Ouvrez une issue avec le préfixe "[Suggestion]"
2. Décrivez la fonctionnalité souhaitée et pourquoi elle serait utile
3. Indiquez si vous seriez prêt à la développer vous-même

### Pull requests

1. Créez une branche à partir de la branche `main`
2. Codez votre fonctionnalité ou correction
3. Ajoutez ou mettez à jour les tests si nécessaire
4. Vérifiez que tous les tests passent
5. Créez une pull request vers la branche `main`
6. Dans la description de la PR, expliquez vos changements et référencez l'issue associée

## Style de code

- Suivez les conventions PEP 8 pour Python
- Utilisez des docstrings pour documenter les fonctions et classes
- Commentez votre code quand il est complexe
- Faites des commits atomiques avec des messages clairs

## Configuration de l'environnement de développement

```bash
# Créer un environnement virtuel
python -m venv venv-dev
source venv-dev/bin/activate  # Linux/Mac
# ou
venv-dev\Scripts\activate     # Windows

# Installer les dépendances de développement
pip install -r requirements-dev.txt
```

## Tests

Avant de soumettre une PR, exécutez les tests :

```bash
python run_tests.py
```

Merci pour votre contribution ! 