# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.auth.models
from icare4u_front.community_admin.models import ProductUserManager


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CommunityCardMachineUserProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'User (Community Card Machine User)',
                'managed': False,
                'proxy': True,
                'verbose_name_plural': 'Users (Community Card Machine Users)',
            },
            bases=('cyclos.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='CommunityCardUserProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'User (Community Card User)',
                'managed': False,
                'proxy': True,
                'verbose_name_plural': 'Users (Community Card Users)',
            },
            bases=('cyclos.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='CommunityProductUserProfileProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'Profile (Community Product User Profile)',
                'managed': False,
                'proxy': True,
                'verbose_name_plural': 'Profile (Community Product User Profile)',
            },
            bases=('cyclos.cc3profile',),
            managers=[
                ('objects', ProductUserManager()),
            ],
        ),
    ]
