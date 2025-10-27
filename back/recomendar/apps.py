# recomendar/apps.py
from django.apps import AppConfig
from pathlib import Path
from django.conf import settings
import logging, time

logger = logging.getLogger("recomendar")
_WARMED_UP = False

class RecomendarConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recomendar"

    def ready(self):
        global _WARMED_UP
        if _WARMED_UP:
            return
        try:
            from .utils.recommender import get_recommender
            base_dir = Path(settings.BASE_DIR) / "recomendar" / "utils"
            t0 = time.time()
            logger.info("WARMUP start: building item-item correlation…")
            get_recommender(base_dir=base_dir, min_periods=10)
            logger.info("WARMUP done in %.2fs", time.time() - t0)
            _WARMED_UP = True
        except Exception as e:
            logger.exception("WARMUP FAILED: %s", e)
