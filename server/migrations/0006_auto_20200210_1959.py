# Generated by Django 2.2.10 on 2020-02-10 19:59

import cjwstate.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("server", "0005_auto_20200205_1736")]

    operations = [
        migrations.AddField(
            model_name="wfmodule",
            name="fetch_errors",
            field=cjwstate.models.fields.RenderErrorsField(default=list, null=True),
        ),
        migrations.AlterField(
            model_name="wfmodule",
            name="fetch_error",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=10000,
                null=True,
                verbose_name="fetch_error",
            ),
        ),
    ]
