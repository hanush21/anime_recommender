# back/recomendar/utils/Anime_recomendator.py
import os, time, json, re
from pathlib import Path
from typing import Optional, List, Dict
import pandas as pd
from datetime import datetime, timezone

_singleton = None

def _norm(s: str) -> str:
    s = str(s).lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

class ItemBasedRecommender:
    """
    Construye SOLO la tabla usuario-item (pivot) en memoria (float32),
    y usa pandas.corrwith para calcular similitudes BAJO DEMANDA.
    Evita OOM al no crear la matriz completa item×item.
    """
    def __init__(self, data_dir: Path, min_periods: int = 3):
        t0 = time.time()
        self.data_dir = Path(data_dir)
        self.min_periods = int(min_periods)

        # Carga anime
        a_cols = ["anime_id", "name"]
        self.anime = pd.read_csv(self.data_dir / "anime.csv", usecols=a_cols)
        self.anime["name_norm"] = self.anime["name"].map(_norm)
        self.id_to_name = dict(zip(self.anime["anime_id"], self.anime["name"]))
        self.name_to_id = (
            self.anime.drop_duplicates("name_norm").set_index("name_norm")["anime_id"].to_dict()
        )

        # Carga ratings y construye pivot (downcast para ahorrar RAM)
        ratings = pd.read_csv(self.data_dir / "ratings_clean_1.csv", usecols=["user_id","anime_id","rating"])
        ratings = ratings[ratings["rating"] != -1].copy()
        ratings["user_id"] = ratings["user_id"].astype("int32")
        ratings["anime_id"] = ratings["anime_id"].astype("int32")
        ratings["rating"] = ratings["rating"].astype("float32")

        ui = ratings.pivot_table(index="user_id", columns="anime_id", values="rating", aggfunc="mean")
        self.ui = ui.astype("float32")  # reduce memoria

        self.built_at = datetime.now(timezone.utc).isoformat()
        self.build_seconds = round(time.time() - t0, 3)
        self.shape_ui = tuple(self.ui.shape)

    def _find_id(self, title: str) -> Optional[int]:
        t = _norm(title)
        if t in self.name_to_id:
            return int(self.name_to_id[t])
        m = self.anime[self.anime["name_norm"].str.contains(t, na=False)]
        return int(m.iloc[0]["anime_id"]) if not m.empty else None

    def _sim_series(self, aid: int) -> pd.Series:
        # correlación item–item por columna con corrwith (min_periods)
        if aid not in self.ui.columns:
            return pd.Series(dtype="float32")
        target = self.ui[aid]
        sims = self.ui.corrwith(target, axis=0, method="pearson", drop=False)
        return sims.astype("float32")

    def similares_por_titulo(self, title: str, topk: int = 10) -> pd.DataFrame:
        aid = self._find_id(title)
        if aid is None:
            raise ValueError(f"No encontré '{title}'")
        sims = self._sim_series(aid).dropna()
        # filtra por min_periods con conteo de co-valoraciones
        common = (~self.ui[aid].isna() & ~self.ui.isna()).sum(axis=0)
        sims = sims[common >= self.min_periods]
        sims = sims.drop(index=aid, errors="ignore").sort_values(ascending=False).head(topk)

        out = pd.DataFrame({"anime_id": sims.index.astype("int32"), "correlation": sims.values.astype("float32")})
        out["name"] = out["anime_id"].map(self.id_to_name)
        return out[["anime_id","name","correlation"]]

    def recomendar_por_vistos(
        self,
        seen_ids: Optional[List[int]] = None,
        seen_names: Optional[List[str]] = None,
        ratings_map: Optional[Dict[int, float]] = None,
        default_rating: float = 10.0,
        topk: int = 10,
    ) -> pd.DataFrame:
        items: List[int] = []
        if seen_names:
            for n in seen_names:
                aid = self._find_id(n)
                if aid is not None:
                    items.append(aid)
        if seen_ids:
            items.extend(seen_ids)
        items = [i for i in dict.fromkeys(items) if i in self.ui.columns]
        if not items:
            return pd.DataFrame(columns=["anime_id","name","correlation"])

        acc = None
        counts = None
        for aid in items:
            sims = self._sim_series(aid)
            c = (~self.ui[aid].isna() & ~self.ui.isna()).sum(axis=0)
            mask = c >= self.min_periods
            sims = sims.where(mask)
            weight = float(ratings_map.get(aid, default_rating)) if ratings_map else default_rating
            sims = sims * weight
            if acc is None:
                acc = sims
                counts = mask.astype("int32")
            else:
                acc = acc.add(sims, fill_value=0.0)
                counts = counts.add(mask.astype("int32"), fill_value=0)
        # quita los propios vistos y ordena
        for aid in items:
            if acc is not None and aid in acc.index:
                acc.loc[aid] = float("nan")
        acc = acc.dropna().sort_values(ascending=False).head(topk)

        out = pd.DataFrame({"anime_id": acc.index.astype("int32"), "correlation": acc.values.astype("float32")})
        out["name"] = out["anime_id"].map(self.id_to_name)
        return out[["anime_id","name","correlation"]]

    def status(self) -> dict:
        return {
            "ready": True,
            "ui_shape": self.shape_ui,
            "min_periods": self.min_periods,
            "built_at": self.built_at,
            "build_seconds": self.build_seconds,
        }

def get_recommender(base_dir: Path, min_periods: int = 3) -> ItemBasedRecommender:
    global _singleton
    if _singleton is None:
        _singleton = ItemBasedRecommender(base_dir, min_periods)
    return _singleton

def get_status(base_dir: Path, min_periods: int = 3) -> dict:
    return get_recommender(base_dir, min_periods).status()
