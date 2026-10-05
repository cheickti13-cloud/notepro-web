@echo off
chcp 65001 >nul
title NotePro Mobile
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo [ERREUR] Node.js n'est pas installe. Telechargez la version LTS sur https://nodejs.org
  pause
  exit /b 1
)

if not exist node_modules (
  echo Installation des dependances...
  call npm install || goto :erreur
  call npx expo install --fix || goto :erreur
)

echo.
echo Scannez le QR code avec Expo Go (meme Wi-Fi que ce PC). Touche "w" pour la version web.
echo.
call npx expo start
goto :eof

:erreur
echo [ERREUR] L'installation a echoue. Verifiez votre connexion internet.
pause
exit /b 1
