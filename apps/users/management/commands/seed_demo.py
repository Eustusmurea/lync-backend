"""
Seed demo users (one per role) and baseline lab panels for testing.

Usage:
    python manage.py seed_demo --password demo1234
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

DEMO_USERS = [
    ('admin', 'Admin', 'User', 'admin@lyncare.local', 'admin'),
    ('reception', 'Reception', 'Desk', 'reception@lyncare.local', 'receptionist'),
    ('dr.jane', 'Jane', 'Clinician', 'clinician@lyncare.local', 'clinician'),
    ('lab.tech', 'Lab', 'Technician', 'lab@lyncare.local', 'technician'),
    ('pharmacist', 'Pharmacy', 'Staff', 'pharmacy@lyncare.local', 'pharmacist'),
    ('accountant', 'Finance', 'Officer', 'billing@lyncare.local', 'accountant'),
]


class Command(BaseCommand):
    help = 'Create role-specific demo users and baseline test data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default='demo1234',
            help='Password for all demo users (default: demo1234)',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo users before seeding',
        )

    def handle(self, *args, **options):
        password = options['password']

        if options['reset']:
            usernames = [u[0] for u in DEMO_USERS]
            deleted, _ = User.objects.filter(username__in=usernames).delete()
            self.stdout.write(f'Removed {deleted} existing demo user(s)')

        for username, first, last, email, role in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'email': email,
                    'role': role,
                    'is_staff': role == 'admin',
                    'is_superuser': role == 'admin',
                },
            )
            if not created:
                user.first_name = first
                user.last_name = last
                user.email = email
                user.role = role
                user.is_active = True
            user.set_password(password)
            user.save()
            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{action} {username} ({role})'))

        self._seed_lab_panels()
        self.stdout.write(self.style.SUCCESS(f'\nAll demo users use password: {password}'))
        self.stdout.write('Login usernames: admin, reception, dr.jane, lab.tech, pharmacist, accountant')

    def _seed_lab_panels(self):
        from apps.tests.models import TestPanel, TestParameter

        panels = [
            ('CBC', 'Complete Blood Count', 1200, [
                ('WBC', '10^9/L', 4.0, 11.0),
                ('RBC', '10^12/L', 4.5, 5.5),
                ('HGB', 'g/dL', 12.0, 17.0),
            ]),
            ('RFT', 'Renal Function Test', 1500, [
                ('Creatinine', 'mg/dL', 0.6, 1.2),
                ('Urea', 'mg/dL', 15, 45),
            ]),
            ('LFT', 'Liver Function Test', 1800, [
                ('ALT', 'U/L', 7, 56),
                ('AST', 'U/L', 10, 40),
            ]),
        ]

        for code, name, price, params in panels:
            panel, _ = TestPanel.objects.get_or_create(
                code=code,
                defaults={'name': name, 'price': price, 'sla_hours': 4},
            )
            for i, (pname, unit, lo, hi) in enumerate(params):
                TestParameter.objects.get_or_create(
                    panel=panel,
                    name=pname,
                    defaults={
                        'unit': unit,
                        'ref_range_low': lo,
                        'ref_range_high': hi,
                        'order': i,
                    },
                )

        self.stdout.write('Lab panels seeded (CBC, RFT, LFT)')
        self._seed_drugs()

    def _seed_drugs(self):
        from apps.pharmacy.models import Drug, DrugCategory

        cat, _ = DrugCategory.objects.get_or_create(name='General')
        for name, strength, price in [
            ('Paracetamol', '500mg', 5),
            ('Amoxicillin', '500mg', 15),
            ('Metformin', '500mg', 8),
        ]:
            Drug.objects.get_or_create(
                name=name,
                strength=strength,
                defaults={'category': cat, 'unit_price': price, 'stock_quantity': 500},
            )
        self.stdout.write('Sample drugs seeded')
