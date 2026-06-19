# Lyncare Backend

Django REST API for clinic visits, lab, pharmacy, and billing.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo --password demo1234
python manage.py runserver
```

## Seed demo users

```bash
python manage.py seed_demo --password demo1234
python manage.py seed_demo --reset --password demo1234
```

## Production

Set in `.env`:

```
DB_ENGINE=postgresql
DB_NAME=lyncare
DB_USER=lyncare
DB_PASSWORD=...
DB_HOST=db
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=your-domain.com,backend
CORS_ALLOWED_ORIGINS=https://your-frontend.com
```

Docker:

```bash
docker build -t lyncare-api .
docker run -p 8000:8000 --env-file .env lyncare-api
```

The container runs migrations, seeds demo users, and starts Gunicorn.
