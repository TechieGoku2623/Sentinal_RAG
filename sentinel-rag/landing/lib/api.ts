/** Client types and helpers for Sentinel-RAG REST API (via Next.js route handlers). */

export interface QuerySource {
  id: string;
  section: string;
  excerpt: string;
}

export interface QueryResult {
  response: string;
  confidence: number;
  flagged: boolean;
  retry_count: number;
  validation_verdict: string;
  flag_reason: string;
  response_time_ms: number;
  sources: QuerySource[];
  cache_hit: boolean;
  latency_mode: string;
}

export interface HealthStatus {
  status: string;
  chroma_parent_chunks: number;
  chroma_child_chunks: number;
}

type RawSource = {
  text?: string;
  chunk?: string;
  source?: string;
  doc_name?: string;
  publication_year?: number;
  metadata?: {
    source?: string;
    doc_name?: string;
    publication_year?: number;
  };
};

export function mapSources(raw: RawSource[] | undefined): QuerySource[] {
  const out: QuerySource[] = [];
  const seen = new Set<string>();

  for (const item of raw ?? []) {
    const meta = item.metadata ?? item;
    const id = String(meta.source || meta.doc_name || item.source || "Unknown");
    const year = meta.publication_year ?? item.publication_year ?? 0;
    const key = `${id}:${year}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const section = year ? String(year) : "guideline";
    const excerpt = String(item.text || item.chunk || id).slice(0, 280);
    out.push({ id, section, excerpt: excerpt || id });
  }

  return out;
}

export async function fetchHealth(): Promise<HealthStatus | null> {
  try {
    const res = await fetch("/api/health", { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as HealthStatus;
  } catch {
    return null;
  }
}

export async function submitQuery(
  query: string,
  options?: { latencyMode?: string; useCache?: boolean },
): Promise<QueryResult> {
  const res = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      latency_mode: options?.latencyMode ?? "fast",
      use_cache: options?.useCache ?? true,
    }),
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((d: { msg?: string }) => d.msg).join("; ")
          : data.error || "Query failed";
    throw new Error(detail);
  }

  return {
    response: data.response,
    confidence: Math.round(Number(data.confidence) * 100),
    flagged: Boolean(data.flagged),
    retry_count: Number(data.retry_count ?? 0),
    validation_verdict: String(data.validation_verdict ?? "ERROR"),
    flag_reason: String(data.flag_reason ?? ""),
    response_time_ms: Number(data.response_time_ms ?? 0),
    sources: mapSources(data.sources),
    cache_hit: Boolean(data.cache_hit),
    latency_mode: String(data.latency_mode ?? "fast"),
  };
}
