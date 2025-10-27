from django.apps import AppConfig
import os

class RecomendarConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recomendar"

    def ready(self):
        if os.environ.get("DISABLE_WARMUP", "1") == "1":
            return
