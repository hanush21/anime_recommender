"use client";

import { useMemo, useState } from "react";
import axios from "axios";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import RecommendationsTable from "@/components/ui/recommendations-table";
import SeenPicker from "@/components/seen-picker";
import type { RecommenderItem } from "@/lib/types";
import MOCK_RECS  from "@/lib/data.json";

const USE_MOCK = false;

export default function Home() {
  const [query, setQuery] = useState("");
  const [data, setData] = useState<RecommenderItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setErr(null);
    setData(null);
    setLoading(true);

    try {
      if (USE_MOCK) {
        await new Promise((r) => setTimeout(r, 500));
        const q = query.trim().toLowerCase();
        const results = MOCK_RECS.filter((x) =>
          x.name.toLowerCase().includes(q)
        );
        setData(results);
      } else {
        const res = await axios.get<RecommenderItem[]>("/api/recommenders", {
          params: { q: query.trim() },
        });
        setData(res.data ?? []);
      }
    } catch (e: any) {
      setErr(e?.message ?? "Error al cargar datos");
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  const stats = useMemo(() => {
    if (!data || data.length === 0) return { count: 0, avg: 0 };
    const avg = data.reduce((s, x) => s + x.correlation, 0) / data.length;
    return { count: data.length, avg };
  }, [data]);

  return (
    <div className="flex min-h-screen justify-center bg-zinc-50 font-sans relative dark:bg-black p-8">
      <div className="w-full max-w-6xl space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">Anime Recommender</h1>
          <p className="text-sm text-muted-foreground">
            Recomendaciones basadas en similitud item–item. Escribe un título y busca.
          </p>
        </div>

        {/* Layout principal */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Columna izquierda: búsqueda + métricas */}
          <div className="md:col-span-1 space-y-4">
            <Card>
              <CardContent className="p-4 space-y-3">
                <form onSubmit={onSearch} className="space-y-3">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Título de animé</label>
                    <Input
                      placeholder="Ej: Naruto, One Piece…"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={!query.trim() || loading}>
                    {loading ? "Buscando..." : "Buscar"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="text-sm text-muted-foreground mb-2">Resumen</div>
                {loading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-7 w-full" />
                    <Skeleton className="h-7 w-2/3" />
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border p-3">
                      <div className="text-xs text-muted-foreground">Resultados</div>
                      <div className="text-xl font-semibold">{stats.count}</div>
                    </div>
                    <div className="rounded-xl border p-3">
                      <div className="text-xs text-muted-foreground">Media corr.</div>
                      <div className="text-xl font-semibold">
                        {stats.count ? stats.avg.toFixed(3) : "—"}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
            <SeenPicker onResults={(items) => {
              setErr(null);
              setLoading(false);
              setData(items);
            }} />

          </div>

          {/* Columna derecha: resultados */}
          <div className="md:col-span-2 space-y-4">
            {loading && (
              <div className="space-y-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            )}

            {!loading && err && (
              <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-md p-3">
                {err}
              </div>
            )}

            {!loading && data && <RecommendationsTable items={data} />}

            {!loading && data === null && !err && (
              <Card>
                <CardContent className="p-8 text-center text-sm text-muted-foreground">
                  Escribe un título en el formulario para ver recomendaciones.
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* Footer simple */}
        <div className="text-center posit w-[100%] absolute bottom-0 text-xs text-muted-foreground pt-4">
          Demo — Next.js · Tailwind · shadcn/ui
        </div>
      </div>
    </div>
  );
}
