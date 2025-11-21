#!/usr/bin/env bash
# Build script for Render deployment
# Desenvolvedor: Maxwell da Silva Oliveira

set -o errexit  # exit on error

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running database migrations..."
python manage.py migrate --no-input

echo "Creating superuser (if not exists)..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@gestaocontrato.com', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Superuser already exists')
EOF

echo "Build completed successfully!"
