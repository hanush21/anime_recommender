import os, re, time, csv, json
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

def _cache_dir(base_data_dir: Path) -> Path:
    dj = os.environ.get("DJ_CACHE_DIR")
    if dj:
        p = Path(dj)
    else:
        p = base_data_dir / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p

class ItemBasedRecommender:
    """
    Usa vecinos precomputados (neighbors CSV) para respuestas en milisegundos.
    Fallback: corrwith puntual si falta el vecindario de algún item.
    """
    def __init__(self, data_dir: Path, min_periods: int = 3, topk_default: int = 50):
        t0 = time.time()
        self.data_dir = Path(data_dir)
        self.min_periods = int(min_periods)
        self.topk_default = int(os.environ.get("DJ_TOPK", topk_default))

        # Anime
        a_cols = ["anime_id", "name"]
        self.anime = pd.read_csv(self.data_dir / "anime.csv", usecols=a_cols)
        self.anime["name_norm"] = self.anime["name"].map(_norm)
        self.id_to_name = dict(zip(self.anime["anime_id"], self.anime["name"]))
        self.name_to_id = (
            self.anime.drop_duplicates("name_norm").set_index("name_norm")["anime_id"].to_dict()
        )

        # Intentar cargar vecinos
        cdir = _cache_dir(self.data_dir)
        neigh_csv = cdir / f"neighbors_top{self.topk_default}_mp{self.min_periods}.csv"
        self._neighbors: Dict[int, pd.DataFrame] = {}

        if neigh_csv.exists():
            # Cargar a dict en memoria
            df = pd.read_csv(neigh_csv, dtype={"src_id":"int32","dst_id":"int32","correlation":"float32","common":"int32"})
            df = df.sort_values(["src_id","correlation"], ascending=[True, False])
            for src, grp in df.groupby("src_id"):
                g = grp[["dst_id","correlation"]].copy()
                g["name"] = g["dst_id"].map(self.id_to_name)
                g.rename(columns={"dst_id":"anime_id"}, inplace=True)
                self._neighbors[int(src)] = g[["anime_id","name","correlation"]].reset_index(drop=True)

        # Fallback: pivot ligero para corrwith puntual
        self.ui = None
        if not self._neighbors:
            ratings = pd.read_csv(self.data_dir / "ratings_clean_1.csv", usecols=["user_id","anime_id","rating"])
            ratings = ratings[ratings["rating"] != -1].copy()
            ratings["user_id"] = ratings["user_id"].astype("int32")
            ratings["anime_id"] = ratings["anime_id"].astype("int32")
            ratings["rating"] = ratings["rating"].astype("float32")
            self.ui = ratings.pivot_table(index="user_id", columns="anime_id", values="rating", aggfunc="mean").astype("float32")

        self.built_at = datetime.now(timezone.utc).isoformat()
        self.build_seconds = round(time.time() - t0, 3)
        self.neighbors_loaded = bool(self._neighbors)

    def _find_id(self, title: str) -> Optional[int]:
        t = _norm(title)
        if t in self.name_to_id:
            return int(self.name_to_id[t])
        m = self.anime[self.anime["name_norm"].str.contains(t, na=False)]
        return int(m.iloc[0]["anime_id"]) if not m.empty else None

    def _fallback_corr(self, aid: int, topk: int) -> pd.DataFrame:
        if self.ui is None or aid not in self.ui.columns:
            return pd.DataFrame(columns=["anime_id","name","correlation"])
        target = self.ui[aid]
        sims = self.ui.corrwith(target, axis=0, method="pearson", drop=False)
        common = (~target.isna() & ~self.ui.isna()).sum(axis=0)
        sims = sims.where(common >= self.min_periods).dropna()
        sims = sims.drop(index=aid, errors="ignore").sort_values(ascending=False).head(topk)
        out = pd.DataFrame({"anime_id": sims.index.astype("int32"), "correlation": sims.values.astype("float32")})
        out["name"] = out["anime_id"].map(self.id_to_name)
        return out[["anime_id","name","correlation"]]

    # --------- API ----------
    def similares_por_titulo(self, title: str, topk: int = 10, order: str = "name") -> pd.DataFrame:
        aid = self._find_id(title)
        if aid is None:
            raise ValueError(f"No encontré '{title}'")
        if self._neighbors and aid in self._neighbors:
            out = self._neighbors[aid].head(topk).copy()
        else:
            out = self._fallback_corr(aid, max(topk, self.topk_default))
            out = out.head(topk)
        if order == "name":
            out = out.sort_values("name", kind="stable")
        return out.reset_index(drop=True)

    def recomendar_por_vistos(
        self,
        seen_ids: Optional[List[int]] = None,
        seen_names: Optional[List[str]] = None,
        ratings_map: Optional[Dict[int, float]] = None,
        default_rating: float = 10.0,
        topk: int = 10,
        order: str = "name",
    ) -> pd.DataFrame:
        items: List[int] = []
        if seen_names:
            for n in seen_names:
                aid = self._find_id(n)
                if aid is not None:
                    items.append(aid)
        if seen_ids:
            items.extend(seen_ids)
        items = [i for i in dict.fromkeys(items) if (self._neighbors and i in self._neighbors) or (self.ui is not None and i in self.ui.columns)]
        if not items:
            return pd.DataFrame(columns=["anime_id","name","correlation"])

        acc = {}
        for aid in items:
            neigh = None
            if self._neighbors and aid in self._neighbors:
                neigh = self._neighbors[aid]
            else:
                neigh = self._fallback_corr(aid, max(topk, self.topk_default))
            weight = float(ratings_map.get(aid, default_rating)) if ratings_map else default_rating
            for _, row in neigh.iterrows():
                dst = int(row["anime_id"])
                if dst in items:  # no recomendar vistos
                    continue
                acc[dst] = acc.get(dst, 0.0) + float(row["correlation"]) * weight

        if not acc:
            return pd.DataFrame(columns=["anime_id","name","correlation"])

        out = pd.DataFrame({"anime_id": list(acc.keys()), "correlation": list(acc.values())})
        out["name"] = out["anime_id"].map(self.id_to_name)
        # orden
        if order == "name":
            out = out.sort_values("name", kind="stable")
        else:
            out = out.sort_values("correlation", ascending=False, kind="stable")
        return out.head(topk).reset_index(drop=True)

    def status(self) -> dict:
        return {
            "ready": True,
            "neighbors_loaded": self.neighbors_loaded,
            "min_periods": self.min_periods,
            "topk_default": self.topk_default,
            "built_at": self.built_at,
            "build_seconds": self.build_seconds,
        }

def get_recommender(base_dir: Path, min_periods: int = 3) -> ItemBasedRecommender:
    global _singleton
    if _singleton is None:
        _singleton = ItemBasedRecommender(base_dir, min_periods=min_periods)
    return _singleton

def get_status(base_dir: Path, min_periods: int = 3) -> dict:
    return get_recommender(base_dir, min_periods).status()
