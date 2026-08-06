from django.db import migrations

# Renames the LocalBaserow* models to LocalJadawel*. Each pair differs only by
# that token, so the rename is 1:1 and RenameModel renames the table in place
# rather than dropping and recreating it.


class Migration(migrations.Migration):
    dependencies = [
        ("arabase", "0002_phase_d_widgets"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="LocalBaserowGroupedAggregateRows",
            new_name="LocalJadawelGroupedAggregateRows",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowTableServiceAggregationGroupBy",
            new_name="LocalJadawelTableServiceAggregationGroupBy",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowTableServiceAggregationSeries",
            new_name="LocalJadawelTableServiceAggregationSeries",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowTableServiceAggregationSortBy",
            new_name="LocalJadawelTableServiceAggregationSortBy",
        ),
        migrations.RenameModel(
            old_name="LocalBaserowUpcomingRows",
            new_name="LocalJadawelUpcomingRows",
        ),
    ]
