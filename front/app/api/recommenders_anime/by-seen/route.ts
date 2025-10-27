import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const base = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
    const body = await req.json();

    const res = await fetch(`${base}/recommend_by_seen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      // importante para Dev: no caches
      cache: "no-store",
    });

    if (!res.ok) {
      const txt = await res.text();
      return NextResponse.json({ error: `Backend ${res.status}: ${txt}` }, { status: 502 });
    }

    const data = await res.json();
    return NextResponse.json(data, { status: 200 });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "Proxy failed" }, { status: 500 });
  }
}
