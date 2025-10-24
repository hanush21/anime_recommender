import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET(req: NextRequest) {
    try {
        const { searchParams } = new URL(req.url);
        const q = searchParams.get("q") ?? "";
        const url = new URL("http://localhost:8000/getrecomenders");
        if (q) url.searchParams.set("q", q);

        const res = await fetch(url.toString(), { cache: "no-store" });
        if (!res.ok) return NextResponse.json({ error: `Backend ${res.status}` }, { status: 502 });

        const data = await res.json();
        return NextResponse.json(data);
    } catch (e: any) {
        return NextResponse.json({ error: e?.message ?? "Proxy failed" }, { status: 500 });
    }
}
