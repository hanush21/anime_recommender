from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from pathlib import Path
import logging

from .utils.recommender import get_recommender, get_status  # <— importa del módulo correcto

logger = logging.getLogger("recomendar")
DATA_DIR = Path(settings.BASE_DIR) / "recomendar" / "utils"

@api_view(["GET"])
def healthz(request):
    return Response({"status": "ok"}, status=200)

@api_view(["GET"])
def recommender_status(request):
    try:
        data = get_status(DATA_DIR, 10)
        return Response(data, status=200)
    except Exception as e:
        return Response({"ready": False, "error": str(e)}, status=500)

@api_view(["GET"])
def getrecomenders(request):
    q = request.query_params.get("q", "")
    topk = int(request.query_params.get("topk", 10))
    if not q.strip():
        return Response({"error": "Parámetro 'q' requerido."}, status=status.HTTP_400_BAD_REQUEST)
    logger.info("GET /getrecomenders q='%s' topk=%s", q, topk)
    try:
        rec = get_recommender(DATA_DIR, min_periods=10)
        df = rec.similares_por_titulo(q, topk=topk)
        payload = df.to_dict(orient="records")
        logger.info("getrecomenders -> %d resultados", len(payload))
        return Response(payload, status=200)
    except Exception as e:
        logger.exception("getrecomenders ERROR: %s", e)
        return Response({"error": str(e)}, status=400)

@api_view(["POST"])
def recommend_by_seen(request):
    data = request.data if isinstance(request.data, dict) else {}
    seen_names = data.get("seen_names") or []
    seen_ids = data.get("seen_ids") or []
    ratings_map_raw = data.get("ratings") or {}
    default_rating = float(data.get("rating", 10.0))
    topk = int(data.get("topk", 10))

    logger.info("POST /recommend_by_seen seen_names=%d seen_ids=%d topk=%d",
                len(seen_names), len(seen_ids), topk)

    # normaliza ratings_map
    ratings_map = {}
    for k, v in ratings_map_raw.items():
        try:
            ratings_map[int(k)] = float(v)
        except Exception:
            continue

    if not seen_names and not seen_ids:
        return Response({"error": "Debes enviar 'seen_names' o 'seen_ids'."}, status=400)

    try:
        rec = get_recommender(DATA_DIR, min_periods=10)
        df = rec.recomendar_por_vistos(
            seen_ids=seen_ids,
            seen_names=seen_names,
            ratings_map=ratings_map or None,
            default_rating=default_rating,
            topk=topk,
        )
        payload = df.to_dict(orient="records")
        logger.info("recommend_by_seen -> %d resultados", len(payload))
        return Response(payload, status=200)
    except Exception as e:
        logger.exception("recommend_by_seen ERROR: %s", e)
        return Response({"error": str(e)}, status=400)
