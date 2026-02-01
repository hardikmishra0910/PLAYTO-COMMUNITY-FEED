#!/bin/bash
echo "Starting build process..."
python manage.py collectstatic --noinput
python manage.py migrate
echo "Build completed successfully!"