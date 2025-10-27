import { NextRequest, NextResponse } from "next/server";

const BASE =
  process.env.SERVER_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

type BackRec = {
  name?: string;
  title?: string;
  anime_id?: number | string;
  correlation?: number | string | null;
  score?: number | string | null;
  members?: number;
};

export async function POST(req: NextRequest) {
  try {
    const incoming = await req.json().catch(() => ({}));

    // Normaliza body con defaults
    const body = {
      seen_names: Array.isArray(incoming?.seen_names) ? incoming.seen_names : [],
      seen_ids: Array.isArray(incoming?.seen_ids) ? incoming.seen_ids : [],
      ratings: typeof incoming?.ratings === "object" && incoming?.ratings !== null ? incoming.ratings : undefined,
      topk: Number.isFinite(Number(incoming?.topk)) ? Number(incoming.topk) : 10,
      minp: Number.isFinite(Number(incoming?.minp)) ? Number(incoming.minp) : 3,
      rating: Number.isFinite(Number(incoming?.rating)) ? Number(incoming.rating) : 10,
    };

    if (body.seen_names.length === 0 && body.seen_ids.length === 0 && !body.ratings) {
      return NextResponse.json(
        { error: "Debes enviar seen_names, seen_ids o ratings." },
        { status: 400 }
      );
    }

    const url = `${BASE.replace(/\/$/, "")}/recommend_by_seen`;

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      return NextResponse.json(
        { error: `Backend ${res.status}`, detail: txt.slice(0, 500) },
        { status: 502 }
      );
    }

    const raw: unknown = await res.json();
    const arr = Array.isArray(raw) ? (raw as BackRec[]) : [];

    // Normaliza siempre a { name, correlation }
    const items = arr.map((x) => {
      const name =
        x.name ??
        x.title ??
        (x.anime_id != null ? String(x.anime_id) : "Unknown");
      const corrRaw = x.correlation ?? x.score ?? 0;
      const correlation = Number(corrRaw);
      return {
        name,
        correlation: Number.isFinite(correlation) ? correlation : 0,
      };
    });

    // Ordena por mayor correlación
    items.sort((a, b) => b.correlation - a.correlation);

    return NextResponse.json(items, { status: 200 });
  } catch (e: any) {
    return NextResponse.json(
      { error: e?.message ?? "Proxy failed" },
      { status: 500 }
    );
  }
}
