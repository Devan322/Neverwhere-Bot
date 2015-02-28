# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Neverwherebot', '0013_auto_20150228_1413'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemtype',
            name='skill',
            field=models.ForeignKey(blank=True, to='Neverwherebot.Skill', null=True),
            preserve_default=True,
        ),
    ]
