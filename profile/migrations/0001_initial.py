# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import localflavor.generic.models
import icare4u_front.profile.validators
import cc3.core.utils


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0003_auto_20160609_1610'),
    ]

    operations = [
        migrations.CreateModel(
            name='BusinessProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('account_holder', models.CharField(default=b'', max_length=255, blank=True)),
                ('iban', localflavor.generic.models.IBANField(max_length=34, null=True, verbose_name='IBAN nummer', blank=True)),
                ('bic_code', models.CharField(blank=True, max_length=11, null=True, verbose_name='BIC code', validators=[icare4u_front.profile.validators.swift_bic_validator])),
                ('mandate_id', models.CharField(max_length=35, null=True, verbose_name='Mandaat ID', blank=True)),
                ('signature_date', models.DateField(null=True, verbose_name='Datum handtekening', blank=True)),
                ('latest_payment_date', models.DateTimeField(help_text='Tijd van de laatste SEPA debit verwerking time.', null=True, blank=True)),
                ('vat_number', models.CharField(default=b'', help_text='BTW Nummer', max_length=14, blank=True)),
            ],
            options={
                'ordering': ('profile',),
                'verbose_name': 'Winkeliersprofiel',
                'verbose_name_plural': 'Winkeliersprofielen',
            },
        ),
        migrations.CreateModel(
            name='CharityProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('account_holder', models.CharField(default=b'', max_length=255, blank=True)),
                ('iban', localflavor.generic.models.IBANField(max_length=34, null=True, verbose_name='IBAN nummer', blank=True)),
                ('bic_code', models.CharField(blank=True, max_length=11, null=True, verbose_name='BIC code', validators=[icare4u_front.profile.validators.swift_bic_validator])),
                ('mandate_id', models.CharField(max_length=35, null=True, verbose_name='Mandaat ID', blank=True)),
                ('signature_date', models.DateField(null=True, verbose_name='Datum handtekening', blank=True)),
                ('latest_payment_date', models.DateTimeField(help_text='Tijd van de laatste SEPA debit verwerking time.', null=True, blank=True)),
            ],
            options={
                'ordering': ('profile',),
                'verbose_name': 'spaardoel profiel',
                'verbose_name_plural': 'spaardoel profielen',
            },
        ),
        migrations.CreateModel(
            name='IndividualProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('nickname', models.CharField(default=b'', max_length=255, blank=True)),
                ('account_holder', models.CharField(default=b'', max_length=255, blank=True)),
                ('iban', localflavor.generic.models.IBANField(max_length=34, null=True, verbose_name='IBAN nummer', blank=True)),
                ('bic_code', models.CharField(blank=True, max_length=11, null=True, verbose_name='BIC code', validators=[icare4u_front.profile.validators.swift_bic_validator])),
            ],
            options={
                'ordering': ('profile',),
                'verbose_name': 'Spaardersprofiel',
                'verbose_name_plural': 'Spaardersprofielen',
            },
        ),
        migrations.CreateModel(
            name='InstitutionProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('account_holder', models.CharField(default=b'', max_length=255, blank=True)),
                ('iban', localflavor.generic.models.IBANField(max_length=34, null=True, verbose_name='IBAN nummer', blank=True)),
                ('bic_code', models.CharField(blank=True, max_length=11, null=True, verbose_name='BIC code', validators=[icare4u_front.profile.validators.swift_bic_validator])),
                ('mandate_id', models.CharField(max_length=35, null=True, verbose_name='Mandaat ID', blank=True)),
                ('signature_date', models.DateField(null=True, verbose_name='Datum handtekening', blank=True)),
                ('latest_payment_date', models.DateTimeField(help_text='Tijd van de laatste SEPA debit verwerking time.', null=True, blank=True)),
                ('vat_number', models.CharField(default=b'', help_text='BTW Nummer', max_length=14, blank=True)),
            ],
            options={
                'ordering': ('profile',),
                'verbose_name': 'instelling profiel',
                'verbose_name_plural': 'instelling profielen',
            },
        ),
        migrations.CreateModel(
            name='SEPAXMLFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file', models.FileField(upload_to=cc3.core.utils.UploadToSecure(b'sepa_xml_files'), max_length=500, editable=False)),
                ('file_date', models.DateField(editable=False)),
                ('file_type', models.CharField(default=b'', max_length=10, editable=False, blank=True, choices=[(b'C', 'Krediet'), (b'D', 'Debit')])),
                ('generated_date', models.DateField(editable=False)),
            ],
            options={
                'ordering': ('generated_date',),
                'verbose_name': 'SEPA XML export',
                'verbose_name_plural': 'SEPA XML bestand',
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('cc3profile_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cyclos.CC3Profile')),
                ('terms_and_conditions', models.BooleanField(default=False, help_text='Bent u het eens met de voorwaarden?')),
                ('tussenvoegsel', models.CharField(default=b'', max_length=10, blank=True)),
                ('extra_address', models.CharField(default=b'', max_length=255, blank=True)),
                ('num_street', models.CharField(default=b'', max_length=50, blank=True)),
                ('gender', models.CharField(default=b'', max_length=1, blank=True, choices=[(b'M', 'Man'), (b'F', 'Vrouw')])),
                ('date_of_birth', models.DateField(help_text='Geboortedatum', null=True, blank=True)),
                ('id_type', models.CharField(default=b'', help_text='Identiteitsbewijs', max_length=1, blank=True, choices=[(b'', b'-------'), (b'P', 'paspoort'), (b'R', 'rijbewijs'), (b'I', 'identiteitskaart'), (b'V', 'vreemdelingendocument')])),
                ('document_number', models.CharField(default=b'', help_text='Documentnummer', max_length=50, blank=True)),
                ('expiration_date', models.DateField(help_text='vervaldatum identiteitsbewijs', null=True, blank=True)),
                ('wants_newsletter', models.BooleanField(default=False)),
            ],
            bases=('cyclos.cc3profile',),
        ),
        migrations.AddField(
            model_name='institutionprofile',
            name='profile',
            field=models.OneToOneField(related_name='institution_profile', null=True, to='profile.UserProfile'),
        ),
        migrations.AddField(
            model_name='individualprofile',
            name='profile',
            field=models.OneToOneField(related_name='individual_profile', null=True, to='profile.UserProfile'),
        ),
        migrations.AddField(
            model_name='charityprofile',
            name='profile',
            field=models.OneToOneField(related_name='charity_profile', null=True, to='profile.UserProfile'),
        ),
        migrations.AddField(
            model_name='businessprofile',
            name='profile',
            field=models.OneToOneField(related_name='business_profile', null=True, to='profile.UserProfile'),
        ),
    ]
