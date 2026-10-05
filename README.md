# NotePro

Application web de **gestion de la vie scolaire** (type Pronote) pour **un établissement**.
Stack : **Django 5.2 LTS · PostgreSQL · ReportLab** (PDF) — interface en français, sans dépendance JavaScript externe.

## Fonctionnalités

| Module | Contenu |
|---|---|
| Comptes et rôles | Élève, Parent (lié à 1..n enfants), Enseignant, Administration ; connexion sécurisée, blocage anti brute-force, changement de mot de passe obligatoire |
| Emploi du temps | Vues classe / enseignant / élève, détection des conflits, annulations, changements de salle, remplacements, notifications |
| Carnet de notes | Évaluations (barème, coefficient, période), saisie en grille, moyennes par matière et générale pondérées, rang, stats de classe |
| Absences et retards | Appel par l'enseignant, saisie vie scolaire, justification par le parent (motif + document), vue consolidée, export CSV |
| Cahier de texte | Contenus de séance et devoirs par matière, échéances, suivi « fait » |
| Bulletins | Appréciations par matière et du conseil de classe, mentions, publication, export PDF (élève ou classe entière) |
| Messagerie | Conversations avec règles de destinataires par rôle, notifications, annonces ciblées |
| Tableau de bord | Vue personnalisée par rôle |

## Installation (Windows, développement)

Prérequis : Python 3.12+ et PostgreSQL 15+ (ou SQLite pour un essai rapide).

```powershell
cd $HOME\Desktop\NotePro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# Éditer .env : SECRET_KEY, DATABASE_URL, FIELD_ENCRYPTION_KEYS
# (pour un essai rapide sans PostgreSQL : supprimer la ligne DATABASE_URL -> SQLite)

python manage.py makemigrations accounts scolarite edt notes absences cahier bulletins messagerie finances core
python manage.py migrate
python manage.py seed_demo          # données fictives (DEBUG=True uniquement)
python manage.py createsuperuser    # optionnel
python manage.py runserver
```

Ouvrir http://127.0.0.1:8000 — comptes de démo : `admin`, `prof.math`, `eleve1`, `parent1`…
(mot de passe affiché par `seed_demo`).

Créer la base PostgreSQL :

```sql
CREATE USER notepro WITH PASSWORD 'notepro';
CREATE DATABASE notepro OWNER notepro;
```

## Tests

```powershell
python manage.py test                     # tous les tests
python manage.py test notes absences      # un ou plusieurs modules
python -m unittest notes.test_calculs     # calcul des moyennes, sans base de données
```

## Mise en place d'un établissement réel

Tout se fait dans **/admin** (compte Administration) :

1. Année scolaire (cocher « active ») et ses périodes.
2. Matières, salles.
3. Comptes enseignants, puis classes (avec professeur principal) et leurs **enseignements** (matière + enseignant + coefficient).
4. Comptes élèves (le profil élève est créé automatiquement : choisir la classe), comptes parents, puis **liens parent / élève** depuis la fiche élève.
5. Créneaux d'emploi du temps.

Chaque compte créé doit changer son mot de passe à la première connexion.
Action « Réinitialiser le mot de passe » dans la liste des utilisateurs en cas d'oubli.

## Déploiement cloud

Fonctionne sur tout hébergeur Python + PostgreSQL managé (Railway, Render, Scaleway, Clever Cloud, OVH…).

```text
Commande de build :  pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
Commande de démarrage : gunicorn config.wsgi --workers 3
Tâche planifiée (quotidienne) : python manage.py purge_rgpd
```

Variables d'environnement **obligatoires** en production : `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, `FIELD_ENCRYPTION_KEYS`, `PRIVATE_MEDIA_ROOT` (volume persistant).

> ⚠️ Conservez `FIELD_ENCRYPTION_KEYS` en lieu sûr : sans elle, les données chiffrées sont irrécupérables.
> Sauvegardez la base **et** le dossier des justificatifs.

Avant la mise en ligne : `python manage.py check --deploy`.

## Application mobile et API

- `api/` expose une API REST (`/api/`) protégée par JWT pour l'application mobile. Le contrôle d'accès est le même que sur le web : un parent ne voit que ses enfants.
- `finances/` gère les frais de scolarité et les paiements Mobile Money. Le fournisseur « sandbox » sert aux tests ; l'interface permet de brancher un opérateur réel.
- `mobile/` contient l'application Expo (Android, iOS et web). Voir `mobile/README.md` ou double-cliquer sur `mobile/lancer-mobile.bat`.

## Architecture

```text
config/       réglages (sécurité, base, chiffrement, RGPD)
core/         permissions centralisées, champ chiffré, stockage privé, journal d'accès, commandes
accounts/     utilisateurs, rôles, profils élève, liens parent/élève, export RGPD
scolarite/    année, périodes, classes, matières, salles, enseignements
edt/          créneaux, modifications de cours
notes/        évaluations, notes, calculs (calculs.py = module pur testé)
absences/     appel, absences, justificatifs
cahier/       contenus de séance, devoirs
bulletins/    appréciations, publication, PDF
messagerie/   conversations, notifications, annonces
dashboard/    tableaux de bord par rôle
```

Sécurité et RGPD : voir [docs/SECURITE_RGPD.md](docs/SECURITE_RGPD.md).
