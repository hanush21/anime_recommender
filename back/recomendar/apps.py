# back/recomendar/apps.py
from django.apps import AppConfig
from django.conf import settings
from pathlib import Path
import logging, os, time

logger = logging.getLogger("recomendar")
_WARMED_UP = False

class RecomendarConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recomendar"

    def ready(self):
        global _WARMED_UP
        # evita doble ejecución del autoreloader
        if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
            return
        if _WARMED_UP:
            return
        try:
            from .utils.Anime_recomendator import get_recommender
            base_dir = Path(settings.BASE_DIR) / "recomendar" / "utils"
            minp = int(os.environ.get("DJ_MIN_PERIODS", "3"))
            t0 = time.time()
            logger.info("WARMUP start (min_periods=%s): building or loading cache…", minp)
            get_recommender(base_dir=base_dir, min_periods=minp)
            logger.info("WARMUP done in %.2fs", time.time() - t0)
            _WARMED_UP = True
        except Exception as e:
            logger.exception("WARMUP FAILED: %s", e)
