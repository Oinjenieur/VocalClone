@echo off
echo ====================================================
echo Installation minimale de VocalClone
echo ====================================================
echo.

echo Ce script installe uniquement les dépendances essentielles
echo pour faire fonctionner l'application de base.
echo.

REM Vérifier si Python est installé
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python 3.8 ou supérieur.
    pause
    exit /b 1
)

echo Création de l'environnement virtuel...
python -m venv venv-minimal
if %errorlevel% neq 0 (
    echo Erreur lors de la création de l'environnement virtuel.
    pause
    exit /b 1
)

echo Activation de l'environnement virtuel...
call venv-minimal\Scripts\activate
if %errorlevel% neq 0 (
    echo Erreur lors de l'activation de l'environnement virtuel.
    pause
    exit /b 1
)

echo Mise à jour de pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo Erreur lors de la mise à jour de pip.
    pause
    exit /b 1
)

echo Installation des dépendances minimales...
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
if %errorlevel% neq 0 (
    echo Avertissement: Certaines dépendances n'ont pas pu être installées.
    echo L'application peut fonctionner quand même, avec des fonctionnalités limitées.
)

echo Installation de onnx et trainer...
pip install onnx==1.14.0
pip install trainer==0.0.20 --no-deps
if %errorlevel% neq 0 (
    echo Avertissement: Les packages onnx ou trainer n'ont pas pu être installés.
    echo Certaines fonctionnalités peuvent ne pas fonctionner.
)

echo.
echo ====================================================
echo Installation minimale terminée !
echo.
echo Pour lancer l'application:
echo 1. Assurez-vous que l'environnement virtuel est activé:
echo    call venv-minimal\Scripts\activate
echo.
echo 2. Lancez l'application:
echo    python src/main.py
echo.
echo REMARQUE: Certaines fonctionnalités peuvent ne pas être disponibles
echo avec cette installation minimale.
echo ====================================================
echo.

pause 