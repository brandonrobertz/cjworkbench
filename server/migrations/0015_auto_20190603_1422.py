# Generated by Django 2.2.2 on 2019-06-03 14:22

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("server", "0014_nix_upload_stored_objects")]

    operations = [
        migrations.AlterModelOptions(
            name="addmodulecommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="addtabcommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="changedataversioncommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="changeparameterscommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="changewfmodulenotescommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="changeworkflowtitlecommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="deletemodulecommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="deletetabcommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="delta", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="duplicatetabcommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="initworkflowcommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="reordermodulescommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="reordertabscommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterModelOptions(
            name="settabnamecommand", options={"base_manager_name": "objects"}
        ),
        migrations.AlterField(
            model_name="wfmodule",
            name="params",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="wfmodule",
            name="secrets",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
    ]
