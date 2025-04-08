#!/bin/bash

echo "===================================================="
echo "Réparation des conflits de dépendances VocalClone"
echo "===================================================="
echo

echo "Ce script va réparer les conflits de dépendances entre onnx et trainer."
echo "Il est conçu pour être exécuté dans un environnement virtuel existant."
echo

echo "Désinstallation des packages problématiques..."
pip uninstall -y protobuf onnx trainer
if [ $? -ne 0 ]; then
    echo "Avertissement: Certains packages n'ont pas pu être désinstallés."
    echo "Continuons tout de même..."
fi

echo "Installation des packages dans l'ordre correct..."
pip install protobuf==3.20.2
if [ $? -ne 0 ]; then
    echo "Erreur lors de l'installation de protobuf."
    exit 1
fi

echo "Installation d'onnx avec la bonne version de protobuf..."
pip install onnx==1.14.0
if [ $? -ne 0 ]; then
    echo "Erreur lors de l'installation d'onnx."
    exit 1
fi

echo "Installation d'onnxruntime..."
pip install onnxruntime==1.15.0
if [ $? -ne 0 ]; then
    echo "Erreur lors de l'installation d'onnxruntime."
    exit 1
fi

echo "Installation de trainer sans dépendances..."
pip install trainer==0.0.20 --no-deps
if [ $? -ne 0 ]; then
    echo "Erreur lors de l'installation de trainer."
    exit 1
fi

echo
echo "===================================================="
echo "Réparation terminée !"
echo
echo "Si vous rencontrez encore des erreurs au lancement de l'application,"
echo "essayez d'exécuter install_py38.sh pour une installation complète."
echo "===================================================="
echo 