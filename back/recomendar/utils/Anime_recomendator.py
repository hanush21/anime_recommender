import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict
import time
from datetime import datetime, timezone

class ItemBasedRecommender:
    def __init__(self, base_dir: Path, min_periods: int = 10):
        t0 = time.time()

        a_cols = ["anime_id", "name"]
        self.anime = pd.read_csv(base_dir / "anime.csv", usecols=a_cols)
        self.anime["name_norm"] = self.anime["name"].str.strip().str.lower()

        ratings = pd.read_csv(base_dir / "ratings_clean_1.csv")
        ratings = ratings[ratings["rating"] != -1].copy()

        ui = ratings.pivot_table(index="user_id", columns="anime_id", values="rating", aggfunc="mean")
        self.corr = ui.corr(method="pearson", min_periods=min_periods)

        self.id_to_name = dict(zip(self.anime["anime_id"], self.anime["name"]))
        self.name_to_id = (
            self.anime.drop_duplicates("name_norm").set_index("name_norm")["anime_id"].to_dict()
        )

        self.min_periods = min_periods
        self.built_at = datetime.now(timezone.utc).isoformat()
        self.build_seconds = round(time.time() - t0, 3)

    def _find_id(self, title: str) -> Optional[int]:
        t = title.strip().lower()
        if t in self.name_to_id:
            return int(self.name_to_id[t])
        m = self.anime[self.anime["name_norm"].str.contains(t, na=False)]
        return int(m.iloc[0]["anime_id"]) if not m.empty else None

    def similares_por_titulo(self, title: str, topk: int = 10) -> pd.DataFrame:
        aid = self._find_id(title)
        if aid is None or aid not in self.corr.columns:
            raise ValueError(f"No encontré '{title}' o no tiene correlaciones suficientes.")
        sims = self.corr[aid].dropna().sort_values(ascending=False).drop(index=aid, errors="ignore").head(topk)
        out = pd.DataFrame({"anime_id": sims.index.astype(int), "correlation": sims.values})
        out["name"] = out["anime_id"].map(self.id_to_name)
        return out[["anime_id", "name", "correlation"]]

    def recomendar_por_vistos(
        self,
        seen_ids: Optional[List[int]] = None,
        seen_names: Optional[List[str]] = None,
        ratings_map: Optional[Dict[int, float]] = None,
        default_rating: float = 10.0,
        topk: int = 10,
    ) -> pd.DataFrame:
        items: List[int] = []
        if seen_ids:
            items += [i for i in seen_ids if i in self.corr.columns]
        if seen_names:
            for n in seen_names:
                aid = self._find_id(n)
                if aid is not None and aid in self.corr.columns:
                    items.append(aid)
        items = list(dict.fromkeys(items))
        if not items:
            return pd.DataFrame(columns=["anime_id", "name", "correlation"])

        cand = pd.Series(dtype=float)
        for aid in items:
            sims = self.corr[aid].dropna()
            r = float(ratings_map.get(aid, default_rating)) if ratings_map else default_rating
            cand = pd.concat([cand, sims * r])
        cand = cand.groupby(cand.index).sum().drop(index=items, errors="ignore").sort_values(ascending=False).head(topk)

        out = pd.DataFrame({"anime_id": cand.index.astype(int), "correlation": cand.values})
        out["name"] = out["anime_id"].map(self.id_to_name)
        return out[["anime_id", "name", "correlation"]]

    def status(self) -> dict:
        return {
            "ready": True,
            "built_at": self.built_at,
            "build_seconds": self.build_seconds,
            "corr_shape": tuple(self.corr.shape),
            "min_periods": self.min_periods,
        }

# --- singleton ---
_singleton: Optional[ItemBasedRecommender] = None

def get_recommender(base_dir: Path, min_periods: int = 10) -> ItemBasedRecommender:
    global _singleton
    if _singleton is None:
        _singleton = ItemBasedRecommender(base_dir, min_periods)
    return _singleton

def get_status(base_dir: Path, min_periods: int = 10) -> dict:
    return get_recommender(base_dir, min_periods).status()
