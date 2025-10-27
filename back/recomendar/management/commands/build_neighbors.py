from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import os, csv, time, warnings
import pandas as pd
import numpy as np


def _norm_cache_dir() -> Path:
    base = os.environ.get("DJ_CACHE_DIR")
    if base:
        p = Path(base)
    else:
        p = Path(settings.BASE_DIR) / "recomendar" / "utils" / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


class Command(BaseCommand):
    help = "Precompute top-K neighbors (Pearson) per anime and persist to CSV for fast lookups."

    def add_arguments(self, parser):
        parser.add_argument("--min-periods", type=int, default=3,
                            help="Mínimo de co-valoraciones para aceptar una correlación.")
        parser.add_argument("--topk", type=int, default=50,
                            help="Vecinos a guardar por anime.")
        parser.add_argument("--overwrite", action="store_true",
                            help="Recalcula aunque exista el CSV en caché.")
        parser.add_argument("--item-min-reviews", type=int, default=100,
                            help="Filtra animes con menos de N ratings ANTES de pivotear (reduce memoria).")

    def handle(self, *args, **opts):
        t0 = time.time()
        minp = int(opts["min_periods"])
        topk = int(opts["topk"])
        overwrite = bool(opts["overwrite"])
        item_min_reviews = int(opts["item_min_reviews"])

        cache_dir = _norm_cache_dir()
        out_csv = cache_dir / f"neighbors_top{topk}_mp{minp}_imin{item_min_reviews}.csv"

        if out_csv.exists() and not overwrite:
            self.stdout.write(self.style.WARNING(
                f"[build_neighbors] Found {out_csv}, skip (use --overwrite to rebuild)."
            ))
            return

        # Silencia RuntimeWarnings típicos de numpy (dof<=0, divide-by-zero...)
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="numpy")

        # -------- Carga & filtros previos (para no OOM) ----------
        data_dir = Path(settings.BASE_DIR) / "recomendar" / "utils"
        ratings = pd.read_csv(
            data_dir / "ratings_clean_1.csv",
            usecols=["user_id", "anime_id", "rating"]
        )
        ratings = ratings[ratings["rating"] != -1].copy()

        # casts compactos
        ratings["user_id"] = ratings["user_id"].astype("int32")
        ratings["anime_id"] = ratings["anime_id"].astype("int32")
        ratings["rating"] = ratings["rating"].astype("float32")

        # FILTRO por popularidad de item para reducir columnas del pivot
        item_counts = ratings.groupby("anime_id")["rating"].count().astype("int32")
        keep_items = item_counts[item_counts >= item_min_reviews].index
        ratings = ratings[ratings["anime_id"].isin(keep_items)].copy()

        # Si tras filtrar quedó muy poco, aborta con mensaje
        if ratings["anime_id"].nunique() == 0:
            self.stdout.write(self.style.ERROR(
                f"[build_neighbors] No items after filter item_min_reviews={item_min_reviews}"
            ))
            return

        # pivot denso (ya reducido)
        ui = ratings.pivot_table(index="user_id", columns="anime_id", values="rating", aggfunc="mean")
        ui = ui.astype("float32")

        # -------- Escritura incremental CSV ----------
        if out_csv.exists():
            out_csv.unlink()
        with out_csv.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["src_id", "dst_id", "correlation", "common"])

        total = ui.shape[1]
        self.stdout.write(self.style.WARNING(
            f"[build_neighbors] users={ui.shape[0]} items={ui.shape[1]} "
            f"minp={minp} topk={topk} item_min_reviews={item_min_reviews}"
        ))

        done = 0
        for col in ui.columns:
            target = ui[col]

            # objetivo debe tener suficientes valores y varianza
            if target.count() < minp:
                done += 1
                continue
            if float(target.std(ddof=0)) == 0.0:
                done += 1
                continue

            # candidatos con al menos 'minp' co-valoraciones con target
            common = (~target.isna() & ~ui.isna()).sum(axis=0)
            mask = common >= minp
            # no compararse con sí mismo
            if col in mask.index:
                mask.loc[col] = False
            if not mask.any():
                done += 1
                continue

            cand = ui.loc[:, mask]

            # candidatas con varianza > 0 (evita divide-by-zero)
            stds = cand.std(axis=0, ddof=0)
            cand = cand.loc[:, stds > 0]
            if cand.shape[1] == 0:
                done += 1
                continue

            # correlación sólo con candidatas válidas
            with np.errstate(all="ignore"):
                sims = cand.corrwith(target, axis=0, method="pearson")

            sims = sims.dropna().sort_values(ascending=False).head(topk)
            if sims.empty:
                done += 1
                continue

            out = pd.DataFrame({
                "src_id": col,
                "dst_id": sims.index.astype("int32"),
                "correlation": sims.values.astype("float32"),
                "common": common.loc[sims.index].astype("int32").values,
            })
            out.to_csv(out_csv, mode="a", header=False, index=False)

            done += 1
            if done % 100 == 0:
                self.stdout.write(f"[build_neighbors] {done}/{total} items...")

        self.stdout.write(self.style.SUCCESS(
            f"[build_neighbors] DONE in {time.time()-t0:.2f}s → {out_csv}"
        ))
