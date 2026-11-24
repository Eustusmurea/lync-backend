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
    ('scientist', 'Achieng', 'Scientist', 'scientist@lyncare.local', 'scientist'),
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
        self.stdout.write(
            'Login usernames: admin, reception, dr.jane, lab.tech, scientist, pharmacist, accountant'
        )

    def _seed_lab_panels(self):
        from apps.tests.models import TestPanel, TestParameter

        panels = [
            ('CBC', 'Complete Blood Count', 'haematology', '58410-2', 1200, [
                ('WBC', '6690-2', '10^9/L', 4.0, 11.0, 2.0, 30.0),
                ('RBC', '789-8', '10^12/L', 4.5, 5.5, 2.0, 8.0),
                ('HGB', '718-7', 'g/dL', 12.0, 17.0, 7.0, 20.0),
            ]),
            ('RFT', 'Renal Function Test', 'chemistry', '', 1500, [
                ('Creatinine', '2160-0', 'mg/dL', 0.6, 1.2, 0.2, 8.0),
                ('Urea', '3091-6', 'mg/dL', 15, 45, 5, 200),
            ]),
            ('LFT', 'Liver Function Test', 'chemistry', '24325-3', 1800, [
                ('ALT', '1742-6', 'U/L', 7, 56, None, 1000),
                ('AST', '1920-8', 'U/L', 10, 40, None, 1000),
            ]),
        ]

        for code, name, discipline, panel_loinc, price, params in panels:
            panel, _ = TestPanel.objects.get_or_create(
                code=code,
                defaults={'name': name, 'price': price, 'sla_hours': 4},
            )
            panel.discipline = discipline
            panel.loinc_code = panel_loinc
            panel.name = name
            panel.save(update_fields=['discipline', 'loinc_code', 'name'])
            for i, (pname, loinc, unit, lo, hi, crit_lo, crit_hi) in enumerate(params):
                parameter, _ = TestParameter.objects.get_or_create(
                    panel=panel,
                    name=pname,
                    defaults={
                        'unit': unit,
                        'loinc_code': loinc,
                        'ref_range_low': lo,
                        'ref_range_high': hi,
                        'critical_low': crit_lo,
                        'critical_high': crit_hi,
                        'order': i,
                    },
                )
                parameter.loinc_code = loinc
                parameter.unit = unit
                parameter.ref_range_low = lo
                parameter.ref_range_high = hi
                parameter.critical_low = crit_lo
                parameter.critical_high = crit_hi
                parameter.order = i
                parameter.save()

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
