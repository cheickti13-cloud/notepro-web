web: gunicorn config.wsgi --workers 3 --log-file -
release: python manage.py migrate --noinput
