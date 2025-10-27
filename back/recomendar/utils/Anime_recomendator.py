import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class ItemBasedRecommender:
    """
    Carga los CSV, construye matriz usuario-item y correlación item-item (Pearson).
    Ofrece:
      - similares_por_titulo(titulo, topk)
      - recomendar_por_vistos(seen_ids, ratings_map, topk)
    """

    def __init__(self, base_dir: Path, min_periods: int = 10):
        self.base_dir = Path(base_dir)
        self.min_periods = min_periods

        # --- carga de datos ---
        a_cols = ["anime_id", "name"]  # usaremos name; si luego quieres género añade "genre"
        self.anime = pd.read_csv(self.base_dir / "anime.csv", usecols=a_cols)
        self.anime["name_norm"] = self.anime["name"].str.strip().str.lower()

        self.ratings = pd.read_csv(self.base_dir / "ratings_clean_1.csv")
        # quitamos -1 por si acaso (aunque ya vienen limpios)
        self.ratings = self.ratings[self.ratings["rating"] != -1].copy()

        # --- pivot usuario x item ---
        ui = self.ratings.pivot_table(
            index="user_id", columns="anime_id", values="rating", aggfunc="mean"
        )

        # --- correlación item-item (Pearson) ---
        self.corr = ui.corr(method="pearson", min_periods=self.min_periods)

        # mapas útiles
        self.id_to_name = dict(zip(self.anime["anime_id"], self.anime["name"]))
        self.name_to_id = (
            self.anime.drop_duplicates("name_norm")
            .set_index("name_norm")["anime_id"]
            .to_dict()
        )

    # ------------------- helpers -------------------
    def _find_anime_id_by_title(self, title: str) -> Optional[int]:
        t = title.strip().lower()
        # exacto
        if t in self.name_to_id:
            return int(self.name_to_id[t])
        # contiene
        candidates = self.anime[self.anime["name_norm"].str.contains(t, na=False)]
        if not candidates.empty:
            return int(candidates.iloc[0]["anime_id"])
        return None

    def _ensure_ids(self, seen_ids: Optional[List[int]] = None,
                    seen_names: Optional[List[str]] = None) -> List[int]:
        ids: List[int] = []
        if seen_ids:
            ids.extend([int(x) for x in seen_ids])
        if seen_names:
            for n in seen_names:
                aid = self._find_anime_id_by_title(n)
                if aid is not None:
                    ids.append(aid)
        # filtra solo los que existen en la matriz de correlación
        existing = [aid for aid in ids if aid in self.corr.columns]
        return list(dict.fromkeys(existing))  # únicos, preserva orden

    # ------------------- API -------------------
    def similares_por_titulo(self, title: str, topk: int = 10) -> pd.DataFrame:
        aid = self._find_anime_id_by_title(title)
        if aid is None:
            raise ValueError(f"No encontré el animé '{title}' en anime.csv")
        if aid not in self.corr.columns:
            raise ValueError(f"'{self.id_to_name.get(aid, aid)}' no aparece en la matriz (muy pocos datos).")

        sims = self.corr[aid].dropna().sort_values(ascending=False)
        sims = sims.drop(index=aid, errors="ignore")
        sims = sims.head(topk)

        out = (
            pd.DataFrame({"anime_id": sims.index.astype(int), "correlation": sims.values})
            .assign(name=lambda d: d["anime_id"].map(self.id_to_name))
            .loc[:, ["anime_id", "name", "correlation"]]
        )
        return out

    def recomendar_por_vistos(
        self,
        seen_ids: Optional[List[int]] = None,
        seen_names: Optional[List[str]] = None,
        ratings_map: Optional[Dict[int, float]] = None,
        default_rating: float = 10.0,
        topk: int = 10,
    ) -> pd.DataFrame:
        """
        Agrega similitudes ponderadas por la nota del usuario:
            score = sum_j (corr(item, seen_j) * rating_j)
        """
        items = self._ensure_ids(seen_ids=seen_ids, seen_names=seen_names)
        if not items:
            raise ValueError("No se encontraron animes válidos en la selección.")

        # Serie de candidatos
        sim_candidates = pd.Series(dtype=float)
        for aid in items:
            if aid not in self.corr.columns:
                continue
            sims = self.corr[aid].dropna()
            r = float(ratings_map.get(aid, default_rating)) if ratings_map else default_rating
            sims = sims * r
            sim_candidates = pd.concat([sim_candidates, sims])

        if sim_candidates.empty:
            return pd.DataFrame(columns=["anime_id", "name", "correlation"])

        sim_candidates = sim_candidates.groupby(sim_candidates.index).sum()

        # excluye vistos
        for aid in items:
            if aid in sim_candidates.index:
                sim_candidates = sim_candidates.drop(index=aid)

        sim_candidates = sim_candidates.sort_values(ascending=False).head(topk)

        out = (
            pd.DataFrame({"anime_id": sim_candidates.index.astype(int), "correlation": sim_candidates.values})
            .assign(name=lambda d: d["anime_id"].map(self.id_to_name))
            .loc[:, ["anime_id", "name", "correlation"]]
        )
        return out


# ---- singleton perezoso (para no recalcular en cada request) ----
_recommender_singleton: Optional[ItemBasedRecommender] = None

def get_recommender(base_dir: Path, min_periods: int = 10) -> ItemBasedRecommender:
    global _recommender_singleton
    if _recommender_singleton is None:
        _recommender_singleton = ItemBasedRecommender(base_dir=base_dir, min_periods=min_periods)
    return _recommender_singleton
