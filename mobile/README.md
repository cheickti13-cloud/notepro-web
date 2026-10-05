# NotePro Mobile

Application mobile NotePro (Android, iOS et web) : Expo SDK 56, expo-router et TypeScript.
Elle se connecte au serveur Django NotePro via l'API REST `/api/`. Un **mode démo** intégré permet de la tester sans serveur.

## Prérequis

- Node.js 20 ou plus récent ([nodejs.org](https://nodejs.org))
- L'application **Expo Go** sur votre téléphone (Play Store / App Store)

## Lancer l'application

Sous Windows, double-cliquez sur `lancer-mobile.bat`. Sinon, lancez :

```bash
cd mobile
npm install
npx expo install --fix     # aligne les versions des modules sur le SDK 56
npx expo start
```

Ensuite :

- **Téléphone** : scannez le QR code avec Expo Go (Android) ou avec l'appareil photo (iOS). Le téléphone et le PC doivent être sur le même Wi-Fi.
- **Web** : appuyez sur `w` dans le terminal.
- **Émulateur Android** : appuyez sur `a`.

## Mode démo

Sur l'écran de connexion, choisissez l'établissement « Démo NotePro ». Saisissez n'importe quel identifiant et choisissez le rôle (parent, élève, enseignant ou administration). Les données sont fictives : deux enfants, Aïcha (3e A) et Ibrahim (6e B), avec des dates calculées à partir d'aujourd'hui.

## Se connecter au serveur Django

1. Démarrez le serveur pour qu'il soit joignable depuis le réseau local :
   `python manage.py runserver 0.0.0.0:8000`
2. Trouvez l'adresse IP du PC avec `ipconfig` (par exemple 192.168.1.20).
3. Dans l'application, ouvrez « Changer d'établissement » puis ajoutez `http://192.168.1.20:8000`.
   Vous pouvez aussi copier `.env.example` vers `.env` et y mettre `EXPO_PUBLIC_API_URL`.
4. Côté serveur, ajoutez l'origine web de l'application à `CORS_ALLOWED_ORIGINS` (uniquement pour la version web).
5. Ajoutez aussi l'IP du PC à `DJANGO_ALLOWED_HOSTS`.

Les comptes de démonstration créés par `python manage.py seed_demo` fonctionnent. La connexion est possible par identifiant, e-mail ou numéro de téléphone.

## Fonctionnalités

- Connexion sécurisée : jetons JWT stockés dans SecureStore, déverrouillage biométrique, changement de mot de passe obligatoire au premier accès.
- Choix de l'établissement, avec un serveur par établissement.
- Tableau de bord : cours du jour, dernières notes, devoirs, alertes. Sélecteur d'enfant pour les parents.
- Emploi du temps : vue jour et vue semaine, modifications de cours, ajout au calendrier du téléphone.
- Notes : moyennes pondérées, évolution, comparaison avec le trimestre précédent, détail par matière, bulletin PDF.
- Devoirs : statut à faire, en cours ou terminé, pièces jointes, rappel local.
- Absences et retards : justification avec photo ou PDF, déclaration d'absence anticipée.
- Messagerie avec pièces jointes, notifications push et centre de notifications.
- Vie scolaire : actualités, événements, examens, vacances, documents.
- Frais de scolarité : paiement Mobile Money (bac à sable) et reçu PDF.
- Mode sombre, mode hors ligne (cache persistant) et accessibilité (libellés, tailles tactiles de 44 px minimum).

## Notifications push et builds

Les notifications push nécessitent un projet EAS :

1. `npx eas init` renseigne `extra.eas.projectId` dans `app.json`.
2. `npx eas build -p android --profile preview` produit un APK installable.
3. `npx eas build -p ios` nécessite un compte Apple Developer.

## Structure

```
src/app/          écrans (expo-router) ; (app)/(onglets) = barre d'onglets
src/components/   composants d'interface (ui.tsx) et métier (metier.tsx)
src/lib/          API, session, mode démo, cache hors ligne, formats
src/theme/        couleurs clair/sombre
```
