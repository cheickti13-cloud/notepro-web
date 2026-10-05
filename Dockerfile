# NotePro — image de production (Django + gunicorn + whitenoise)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATABASE_URL=sqlite:////app/data/db.sqlite3

WORKDIR /app

# Dépendances Python (couche mise en cache tant que requirements.txt ne change pas)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Code de l'application
COPY . .

# Fichiers statiques compressés (clé factice : uniquement pour cette étape de build)
RUN SECRET_KEY=build-only FIELD_ENCRYPTION_KEYS=l9Zf8gd_hwdzfDDS70eg1QqVr9YrcaSVHad9WBEDn3g= \
    python manage.py collectstatic --noinput

# Utilisateur sans privilèges
RUN useradd --create-home --uid 10001 notepro \
    && mkdir -p /app/private_media /app/data \
    && chown -R notepro:notepro /app/private_media /app/data
USER notepro

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/compte/connexion/', timeout=4).status == 200 else 1)"

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
