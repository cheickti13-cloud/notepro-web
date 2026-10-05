@echo off
REM Lance tous les tests automatises et enregistre le resultat dans resultats-tests.txt
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Lancez d'abord lancer-notepro.bat & pause & exit /b 1)
.venv\Scripts\python.exe manage.py test --noinput -v 2 > resultats-tests.txt 2>&1
type resultats-tests.txt | more
echo.
echo Resultat complet enregistre dans resultats-tests.txt
pause
