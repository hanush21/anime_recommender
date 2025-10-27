import { NextRequest, NextResponse } from "next/server";

const BASE =
    process.env.SERVER_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";

export async function GET(req: NextRequest) {
    try {
        const inUrl = new URL(req.url);
        const q = inUrl.searchParams.get("q") || inUrl.searchParams.get("s") || "";
        const limit = inUrl.searchParams.get("limit") || "50";
        const offset = inUrl.searchParams.get("offset") || "0";
        const min_r = inUrl.searchParams.get("min_r") || "0";
        const minp = inUrl.searchParams.get("minp") || "3";

        const out = new URL("/titles", BASE);

        // Solo añade 's' si hay texto real
        if (q.trim().length > 0) out.searchParams.set("s", q.trim());
        if (limit) out.searchParams.set("limit", limit);
        if (offset) out.searchParams.set("offset", offset);
        if (min_r) out.searchParams.set("min_r", min_r);
        if (minp) out.searchParams.set("minp", minp);

        const r = await fetch(out.toString(), { cache: "no-store" });
        if (!r.ok) {
            const text = await r.text().catch(() => "");
            return NextResponse.json(
                { error: `Backend ${r.status}`, detail: text.slice(0, 500) },
                { status: 502 }
            );
        }
        const data = await r.json();
        return NextResponse.json(data, { status: 200 });
    } catch (e: any) {
        return NextResponse.json({ error: e?.message ?? "Proxy failed" }, { status: 500 });
    }
}
