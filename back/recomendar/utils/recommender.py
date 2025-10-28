from __future__ import annotations
from pathlib import Path
from functools import lru_cache
import pandas as pd
import numpy as np
from typing import List, Dict, Optional

class LightRecommender:
    def __init__(self, data_dir: Path, min_periods: int = 3):
        self.data_dir = Path(data_dir)
        self.min_periods = int(min_periods)

        self.anime = pd.read_csv(self.data_dir / "anime.csv",
                                 usecols=["anime_id","name","members","genre","episodes"])  # Añadidos genre y episodes
        self.anime["anime_id"] = self.anime["anime_id"].astype("int32")
        self.anime["members"] = self.anime["members"].fillna(0).astype("int64")
        self.anime["episodes"] = self.anime["episodes"].fillna(0).astype("int32")  # Convertir episodes a int
        self.anime["genre"] = self.anime["genre"].fillna("Unknown")  # Manejar géneros vacíos
        self.anime["name_norm"] = self.anime["name"].astype(str).str.strip().str.lower()

        self.ratings = pd.read_csv(self.data_dir / "ratings_clean_1.csv",
                                   usecols=["user_id","anime_id","rating"])
        self.ratings = self.ratings[self.ratings["rating"] != -1].copy()
        self.ratings["user_id"] = self.ratings["user_id"].astype("int32")
        self.ratings["anime_id"] = self.ratings["anime_id"].astype("int32")
        self.ratings["rating"] = self.ratings["rating"].astype("float32")

        self.id_by_name = dict(zip(self.anime["name_norm"], self.anime["anime_id"]))

    def _title_to_id_exact(self, title: str) -> Optional[int]:
        return self.id_by_name.get(str(title).strip().lower())

    def best_match_id(self, query: str) -> Optional[int]:
        q = str(query).strip().lower()
        if not q:
            return None
        mask = self.anime["name_norm"].str.contains(q, na=False)
        cand = self.anime.loc[mask, ["anime_id","members"]].sort_values("members", ascending=False)
        if cand.empty:
            return None
        return int(cand.iloc[0]["anime_id"])

    def suggest_titles(self, q: str, limit: int = 50) -> pd.DataFrame:
        qn = str(q).strip().lower()
        if not qn or len(qn) < 2:
            return pd.DataFrame(columns=["anime_id","name","members","genre","episodes"])
        df = (
            self.anime.loc[self.anime["name_norm"].str.contains(qn, na=False), 
                          ["anime_id","name","members","genre","episodes"]]
            .sort_values(["members","name"], ascending=[False, True])
            .head(int(limit))
            .reset_index(drop=True)
        )
        return df

    @lru_cache(maxsize=1024)
    def similares_por_id(self, anime_id: int, topk: int = 10) -> pd.DataFrame:
        users = self.ratings.loc[self.ratings["anime_id"] == anime_id, "user_id"].unique()
        if len(users) < self.min_periods:
            return pd.DataFrame(columns=["anime_id","correlation","common","name"])

        sub = self.ratings[self.ratings["user_id"].isin(users)].copy()
        ui = sub.pivot_table(index="user_id", columns="anime_id", values="rating", aggfunc="mean").astype("float32")
        if anime_id not in ui.columns:
            return pd.DataFrame(columns=["anime_id","correlation","common","name"])

        target = ui[anime_id]
        if target.count() < self.min_periods or float(target.std(ddof=0)) == 0.0:
            return pd.DataFrame(columns=["anime_id","correlation","common","name"])

        common = (~target.isna() & ~ui.isna()).sum(axis=0)
        mask = common >= self.min_periods
        if anime_id in mask.index:
            mask.loc[anime_id] = False

        cand = ui.loc[:, mask]
        if cand.shape[1] == 0:
            return pd.DataFrame(columns=["anime_id","correlation","common","name"])

        stds = cand.std(axis=0, ddof=0)
        cand = cand.loc[:, stds > 0]
        if cand.shape[1] == 0:
            return pd.DataFrame(columns=["anime_id","correlation","common","name"])

        with np.errstate(all="ignore"):
            sims = cand.corrwith(target, axis=0, method="pearson")

        sims = sims.dropna()
        if sims.empty:
            return pd.DataFrame(columns=["anime_id","correlation","common","name","genre","episodes"])

        top = sims.sort_values(ascending=False).head(int(topk))
        out = pd.DataFrame({
            "anime_id": top.index.astype("int32"),
            "correlation": top.values.astype("float32"),
            "common": common.loc[top.index].astype("int32").values
        })
        out = out.merge(self.anime[["anime_id","name","genre","episodes"]], on="anime_id", how="left")
        out = out.sort_values(["name"], ascending=[True]).reset_index(drop=True)
        return out

    def similares_por_titulo(self, title: str, topk: int = 10) -> pd.DataFrame:
        aid = self._title_to_id_exact(title)
        if aid is None:
            aid = self.best_match_id(title)
        if aid is None:
            return pd.DataFrame(columns=["anime_id","correlation","common","name"])
        return self.similares_por_id(aid, topk=topk)

    def recomendar_por_vistos(
        self,
        seen_ids: Optional[List[int]] = None,
        seen_names: Optional[List[str]] = None,
        ratings_map: Optional[Dict[int, float]] = None,
        default_rating: float = 10.0,
        topk: int = 10,
    ) -> pd.DataFrame:

        seen_ids = list(seen_ids or [])
        if seen_names:
            for n in seen_names:
                aid = self._title_to_id_exact(n)
                if aid is None:
                    aid = self.best_match_id(n)
                if aid is not None:
                    seen_ids.append(int(aid))

        seen_ids = [int(x) for x in set(seen_ids)]
        if not seen_ids:
            return pd.DataFrame(columns=["anime_id","name","score"])

        acc: Dict[int, float] = {}
        for aid in seen_ids:
            df = self.similares_por_id(aid, topk=200)  # más ancho para mezclar
            if df.empty:
                continue
            weight = float(ratings_map.get(aid, default_rating) if ratings_map else default_rating)
            for row in df.itertuples():
                if row.anime_id in seen_ids:
                    continue
                acc[row.anime_id] = acc.get(row.anime_id, 0.0) + (row.correlation * weight)

        if not acc:
            return pd.DataFrame(columns=["anime_id","name","score","genre","episodes"])

        out = pd.DataFrame([(k, v) for k, v in acc.items()], columns=["anime_id","score"])
        out = out.merge(self.anime[["anime_id","name","genre","episodes"]], on="anime_id", how="left")
        out = out.sort_values(by=["name","score"], ascending=[True, False]).head(int(topk)).reset_index(drop=True)
        return out


_recommender: Optional[LightRecommender] = None

def get_recommender(base_dir: Path, min_periods: int = 3) -> LightRecommender:
    global _recommender
    if _recommender is None:
        _recommender = LightRecommender(base_dir, min_periods=min_periods)
    else:
        if _recommender.min_periods != int(min_periods):
            _recommender = LightRecommender(base_dir, min_periods=min_periods)
    return _recommender
