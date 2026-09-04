import importlib.util
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Seed demo data for ElectroMart MongoDB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep existing data instead of clearing seeded collections",
        )

    def handle(self, *args, **options):
        # Backend/ -> ElectroMart/ -> Database/seed_data.py
        project_root = Path(settings.BASE_DIR).parent
        seed_file = project_root / "Database" / "seed_data.py"

        if not seed_file.exists():
            raise CommandError(
                f"Cannot find seed file: {seed_file}"
            )

        spec = importlib.util.spec_from_file_location(
            "electromart_seed_data",
            seed_file,
        )

        if spec is None or spec.loader is None:
            raise CommandError(
                "Cannot load Database/seed_data.py"
            )

        seed_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(seed_module)

        if not hasattr(seed_module, "seed"):
            raise CommandError(
                "Database/seed_data.py does not contain seed()"
            )

        self.stdout.write(
            self.style.WARNING("Starting ElectroMart seed data...")
        )

        seed_module.seed(
            keep=options["keep"]
        )

        self.stdout.write(
            self.style.SUCCESS(
                "ElectroMart seed data completed successfully."
            )
        )