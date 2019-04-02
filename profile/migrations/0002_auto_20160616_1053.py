# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='businessprofile',
            name='registration_number',
            field=models.CharField(default=b'', help_text='KvK nummer', max_length=14, blank=True),
        ),
        migrations.AddField(
            model_name='charityprofile',
            name='registration_number',
            field=models.CharField(default=b'', help_text='KvK nummer', max_length=14, blank=True),
        ),
        migrations.AddField(
            model_name='institutionprofile',
            name='registration_number',
            field=models.CharField(default=b'', help_text='KvK nummer', max_length=14, blank=True),
        ),
    ]
