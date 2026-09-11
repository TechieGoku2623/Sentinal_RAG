import { NextRequest, NextResponse } from "next/server";

const API_BASE = (process.env.SENTINEL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);
const API_KEY = process.env.SENTINEL_API_KEY ?? "";

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) headers["X-API-Key"] = API_KEY;

  try {
    const upstream = await fetch(`${API_BASE}/v1/query`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    const data = await upstream.json().catch(() => ({}));
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Cannot reach Sentinel-RAG API. Start it with: uvicorn src.api.main:app --reload --port 8000",
      },
      { status: 503 },
    );
  }
}
