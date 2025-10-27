import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET(req: NextRequest) {
    try {
        const { searchParams } = new URL(req.url);
        const q = searchParams.get("q") ?? "";
        const limit = searchParams.get("limit") ?? "200";

        const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const url = new URL(`${base.replace(/\/$/, "")}/anime/titles`);
        if (q) url.searchParams.set("q", q);
        if (limit) url.searchParams.set("limit", limit);

        const res = await fetch(url.toString(), { cache: "no-store" });
        if (!res.ok) {
            return NextResponse.json({ error: `Backend ${res.status}` }, { status: 502 });
        }
        const data = await res.json();
        return NextResponse.json(data, { status: 200 });
    } catch (e: any) {
        return NextResponse.json({ error: e?.message ?? "Proxy failed" }, { status: 500 });
    }
}
