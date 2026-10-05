# Sécurité et conformité RGPD — NotePro

NotePro traite des **données de mineurs**. Ce document décrit les mesures intégrées dès la conception
et ce qui reste à la charge de l'établissement (responsable de traitement).

## 1. Mesures techniques

| Risque | Mesure | Où |
|---|---|---|
| Vol de mots de passe | Hachage **Argon2**, 10 caractères minimum, mots courants refusés | `config/settings.py` |
| Brute-force | Blocage 15 min après 5 échecs (identifiant + IP), messages d'erreur génériques | django-axes |
| Mot de passe initial connu | Changement **obligatoire** à la première connexion | `core/middleware.py` |
| Injection SQL | ORM Django exclusivement (requêtes paramétrées), aucune requête SQL brute | tout le code |
| XSS | Échappement automatique des gabarits, **CSP** stricte (aucun script inline), échappement dans les PDF | `core/middleware.py`, `bulletins/pdf.py` |
| CSRF / clickjacking | Jetons CSRF, `X-Frame-Options: DENY`, `frame-ancestors 'none'` | Django |
| Accès non autorisé | Connexion requise partout ; contrôle **par rôle** et **par objet** centralisé dans `core/permissions.py` | toutes les vues |
| Interception | HTTPS forcé, HSTS 1 an, cookies `Secure`/`HttpOnly`/`SameSite` (hors DEBUG) | `config/settings.py` |
| Fuite de la base | Chiffrement **Fernet** (AES + HMAC) des données sensibles : téléphone, adresse, date de naissance, motif d'absence ; rotation de clés possible | `core/fields.py` |
| Documents sensibles | Justificatifs hors de l'espace web, renommés aléatoirement, type vérifié par signature binaire, 5 Mo max., téléchargement contrôlé et tracé | `core/storage.py`, `core/validators.py` |
| Cache navigateur | `Cache-Control: no-store` sur les pages authentifiées | `core/middleware.py` |
| Redirection ouverte | Liens de notification limités aux URL internes | `messagerie/views.py` |

### Matrice d'accès aux données d'élève

| Donnée | Élève | Parent | Enseignant | Administration |
|---|---|---|---|---|
| Notes publiées | lui-même | ses enfants | ses classes | toutes |
| Absences | lui-même | ses enfants | appel de ses cours | toutes |
| Motif / justificatif | — (« motif transmis ») | ses enfants | **non** | oui (tracé) |
| Bulletin | après publication | après publication | ses classes | tous |
| Messagerie | enseignants de sa classe + admin (**pas entre élèves**) | enseignants de ses enfants + admin | admin, collègues, élèves/parents de ses classes | tous |
| Conversations privées dans /admin | — | — | — | **non exposées** |

## 2. Principes RGPD dans le schéma

- **Minimisation** : pas de photo, pas de numéro de sécurité sociale, pas d'adresse obligatoire ; l'e-mail est facultatif.
  Les notifications par e-mail ne contiennent **aucune donnée scolaire** (simple invitation à se connecter), et sont désactivées par défaut.
- **Exactitude** : l'utilisateur consulte ses informations dans « Mon compte » et demande les corrections à l'administration.
- **Droit d'accès et portabilité** (art. 15 et 20) : bouton « Télécharger mes données » (JSON), qui inclut les données des enfants pour un parent.
- **Droit à l'effacement / fin de scolarité** : action admin « Anonymiser » (identité effacée, justificatifs supprimés, liens parentaux supprimés, compte désactivé) ; les données pédagogiques restent cohérentes pour les statistiques de classe sans être rattachables à une personne.
- **Limitation de la conservation** : commande `purge_rgpd` (à planifier chaque nuit) ; durées configurables :
  notifications 180 j, conversations 365 j, justificatifs et motifs 365 j, journal d'accès 365 j.
- **Traçabilité** : `JournalAcces` (lecture seule dans l'admin) pour les téléchargements de justificatifs et de bulletins, les exports et les anonymisations.
- **Publication maîtrisée** : notes masquables pendant la saisie, bulletins invisibles avant publication.

## 3. À la charge de l'établissement

1. Inscrire le traitement au **registre des traitements** (finalité : gestion de la scolarité ; base légale : mission d'intérêt public / obligation légale).
2. Informer élèves et familles (mentions d'information, durées de conservation, droits, contact du DPO).
3. Choisir un hébergeur conforme (de préférence UE, ou pays avec un niveau de protection adéquat) et signer un contrat de sous-traitance (art. 28).
4. Conserver la clé `FIELD_ENCRYPTION_KEYS` hors du serveur (coffre-fort de secrets) et la faire tourner périodiquement.
5. Activer des **sauvegardes chiffrées** de la base et du dossier des justificatifs.
6. Limiter le nombre de comptes Administration, et former les utilisateurs.
7. Lancer `python manage.py check --deploy` avant chaque mise en production.

## 4. Évolutions recommandées

- Double authentification (TOTP) pour les comptes Administration et Enseignant (`django-otp`).
- Stockage des justificatifs sur un bucket S3 privé chiffré (`django-storages`).
- Analyse antivirus des fichiers déposés (ClamAV).
- Journal des modifications de notes (historique / audit).
