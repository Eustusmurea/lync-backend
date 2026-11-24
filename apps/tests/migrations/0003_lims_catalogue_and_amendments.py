from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tests', '0002_testorder_visit'),
    ]

    operations = [
        migrations.AddField(
            model_name='testpanel',
            name='discipline',
            field=models.CharField(
                blank=True,
                choices=[
                    ('haematology', 'Haematology'),
                    ('chemistry', 'Clinical Chemistry'),
                    ('microbiology', 'Microbiology'),
                    ('immunology', 'Immunology'),
                    ('histopathology', 'Histopathology'),
                    ('cytology', 'Cytology'),
                ],
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='testpanel',
            name='loinc_code',
            field=models.CharField(blank=True, help_text='Published LOINC code for the panel, when one exists', max_length=20),
        ),
        migrations.AddField(
            model_name='testparameter',
            name='loinc_code',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.CreateModel(
            name='ResultAmendment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('previous_value', models.CharField(max_length=100)),
                ('previous_numeric_value', models.FloatField(blank=True, null=True)),
                ('previous_flag', models.CharField(max_length=20)),
                ('new_value', models.CharField(max_length=100)),
                ('reason', models.TextField()),
                ('amended_at', models.DateTimeField(auto_now_add=True)),
                ('amended_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='result_amendments', to=settings.AUTH_USER_MODEL)),
                ('result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='amendments', to='tests.testresult')),
            ],
            options={'ordering': ['amended_at']},
        ),
    ]
