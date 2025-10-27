from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import time

class Command(BaseCommand):
    help = "Warm up the recommender (load pivot/etc) before starting the server."

    def add_arguments(self, parser):
        parser.add_argument("--min-periods", type=int, default=3)

    def handle(self, *args, **options):
        from recomendar.utils.Anime_recomendator import get_recommender, get_status

        base_dir = Path(settings.BASE_DIR) / "recomendar" / "utils"
        minp = options["min_periods"]
        t0 = time.time()
        self.stdout.write(self.style.WARNING(f"[warmup] starting (min_periods={minp})…"))
        rec = get_recommender(base_dir=base_dir, min_periods=minp)
        status = rec.status() if hasattr(rec, "status") else get_status(base_dir, minp)
        dt = time.time() - t0
        self.stdout.write(self.style.SUCCESS(f"[warmup] done in {dt:.2f}s → {status}"))
