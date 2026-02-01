release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn community_feed.wsgi:application --bind 0.0.0.0:$PORT --log-file -