from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from pathlib import Path
import logging
import os





from .utils.Anime_recomendator import get_recommender, get_status 


logger = logging.getLogger("recomendar")
DATA_DIR = Path(settings.BASE_DIR) / "recomendar" / "utils"

@api_view(["GET"])
def healthz(request):
    return Response({"status": "ok"}, status=200)

@api_view(["GET"])
def recommender_status(request):
    try:
        return Response(get_status(DATA_DIR, 10), status=200)
    except Exception as e:
        return Response({"ready": False, "error": str(e)}, status=500)

@api_view(["GET"])
def getrecomenders(request):
    q = request.query_params.get("q", "")
    topk = int(request.query_params.get("topk", 10))
    df = rec.similares_por_titulo(q, topk=topk, order="name")
    payload = df.to_dict(orient="records")
    if not q.strip():
        return Response({"error": "Parámetro 'q' requerido."}, status=status.HTTP_400_BAD_REQUEST)
    logger.info("GET /getrecomenders q='%s' topk=%s", q, topk)
    try:
        rec = get_recommender(DATA_DIR, min_periods=10)
        df = rec.similares_por_titulo(q, topk=topk)
        return Response(df.to_dict(orient="records"), status=200)
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
    ratings_map = {}
    
    df = rec.recomendar_por_vistos(
    seen_ids=seen_ids,
    seen_names=seen_names,
    ratings_map=ratings_map or None,
    default_rating=default_rating,
    topk=topk,
    order="name",
    )
    payload = df.to_dict(orient="records")
    for k, v in ratings_map_raw.items():
        try: ratings_map[int(k)] = float(v)
        except Exception: pass
    if not seen_names and not seen_ids:
        return Response({"error": "Debes enviar 'seen_names' o 'seen_ids'."}, status=400)
    logger.info("POST /recommend_by_seen seen_names=%d seen_ids=%d topk=%d", len(seen_names), len(seen_ids), topk)
    try:
        rec = get_recommender(DATA_DIR, min_periods=10)
        df = rec.recomendar_por_vistos(seen_ids=seen_ids, seen_names=seen_names,
                                       ratings_map=ratings_map or None,
                                       default_rating=default_rating, topk=topk)
        return Response(df.to_dict(orient="records"), status=200)
    except Exception as e:
        logger.exception("recommend_by_seen ERROR: %s", e)
        return Response({"error": str(e)}, status=400)


DATA_DIR = Path(settings.BASE_DIR) / "recomendar" / "utils"

@api_view(["GET"])
def healthz(request):
    return Response({"status": "ok"}, status=200)

@api_view(["GET"])
def recommender_status(request):
    # listo si el pivot ya está cargado
    return Response(get_status(DATA_DIR), status=200)

@api_view(["GET"])
def list_titles(request):
    """
    GET /anime/titles?q=nar&limit=200
    Devuelve [{anime_id, name}], ordenado por nombre.
    """
    q = (request.query_params.get("q") or "").strip().lower()
    try:
        limit = int(request.query_params.get("limit", 200))
    except Exception:
        limit = 200

    rec = get_recommender(DATA_DIR, min_periods=int(os.environ.get("DJ_MIN_PERIODS", "3")))
    df = rec.anime[["anime_id", "name"]].copy()
    if q:
        # búsqueda contains sobre nombre normalizado
        mask = rec.anime["name_norm"].str.contains(q, na=False)
        df = rec.anime.loc[mask, ["anime_id", "name"]]

    df = df.sort_values("name", kind="stable").head(limit)
    return Response(df.to_dict(orient="records"), status=200)