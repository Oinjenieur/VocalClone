@echo off
echo ====================================================
echo Réparation des conflits de dépendances VocalClone
echo ====================================================
echo.

echo Ce script va réparer les conflits de dépendances entre onnx et trainer.
echo Il est conçu pour être exécuté dans un environnement virtuel existant.
echo.

echo Désinstallation des packages problématiques...
pip uninstall -y protobuf onnx trainer
if %errorlevel% neq 0 (
    echo Avertissement: Certains packages n'ont pas pu être désinstallés.
    echo Continuons tout de même...
)

echo Installation des packages dans l'ordre correct...
pip install protobuf==3.20.2
if %errorlevel% neq 0 (
    echo Erreur lors de l'installation de protobuf.
    pause
    exit /b 1
)

echo Installation d'onnx avec la bonne version de protobuf...
pip install onnx==1.14.0
if %errorlevel% neq 0 (
    echo Erreur lors de l'installation d'onnx.
    pause
    exit /b 1
)

echo Installation d'onnxruntime...
pip install onnxruntime==1.15.0
if %errorlevel% neq 0 (
    echo Erreur lors de l'installation d'onnxruntime.
    pause
    exit /b 1
)

echo Installation de trainer sans dépendances...
pip install trainer==0.0.20 --no-deps
if %errorlevel% neq 0 (
    echo Erreur lors de l'installation de trainer.
    pause
    exit /b 1
)

echo.
echo ====================================================
echo Réparation terminée !
echo.
echo Si vous rencontrez encore des erreurs au lancement de l'application,
echo essayez d'exécuter install_py38.bat pour une installation complète.
echo ====================================================
echo.

pause 