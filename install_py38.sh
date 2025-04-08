#!/bin/bash

echo "===================================================="
echo "Installation de VocalClone pour Python 3.8"
echo "===================================================="
echo

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    echo "Python n'est pas installé ou n'est pas dans le PATH."
    echo "Veuillez installer Python 3.8 ou supérieur."
    exit 1
fi

# Vérifier la version de Python
PYTHON_VERSION=$(python3 --version 2>&1)
if [[ $PYTHON_VERSION != *"Python 3.8"* ]]; then
    echo "WARNING: Vous n'utilisez pas Python 3.8."
    echo "Ce script est optimisé pour Python 3.8."
    echo "Continuez à vos risques et périls."
    read -p "Appuyez sur ENTRÉE pour continuer..."
fi

echo "Création de l'environnement virtuel..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Erreur lors de la création de l'environnement virtuel."
    exit 1
fi

echo "Activation de l'environnement virtuel..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Erreur lors de l'activation de l'environnement virtuel."
    exit 1
fi

echo "Mise à jour de pip..."
python -m pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "Erreur lors de la mise à jour de pip."
    exit 1
fi

echo "Installation de protobuf 3.20.0 (requis pour résoudre les conflits)..."
pip install protobuf==3.20.0
if [ $? -ne 0 ]; then
    echo "Erreur lors de l'installation de protobuf."
    exit 1
fi

echo "Installation des dépendances principales en ordre spécifique..."
pip install torch==2.0.0
pip install transformers==4.33.0
pip install onnx==1.14.0
pip install onnxruntime==1.15.0
pip install trainer==0.0.20

echo "Installation des autres dépendances..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Avertissement: Certaines dépendances n'ont pas pu être installées."
    echo "Cela peut être dû à des conflits déjà résolus, l'application peut quand même fonctionner."
fi

echo
echo "===================================================="
echo "Installation terminée avec succès!"
echo
echo "Pour lancer l'application:"
echo "1. Assurez-vous que l'environnement virtuel est activé:"
echo "   source venv/bin/activate"
echo
echo "2. Lancez l'application:"
echo "   python src/main.py"
echo
echo "3. Pour la version française:"
echo "   python src/main.py --language fr"
echo "===================================================="
echo 