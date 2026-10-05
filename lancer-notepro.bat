@echo off
REM ============================================================
REM  NotePro - installation et lancement en un double-clic
REM  (essai local avec SQLite, donnees de demonstration)
REM ============================================================
setlocal
cd /d "%~dp0"
title NotePro

REM --- 1. Trouver Python ---------------------------------------
REM (on teste reellement l'execution : le raccourci Microsoft Store
REM  "python.exe" de WindowsApps existe meme quand Python n'est pas installe)
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (python --version >nul 2>nul && set "PY=python")
if not defined PY (
  echo [ERREUR] Python n'est pas installe.
  echo Installez Python 3.12+ depuis https://www.python.org/downloads/
  echo en cochant "Add python.exe to PATH", puis relancez ce fichier.
  pause & exit /b 1
)
%PY% --version

REM --- 2. Environnement virtuel + dependances ------------------
if not exist ".venv\Scripts\python.exe" (
  echo Creation de l'environnement virtuel...
  %PY% -m venv .venv || (echo [ERREUR] venv & pause & exit /b 1)
)
set "VPY=.venv\Scripts\python.exe"
echo Installation des dependances (premiere fois : 1 a 3 minutes)...
"%VPY%" -m pip install --upgrade pip -q
"%VPY%" -m pip install -r requirements.txt -q || (echo [ERREUR] installation des dependances & pause & exit /b 1)

REM --- 3. Fichier .env (genere une seule fois) -----------------
if not exist ".env" (
  echo Generation du fichier .env...
  "%VPY%" -c "import secrets;from cryptography.fernet import Fernet;open('.env','w').write('DEBUG=True\nSECRET_KEY='+secrets.token_urlsafe(50)+'\nALLOWED_HOSTS=localhost,127.0.0.1\nFIELD_ENCRYPTION_KEYS='+Fernet.generate_key().decode()+'\nETABLISSEMENT_NOM=Lycee NotePro (demo)\nTIME_ZONE=Africa/Abidjan\n')"
)

REM --- 4. Base de donnees -------------------------------------
"%VPY%" manage.py makemigrations accounts scolarite edt notes absences cahier bulletins messagerie finances core || (echo [ERREUR] makemigrations & pause & exit /b 1)
"%VPY%" manage.py migrate || (echo [ERREUR] migrate & pause & exit /b 1)

REM --- 5. Donnees de demo (seulement si la base est vide) ------
"%VPY%" manage.py seed_demo

REM --- 6. Lancement --------------------------------------------
echo.
echo ============================================================
echo  NotePro tourne sur http://127.0.0.1:8000
echo  Comptes : admin / prof.math / eleve1 / parent1
echo  Mot de passe : Demo-NotePro-2026
echo  Fermez cette fenetre pour arreter le serveur.
echo ============================================================
start "" http://127.0.0.1:8000
"%VPY%" manage.py runserver
pause
