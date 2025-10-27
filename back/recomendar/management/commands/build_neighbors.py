from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import os, csv, time
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
        parser.add_argument("--min-periods", type=int, default=3)
        parser.add_argument("--topk", type=int, default=50)
        parser.add_argument("--overwrite", action="store_true")

    def handle(self, *args, **opts):
        t0 = time.time()
        minp = int(opts["min_periods"])
        topk = int(opts["topk"])
        overwrite = bool(opts["overwrite"])

        cache_dir = _norm_cache_dir()
        out_csv = cache_dir / f"neighbors_top{topk}_mp{minp}.csv"

        if out_csv.exists() and not overwrite:
            self.stdout.write(self.style.WARNING(
                f"[build_neighbors] Found {out_csv}, skip (use --overwrite to rebuild)."
            ))
            return

        # Carga datos
        data_dir = Path(settings.BASE_DIR) / "recomendar" / "utils"
        ratings = pd.read_csv(
            data_dir / "ratings_clean_1.csv",
            usecols=["user_id", "anime_id", "rating"]
        )
        ratings = ratings[ratings["rating"] != -1].copy()
        ratings["user_id"] = ratings["user_id"].astype("int32")
        ratings["anime_id"] = ratings["anime_id"].astype("int32")
        ratings["rating"] = ratings["rating"].astype("float32")

        ui = ratings.pivot_table(
            index="user_id",
            columns="anime_id",
            values="rating",
            aggfunc="mean"
        ).astype("float32")

        # Escritura incremental CSV
        if out_csv.exists():
            out_csv.unlink()
        with out_csv.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["src_id", "dst_id", "correlation", "common"])

        total = ui.shape[1]
        self.stdout.write(self.style.WARNING(
            f"[build_neighbors] users={ui.shape[0]} items={ui.shape[1]} minp={minp} topk={topk}"
        ))

        done = 0
        for col in ui.columns:
            target = ui[col]

            # 1) el propio target debe tener suficientes valores y varianza
            if target.count() < minp:
                done += 1
                continue
            if float(target.std(ddof=0)) == 0.0:
                done += 1
                continue

            # 2) columnas candidatas con al menos minp co-valoraciones con 'target'
            common = (~target.isna() & ~ui.isna()).sum(axis=0)
            mask = common >= minp
            mask.loc[col] = False  # no compararse consigo mismo
            if not mask.any():
                done += 1
                continue

            cand = ui.loc[:, mask]

            # 3) filtra candidatas con varianza > 0 (evita divide-by-zero)
            stds = cand.std(axis=0, ddof=0)
            cand = cand.loc[:, stds > 0]
            if cand.shape[1] == 0:
                done += 1
                continue

            # 4) correlación SOLO con candidatas válidas (sin warnings)
            with np.errstate(all="ignore"):
                sims = cand.corrwith(target, axis=0, method="pearson")

            sims = sims.dropna().sort_values(ascending=False).head(topk)
            if sims.empty:
                done += 1
                continue

            # 5) guarda filas
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
