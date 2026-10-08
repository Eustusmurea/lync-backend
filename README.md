# Lyncare Backend

Django REST API for a clinic management platform. It supports the full patient visit: registration, consultation, lab orders and results, prescriptions, pharmacy dispensing, and billing.

**Status:** in development.

## Why this project exists

A clinic visit involves several people, each needing a different view of the same patient. Lyncare models the **visit** as a single shared record that moves through stages, so every role works from one source of truth without copying data.

## Visit workflow

1. **Receptionist:** registers the patient and opens a visit.
2. **Clinician:** records vitals, runs the consultation, and orders lab tests.
3. **Lab technician:** enters results, and the visit moves to *Results Ready*.
4. **Clinician:** records a diagnosis and prescription.
5. **Pharmacist:** dispenses medicine.
6. **Accountant:** generates the invoice and collects payment.

## Architecture

The backend is split into Django apps, one per area, so each stage stays isolated in code but links back to one patient and one visit.

| App | Responsibility |
|---|---|
| `users` | Accounts, roles, and authentication |
| `visits` | The visit record and its stages |
| `samples` | [confirm: lab samples] |
| `tests` | [confirm: lab test orders and results] |
| `pharmacy` | Prescriptions and dispensing |
| `inventory` | Stock |
| `billing` | Invoices and payments |
| `reports` | [confirm: reporting] |

**Stack:** Python, Django, Django REST Framework, JWT authentication (`simplejwt`), `django-filter`, `django-cors-headers`, PostgreSQL (production), SQLite (local development), Docker, Gunicorn.

## Roles and permissions

[Describe how roles are enforced, for example custom DRF permission classes that check the user's role, and which role can read or write which resource.]

## Getting started

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo --password demo1234
python manage.py runserver
```

Reset demo users:

```bash
python manage.py seed_demo --reset --password demo1234
```

## Production

Set these in `.env` (never commit this file):

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

## API

[Add a short endpoint overview, or link to API docs if you generate them.]

## Tests

[Add how to run tests, e.g. `python manage.py test`, if you have them.]

## Team

- **Backend:** Eustus Mwirigi (sole backend developer)
- **Frontend:** built collaboratively with one teammate: [link to frontend repo]
