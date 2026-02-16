"""Rename job mode 'quick' -> 'default'."""

from django.db import migrations, models


def rename_quick_to_default(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    Job.objects.filter(mode="quick").update(mode="default")


def rename_default_to_quick(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    Job.objects.filter(mode="default").update(mode="quick")


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(rename_quick_to_default, rename_default_to_quick),
        migrations.AlterField(
            model_name="job",
            name="mode",
            field=models.CharField(
                choices=[("default", "default"), ("detailed", "detailed")],
                default="default",
                max_length=10,
            ),
        ),
    ]
