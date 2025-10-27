import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
    process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const runtime = "nodejs";

export async function GET(req: NextRequest) {
    try {
        const { searchParams } = new URL(req.url);
        const q = searchParams.get("q") ?? "";
        const topk = searchParams.get("topk") ?? "10";

        const url = new URL("/getrecomenders", BACKEND_URL);
        if (q) url.searchParams.set("q", q);
        if (topk) url.searchParams.set("topk", topk);

        const res = await fetch(url.toString(), { cache: "no-store" });
        if (!res.ok) {
            return NextResponse.json({ error: `Backend error: ${res.status}` }, { status: 502 });
        }

        const data = await res.json();
        return NextResponse.json(data, { status: 200 });
    } catch (e: any) {
        return NextResponse.json({ error: e?.message ?? "Proxy failed" }, { status: 500 });
    }
}
