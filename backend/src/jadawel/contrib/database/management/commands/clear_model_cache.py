from django.core.management import BaseCommand

from jadawel.contrib.database.table.cache import clear_generated_model_cache


class Command(BaseCommand):
    help = "Clears Jadawel's internal generated model cache"

    def handle(self, *args, **options):
        clear_generated_model_cache()
