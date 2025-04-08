#!/bin/bash

echo "===================================================="
echo "Installation minimale de VocalClone"
echo "===================================================="
echo

echo "Ce script installe uniquement les dépendances essentielles"
echo "pour faire fonctionner l'application de base."
echo

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    echo "Python n'est pas installé ou n'est pas dans le PATH."
    echo "Veuillez installer Python 3.8 ou supérieur."
    exit 1
fi

echo "Création de l'environnement virtuel..."
python3 -m venv venv-minimal
if [ $? -ne 0 ]; then
    echo "Erreur lors de la création de l'environnement virtuel."
    exit 1
fi

echo "Activation de l'environnement virtuel..."
source venv-minimal/bin/activate
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

echo "Installation des dépendances minimales..."
pip install torch==2.0.0
pip install protobuf==3.20.2
pip install PySide6==6.4.2
pip install numpy==1.21.0
pip install scipy==1.11.2
pip install sounddevice==0.4.6
pip install soundfile==0.12.1
pip install TTS==0.14.3
pip install librosa==0.10.0
pip install transformers==4.33.0
pip install tqdm==4.66.1
pip install python-rtmidi==1.5.8
pip install matplotlib==3.7.0
if [ $? -ne 0 ]; then
    echo "Avertissement: Certaines dépendances n'ont pas pu être installées."
    echo "L'application peut fonctionner quand même, avec des fonctionnalités limitées."
fi

echo "Installation de onnx et trainer..."
pip install onnx==1.14.0
pip install trainer==0.0.20 --no-deps
if [ $? -ne 0 ]; then
    echo "Avertissement: Les packages onnx ou trainer n'ont pas pu être installés."
    echo "Certaines fonctionnalités peuvent ne pas fonctionner."
fi

echo
echo "===================================================="
echo "Installation minimale terminée !"
echo
echo "Pour lancer l'application:"
echo "1. Assurez-vous que l'environnement virtuel est activé:"
echo "   source venv-minimal/bin/activate"
echo
echo "2. Lancez l'application:"
echo "   python src/main.py"
echo
echo "REMARQUE: Certaines fonctionnalités peuvent ne pas être disponibles"
echo "avec cette installation minimale."
echo "===================================================="
echo 