# Generated by Django 2.2.9 on 2020-01-31 20:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("server", "0002_auto_20191216_1735")]

    operations = [
        migrations.AlterField(
            model_name="uploadedfile",
            name="bucket",
            field=models.CharField(blank=True, default="", max_length=255),
        )
    ]
