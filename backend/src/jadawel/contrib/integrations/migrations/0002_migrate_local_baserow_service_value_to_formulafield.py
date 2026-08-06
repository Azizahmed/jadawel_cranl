import django.db.models.manager
from django.db import migrations

import jadawel.contrib.integrations.local_jadawel.models
import jadawel.core.formula.field


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0001_squashed_0011_initial"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="localbaserowtableservicefilter",
            managers=[
                ("objects_and_trash", django.db.models.manager.Manager()),
                (
                    "objects",
                    jadawel.contrib.integrations.local_jadawel.models.LocalJadawelTableServiceRefinementManager(),
                ),
            ],
        ),
        migrations.AlterModelManagers(
            name="localbaserowtableservicesort",
            managers=[
                ("objects_and_trash", django.db.models.manager.Manager()),
                (
                    "objects",
                    jadawel.contrib.integrations.local_jadawel.models.LocalJadawelTableServiceRefinementManager(),
                ),
            ],
        ),
        migrations.AlterField(
            model_name="localbaserowtableservicefilter",
            name="value",
            field=jadawel.core.formula.field.FormulaField(
                blank=True,
                default="",
                help_text="The filter value that must be compared to the field's value.",
            ),
        ),
    ]
