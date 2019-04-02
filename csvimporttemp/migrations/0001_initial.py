# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Huurcontract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('contractnummer', models.CharField(max_length=20)),
                ('vestigingnummer', models.IntegerField()),
                ('vhenummer', models.CharField(default=b'', max_length=20, blank=True)),
                ('persoonsnummer', models.CharField(default=b'', max_length=20, blank=True)),
                ('ingangsdatum', models.DateField(null=True, blank=True)),
                ('einddatum', models.DateField(null=True, blank=True)),
                ('incassowijze', models.CharField(default=b'', max_length=1, blank=True)),
                ('huurprijs', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('huurstand', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('WSNP', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('bedrag_eind_afrekening', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('datum_eind_afrekening', models.DateField(null=True, blank=True)),
                ('parent', models.ForeignKey(related_name='children', blank=True, to='csvimporttemp.Huurcontract', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Positoos',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('vestigingnummer', models.IntegerField()),
                ('persoonsnummer', models.CharField(default=b'', max_length=20, blank=True)),
                ('klantrel_ingdat', models.DateField(null=True, blank=True)),
                ('klantrel_einddat', models.DateField(null=True, blank=True)),
                ('deelname_goudkaart', models.CharField(default=b'', max_length=1, blank=True)),
                ('deelname_positoos', models.CharField(default=b'', max_length=1, blank=True)),
                ('pasnummer', models.CharField(max_length=10)),
                ('betaalregeling', models.CharField(default=b'', max_length=1, blank=True)),
                ('overlastdossier', models.CharField(default=b'', max_length=1, blank=True)),
                ('lid_bew_commissie', models.CharField(default=b'', max_length=1, blank=True)),
                ('lid_klanten_panel', models.CharField(default=b'', max_length=1, blank=True)),
                ('lid_vrijwilligerswerk', models.CharField(default=b'', max_length=1, blank=True)),
                ('correspondentie_wijze', models.CharField(default=b'', max_length=100, blank=True)),
                ('parent', models.ForeignKey(related_name='children', blank=True, to='csvimporttemp.Positoos', null=True)),
            ],
        ),
    ]
