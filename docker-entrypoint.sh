#!/bin/sh
# Démarrage du conteneur : migrations, données de démo facultatives, puis serveur.
set -e

python manage.py migrate --noinput

# SEED_DEMO=1 : remplit une base vide avec les comptes de démonstration
if [ "${SEED_DEMO:-0}" = "1" ]; then
  python manage.py seed_demo || echo "Données de démo déjà présentes."
fi

exec "$@"
