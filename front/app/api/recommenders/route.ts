import { NextResponse } from "next/server";

export const runtime = "nodejs"; // nos aseguramos de edge-off por si usas libs no soportadas

export async function GET() {
    try {
        const res = await fetch("http://localhost:8000/getrecomenders", {
            // envía cookies/headers si hiciera falta
            // cache: "no-store" para evitar cache en dev
            cache: "no-store",
        });

        if (!res.ok) {
            return NextResponse.json(
                { error: `Backend error: ${res.status}` },
                { status: 502 }
            );
        }

        const data = await res.json();
        return NextResponse.json(data);
    } catch (e: any) {
        return NextResponse.json(
            { error: e?.message ?? "Proxy failed" },
            { status: 500 }
        );
    }
}
