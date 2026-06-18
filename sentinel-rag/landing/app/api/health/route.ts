import { NextResponse } from "next/server";

const API_BASE = (process.env.SENTINEL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { status: "offline", chroma_parent_chunks: 0, chroma_child_chunks: 0 },
      { status: 503 },
    );
  }
}
