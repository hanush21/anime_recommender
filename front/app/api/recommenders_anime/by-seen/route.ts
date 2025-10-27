import { NextResponse } from "next/server";
import MOCK_RECS from "@/lib/data.json";


export async function POST(req: Request) {
    try {
        const { seen } = await req.json() as { seen?: string[] };
        const seenSet = new Set((seen ?? []).map(s => s.toLowerCase()));

        const candidates = (MOCK_RECS as { name: string; correlation: number }[])
            .filter(x => !seenSet.has(x.name.toLowerCase()))
            .sort((a, b) => b.correlation - a.correlation)
            .slice(0, 10);

        return NextResponse.json(candidates, { status: 200 });
    } catch (e: any | unknown) {
        return NextResponse.json({ error: e?.message ?? "Bad Request" }, { status: 400 });
    }
}
