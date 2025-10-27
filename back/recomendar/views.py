from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from pathlib import Path
from .utils.Anime_recomendator import get_recommender

DATA_DIR = Path(settings.BASE_DIR) / "recomendar" / "utils"

@api_view(["GET"])
def getrecomenders(request):
    """
    GET /getrecomenders?q=<titulo>&topk=10
    Devuelve: [{ anime_id, name, correlation }, ...]
    """
    q = request.query_params.get("q", "")
    topk = int(request.query_params.get("topk", 10))

    if not q.strip():
        return Response({"error": "Parámetro 'q' requerido."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        rec = get_recommender(DATA_DIR, min_periods=10)
        df = rec.similares_por_titulo(q, topk=topk)
        payload = df.to_dict(orient="records")
        # Si solo quieres name + correlation:
        # payload = [{"name": r["name"], "correlation": r["correlation"]} for r in payload]
        return Response(payload, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def recommend_by_seen(request):
    """
    POST /recommend_by_seen
    Body:
      - seen_names: [str] (opcional)
      - seen_ids:   [int] (opcional)
      - ratings:    { "<anime_id>": float } (opcional)
      - rating:     float  (rating por defecto si no pasas 'ratings')
      - topk:       int
    """
    data = request.data if isinstance(request.data, dict) else {}
    seen_names = data.get("seen_names") or []
    seen_ids = data.get("seen_ids") or []
    ratings_map_raw = data.get("ratings") or {}
    default_rating = float(data.get("rating", 10.0))
    topk = int(data.get("topk", 10))

    # normaliza ratings_map a claves int
    ratings_map = {}
    for k, v in ratings_map_raw.items():
        try:
            ratings_map[int(k)] = float(v)
        except Exception:
            continue

    if not seen_names and not seen_ids:
        return Response({"error": "Debes enviar 'seen_names' o 'seen_ids'."}, status=status.HTTP_400_BAD_REQUEST)

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
        # Si solo quieres name + correlation:
        # payload = [{"name": r["name"], "correlation": r["correlation"]} for r in payload]
        return Response(payload, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
