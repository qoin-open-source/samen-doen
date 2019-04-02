# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0001_initial'),
        ('cyclos', '0003_auto_20160609_1610'),
        ('profile', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdRewardCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ad', models.ForeignKey(to='marketplace.Ad')),
            ],
        ),
        migrations.CreateModel(
            name='CommunityWoonplaat',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('woonplaat', models.CharField(help_text='Woonplaat (residence) received in the Stadlander SSO info', max_length=255)),
                ('community', models.ForeignKey(to='cyclos.CC3Community')),
            ],
            options={
                'ordering': ['community', 'woonplaat'],
            },
        ),
        migrations.CreateModel(
            name='RewardCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveIntegerField(default=1, editable=False, db_index=True)),
                ('title', models.CharField(help_text='Reward Category title', max_length=100)),
                ('description', models.CharField(help_text='Reward Category description', max_length=255)),
                ('reward_first_ad', models.BooleanField(default=False, help_text='If True, user gets a reward for their first advert in this category')),
                ('active', models.BooleanField(default=True, help_text='Marks this Reward Category as active')),
            ],
            options={
                'ordering': ('order', 'title'),
                'abstract': False,
                'verbose_name': 'Stadlander specifieke categorie\xebn',
                'verbose_name_plural': 'stadlander specifieke categorie\xebn',
            },
        ),
        migrations.CreateModel(
            name='StadlanderProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rel_number', models.IntegerField()),
                ('profile', models.OneToOneField(to='profile.UserProfile')),
            ],
        ),
        migrations.AddField(
            model_name='adrewardcategory',
            name='reward_category',
            field=models.ForeignKey(to='stadlander.RewardCategory'),
        ),
        migrations.AlterUniqueTogether(
            name='communitywoonplaat',
            unique_together=set([('community', 'woonplaat')]),
        ),
    ]
