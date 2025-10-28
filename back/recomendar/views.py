from pathlib import Path
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils.recommender import get_recommender

DATA_DIR = Path(settings.BASE_DIR) / "recomendar" / "utils"


@api_view(["GET"])
def healthz(_request):
    return Response({"status": "ok"}, status=200)


@api_view(["GET"])
def getrecomenders(request):
    """
    GET /getrecomenders?q=<titulo|fragmento>&topk=10&minp=3
    Respuesta: [{ anime_id, name, correlation, genre, episodes }]
    Si no hay match exacto, toma el mejor por substring (popularidad por 'members').
    """
    q = request.query_params.get("q", "")
    topk = int(request.query_params.get("topk", 10))
    minp = int(request.query_params.get("minp", 3))

    if not q.strip():
        return Response({"error": "Parámetro 'q' requerido."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        rec = get_recommender(DATA_DIR, min_periods=minp)
        df = rec.similares_por_titulo(q, topk=topk)
        payload = df[["anime_id", "name", "correlation", "genre", "episodes"]].to_dict(orient="records")
        return Response(payload, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["GET"])
def titles(request):
    s = request.query_params.get("s", "").strip()
    limit = max(1, min(int(request.query_params.get("limit", 50)), 500))
    offset = max(0, int(request.query_params.get("offset", 0)))
    minp = int(request.query_params.get("minp", 3))
    min_r = int(request.query_params.get("min_r", 0))

    try:
        rec = get_recommender(DATA_DIR, min_periods=minp)

        # Base: anime
        base = rec.anime.copy()

        # rating_count si hay ratings; si no, lo omitimos sin romper el listado
        rating_counts = None
        if getattr(rec, "ratings", None) is not None and len(rec.ratings) > 0:
            rating_counts = (
                rec.ratings.groupby("anime_id")["rating"]
                .count()
                .rename("rating_count")
                .astype("int32")
                .reset_index()
            )
            base = base.merge(rating_counts, on="anime_id", how="left")
            base["rating_count"] = base["rating_count"].fillna(0).astype("int32")
        else:
            base["rating_count"] = 0  # fallback neutral

        # Filtro por min_r solo si realmente tenemos conteo útil
        if min_r > 0 and rating_counts is not None:
            base = base.loc[base["rating_count"] >= min_r]

        # AUTOCOMPLETE (cuando hay 's')
        if s:
            # aseguramos name_norm
            if "name_norm" not in base.columns:
                base["name_norm"] = base["name"].str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii").str.lower()
            mask = base["name_norm"].str.contains(s.lower(), na=False)
            sub = base.loc[mask, ["anime_id", "name", "members", "rating_count", "genre", "episodes"]]
            sub = sub.sort_values(["members", "name"], ascending=[False, True])
            total = int(sub.shape[0])
            results = sub.head(limit).to_dict(orient="records")
            return Response({"count": total, "results": results}, status=200)

        # LISTADO ALFABÉTICO (sin 's')
        sub = base.loc[:, ["anime_id", "name", "members", "rating_count", "genre", "episodes"]]
        sub = sub.sort_values("name", ascending=True)
        total = int(sub.shape[0])

        if offset >= total:
            page = sub.iloc[0:0]
        else:
            page = sub.iloc[offset: offset + limit]

        results = page.to_dict(orient="records")
        return Response({"count": total, "results": results}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


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
      - minp:       int
    Respuesta: [{ anime_id, name, score, genre, episodes }]
    """
    data = request.data if isinstance(request.data, dict) else {}
    seen_names = data.get("seen_names") or []
    seen_ids = data.get("seen_ids") or []
    ratings_map = data.get("ratings") or {}
    default_rating = float(data.get("rating", 10.0))
    topk = int(data.get("topk", 10))
    minp = int(request.query_params.get("minp", data.get("minp", 3)))

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
        payload = df[["anime_id", "name", "score", "genre", "episodes"]].to_dict(orient="records")
        return Response(payload, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
