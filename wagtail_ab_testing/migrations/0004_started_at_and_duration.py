# Generated by Django 3.1.3 on 2020-11-19 17:36

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtail_ab_testing', '0003_abtest_winning_variant'),
    ]

    operations = [
        migrations.AddField(
            model_name='abtest',
            name='current_run_started_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='abtest',
            name='first_started_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='abtest',
            name='previous_run_duration',
            field=models.DurationField(default=datetime.timedelta(0)),
        ),
    ]
