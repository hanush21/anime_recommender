from pathlib import Path
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils.recommender_light import get_recommender

DATA_DIR = Path(settings.BASE_DIR) / "recomendar" / "utils"


@api_view(["GET"])
def healthz(_request):
    return Response({"status": "ok"}, status=200)


@api_view(["GET"])
def getrecomenders(request):
    """
    GET /getrecomenders?q=<titulo|fragmento>&topk=10&minp=3
    Respuesta: [{ anime_id, name, correlation }]
    - Si no hay match exacto, toma el mejor por substring (popularidad por 'members').
    """
    q = request.query_params.get("q", "")
    topk = int(request.query_params.get("topk", 10))
    minp = int(request.query_params.get("minp", 3))

    if not q.strip():
        return Response({"error": "Parámetro 'q' requerido."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        rec = get_recommender(DATA_DIR, min_periods=minp)
        df = rec.similares_por_titulo(q, topk=topk)
        payload = df[["anime_id", "name", "correlation"]].to_dict(orient="records")
        return Response(payload, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["GET"])
def suggest_titles(request):
    """
    GET /titles?s=<fragmento>&limit=50
    Respuesta: [{ anime_id, name, members }]
    - Para autocompletar en el front.
    """
    s = request.query_params.get("s", "")
    limit = int(request.query_params.get("limit", 50))
    minp = int(request.query_params.get("minp", 3))  # por si quieres un único objeto y llamar similares

    try:
        rec = get_recommender(DATA_DIR, min_periods=minp)
        df = rec.suggest_titles(s, limit=limit)
        payload = df.to_dict(orient="records")
        return Response(payload, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["POST"])
def recommend_by_seen(request):
    data = request.data if isinstance(request.data, dict) else {}
    seen_names = data.get("seen_names") or []
    seen_ids = data.get("seen_ids") or []
    ratings_map = data.get("ratings") or {}
    default_rating = float(data.get("rating", 10.0))
    topk = int(data.get("topk", 10))
    minp = int(data.get("minp", 3))

    if not seen_names and not seen_ids:
        return Response({"error": "Debes enviar 'seen_names' o 'seen_ids'."}, status=400)

    try:
        rec = get_recommender(DATA_DIR, min_periods=minp)
        df = rec.recomendar_por_vistos(
            seen_ids=seen_ids,
            seen_names=seen_names,
            ratings_map=ratings_map or None,
            default_rating=default_rating,
            topk=topk,
        )
        payload = df[["anime_id", "name", "score"]].to_dict(orient="records")
        return Response(payload, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
