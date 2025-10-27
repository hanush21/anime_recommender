# back/recomendar/apps.py
from django.apps import AppConfig
from django.conf import settings
from pathlib import Path
import logging
import os
import time

logger = logging.getLogger("recomendar")
_WARMED_UP = False  # evita recalcular si ya se hizo

class RecomendarConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recomendar"

    def ready(self):
        """
        Construye/carga el motor de recomendaciones al iniciar el servidor.
        Se ejecuta una sola vez gracias a los guards de RUN_MAIN y _WARMED_UP.
        """
        global _WARMED_UP

        # Evita la primera pasada del autoreloader en DEBUG
        if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
            return

        if _WARMED_UP:
            return

        try:
            # Import relativo a tu archivo actual: Anime_recomendator.py
            from .utils.Anime_recomendator import get_recommender

            base_dir = Path(settings.BASE_DIR) / "recomendar" / "utils"
            t0 = time.time()
            logger.info("WARMUP start: building or loading item-item correlation…")
            get_recommender(base_dir=base_dir, min_periods=10)
            logger.info("WARMUP done in %.2fs", time.time() - t0)

            _WARMED_UP = True
        except Exception as e:
            logger.exception("WARMUP FAILED: %s", e)
