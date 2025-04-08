@echo off
echo ====================================================
echo Installation de VocalClone pour Python 3.8
echo ====================================================
echo.

REM Vérifier si Python est installé
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python 3.8 ou supérieur.
    pause
    exit /b 1
)

REM Vérifier la version de Python
python --version | findstr /C:"Python 3.8" >nul
if %errorlevel% neq 0 (
    echo WARNING: Vous n'utilisez pas Python 3.8.
    echo Ce script est optimisé pour Python 3.8.
    echo Continuez à vos risques et périls.
    pause
)

echo Création de l'environnement virtuel...
python -m venv venv
if %errorlevel% neq 0 (
    echo Erreur lors de la création de l'environnement virtuel.
    pause
    exit /b 1
)

echo Activation de l'environnement virtuel...
call venv\Scripts\activate
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

echo Installation de protobuf 3.20.0 (requis pour résoudre les conflits)...
pip install protobuf==3.20.0
if %errorlevel% neq 0 (
    echo Erreur lors de l'installation de protobuf.
    pause
    exit /b 1
)

echo Installation des dépendances principales en ordre spécifique...
pip install torch==2.0.0
pip install transformers==4.33.0
pip install onnx==1.14.0
pip install onnxruntime==1.15.0
pip install trainer==0.0.20

echo Installation des autres dépendances...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Avertissement: Certaines dépendances n'ont pas pu être installées.
    echo Cela peut être dû à des conflits déjà résolus, l'application peut quand même fonctionner.
)

echo.
echo ====================================================
echo Installation terminée avec succès!
echo.
echo Pour lancer l'application:
echo 1. Assurez-vous que l'environnement virtuel est activé:
echo    call venv\Scripts\activate
echo.
echo 2. Lancez l'application:
echo    python src/main.py
echo.
echo 3. Pour la version française:
echo    python src/main.py --language fr
echo ====================================================
echo.

pause 