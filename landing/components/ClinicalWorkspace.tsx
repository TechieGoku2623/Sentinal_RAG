"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { AgentPipeline, type AgentStage } from "./AgentPipeline";
import { QueryInput } from "./QueryInput";
import { AnswerCard } from "./AnswerCard";
import { fetchHealth, submitQuery, type HealthStatus, type QueryResult } from "@/lib/api";
import { SITE, apiDocsUrl } from "@/lib/site";

const EXAMPLE_QUERIES = [
  "What is the first-line treatment for Type 2 diabetes?",
  "Can metformin be used with kidney disease?",
  "What happens if a patient misses a dose?",
] as const;

const STAGE_SEQUENCE: AgentStage[] = ["retrieve", "generate", "reflect", "output"];

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function ClinicalWorkspace() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [stage, setStage] = useState<AgentStage>("idle");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [lastQuery, setLastQuery] = useState("");

  const refreshHealth = useCallback(async () => {
    setHealth(await fetchHealth());
  }, []);

  useEffect(() => {
    refreshHealth();
    const id = setInterval(refreshHealth, 30_000);
    return () => clearInterval(id);
  }, [refreshHealth]);

  const runQuery = async (query: string) => {
    setLastQuery(query);
    setError(null);
    setResult(null);
    setLoading(true);

    for (const s of STAGE_SEQUENCE) {
      setStage(s);
      await sleep(s === "reflect" ? 700 : 450);
    }

    try {
      const data = await submitQuery(query);
      setResult(data);
      setStage(data.flagged ? "flag" : "output");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
      setStage("idle");
    } finally {
      setLoading(false);
    }
  };

  const apiOnline = health?.status === "ok";
  const kbLoaded = (health?.chroma_parent_chunks ?? 0) > 0;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="section-label m-0">Live workspace</p>
          <h1 className="mt-2 font-display text-3xl font-bold text-[var(--text-primary)]">
            Protocol validation
          </h1>
          <p className="mt-2 max-w-xl text-[15px] leading-relaxed text-[var(--text-secondary)]">
            Production-grade React UI on the Sentinel-RAG FastAPI backend — retrieve, generate,
            reflect, and escalate with full source provenance.
          </p>
        </div>
        <div
          className="flex items-center gap-2 rounded-lg border px-3 py-2 font-mono text-[11px]"
          style={{
            borderColor: apiOnline ? "rgba(14,199,136,0.3)" : "rgba(232,64,64,0.3)",
            background: apiOnline ? "rgba(14,199,136,0.06)" : "rgba(232,64,64,0.06)",
            color: apiOnline ? "var(--teal)" : "#E84040",
          }}
        >
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: apiOnline ? "var(--teal)" : "#E84040" }}
          />
          {apiOnline ? "API connected" : "API offline"}
          {apiOnline && (
            <span className="text-[var(--text-muted)]">
              · {health?.chroma_parent_chunks ?? 0} guideline chunks
            </span>
          )}
        </div>
      </div>

      {!kbLoaded && apiOnline && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 rounded-lg border border-[rgba(240,165,0,0.25)] bg-[rgba(240,165,0,0.06)] px-4 py-3 text-sm text-[var(--text-secondary)]"
        >
          Knowledge base empty — run{" "}
          <code className="text-[var(--amber)]">python -m src.ingest</code> before expecting
          grounded answers.
        </motion.div>
      )}

      <AgentPipeline stage={loading ? stage : result ? (result.flagged ? "flag" : "output") : "idle"} />

      <QueryInput onSubmit={runQuery} isLoading={loading} />

      <div className="mb-6 flex flex-wrap gap-2">
        {EXAMPLE_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            disabled={loading}
            onClick={() => runQuery(q)}
            className="cursor-pointer rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-left text-[12px] text-[var(--text-secondary)] transition-colors hover:border-[rgba(14,199,136,0.3)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-[rgba(232,64,64,0.3)] bg-[rgba(232,64,64,0.08)] px-4 py-3 text-sm text-[#E84040]">
          {error}
        </div>
      )}

      {result && (
        <AnswerCard
          answer={result.response}
          confidence={result.confidence}
          retries={result.retry_count}
          latencyMs={result.response_time_ms}
          docCount={result.sources.length}
          flagged={result.flagged}
          sources={result.sources}
        />
      )}

      <section className="mt-14 rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-surface)] p-6">
        <p className="section-label m-0">Deployment surfaces</p>
        <h2 className="mt-2 text-lg font-semibold text-[var(--text-primary)]">
          More than Streamlit — pick the right showcase
        </h2>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {[
            {
              title: "Portfolio + live demo (this page)",
              tag: "Recommended for GitHub",
              detail: "Next.js · Vercel-ready · calls FastAPI",
              href: "/workspace",
              active: true,
            },
            {
              title: "REST API + OpenAPI",
              tag: "Integrators & backends",
              detail: "FastAPI · Swagger · batch jobs",
              href: apiDocsUrl(),
              external: true,
            },
            {
              title: "Clinical workspace (Streamlit)",
              tag: "Internal / rapid prototyping",
              detail: "Full admin flows · patient context",
              href: SITE.streamlitUrl,
              external: true,
            },
            {
              title: "Source & docs",
              tag: "Engineering review",
              detail: "Architecture · safety · eval harness",
              href: SITE.docsUrl,
              external: true,
            },
          ].map((item) => (
            <div
              key={item.title}
              className="rounded-lg border p-4"
              style={{
                borderColor: item.active ? "rgba(14,199,136,0.35)" : "var(--border-subtle)",
                background: item.active ? "rgba(14,199,136,0.04)" : "var(--bg-elevated)",
              }}
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-[var(--text-primary)]">{item.title}</span>
                {item.active && (
                  <span className="rounded px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-[var(--teal)]"
                    style={{ background: "rgba(14,199,136,0.12)" }}>
                    You are here
                  </span>
                )}
              </div>
              <p className="m-0 font-mono text-[10px] uppercase tracking-wider text-[var(--teal)]">
                {item.tag}
              </p>
              <p className="mt-2 m-0 text-[13px] text-[var(--text-muted)]">{item.detail}</p>
              {!item.active && (
                <a
                  href={item.href}
                  target={item.external ? "_blank" : undefined}
                  rel={item.external ? "noopener noreferrer" : undefined}
                  className="mt-3 inline-block text-[13px] text-[var(--teal)] no-underline hover:underline"
                >
                  Open →
                </a>
              )}
            </div>
          ))}
        </div>
        <p className="mt-5 text-[13px] text-[var(--text-muted)]">
          For a public GitHub README, link visitors to{" "}
          <Link href="/workspace" className="text-[var(--teal)] no-underline hover:underline">
            /workspace
          </Link>{" "}
          (this demo) and{" "}
          <a href={apiDocsUrl()} className="text-[var(--teal)] no-underline hover:underline">
            /docs
          </a>{" "}
          — not only the Streamlit port.
          {lastQuery ? "" : ""}
        </p>
      </section>
    </div>
  );
}
