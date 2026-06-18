"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import { METRICS } from "@/lib/metrics";
import { SITE, apiDocsUrl } from "@/lib/site";
import {
  animateCounter,
  heroEntrance,
  prefersReducedMotion,
  revertAnim,
  type AnimInstance,
} from "@/lib/motion/anime";

export function HeroMotion() {
  const sectionRef = useRef<HTMLElement>(null);
  const statRef = useRef<HTMLSpanElement>(null);
  const animRef = useRef<AnimInstance | null>(null);
  const counterRef = useRef<AnimInstance | null>(null);

  useEffect(() => {
    const root = sectionRef.current;
    if (!root) return;

    if (prefersReducedMotion()) {
      if (statRef.current) statRef.current.textContent = METRICS.keywordMatch;
      return;
    }

    if (statRef.current) {
      statRef.current.textContent = "0%";
      counterRef.current = animateCounter(
        (value) => {
          if (statRef.current) statRef.current.textContent = `${value}%`;
        },
        METRICS.keywordMatchNum,
        { duration: 1200, delay: 180 },
      );
    }

    animRef.current = heroEntrance(root);

    return () => {
      revertAnim(animRef.current);
      revertAnim(counterRef.current);
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      className="hero-band border-b border-[var(--color-rule)] px-6 pb-16 pt-10"
    >
      <div className="mx-auto grid max-w-6xl items-start gap-12 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <p data-hero-label className="section-label" style={{ opacity: 0 }}>
            Clinical validation infrastructure
          </p>
          <div className="mt-4 flex flex-wrap items-end gap-x-4 gap-y-2">
            <span
              ref={statRef}
              data-hero-stat
              className="stat-figure"
              style={{ opacity: 0 }}
            >
              {METRICS.keywordMatch}
            </span>
            <h1
              data-hero-title
              className="font-display max-w-xl text-3xl font-semibold leading-tight tracking-tight text-[var(--color-ink)] md:text-4xl"
              style={{ opacity: 0 }}
            >
              keyword match on the eval harness — with explicit flagging when the corpus
              cannot support an answer.
            </h1>
          </div>
          <p
            data-hero-body
            className="mt-5 max-w-xl text-base leading-relaxed text-[var(--color-ink-2)]"
            style={{ opacity: 0 }}
          >
            Sentinel-RAG validates protocol questions against your guideline corpus with
            deterministic grounding scores, cross-model verification, and human escalation —
            measured on {METRICS.questions} eval questions, not marketing claims.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <a
              data-hero-action
              href={SITE.workspaceUrl}
              className="btn-primary inline-block cursor-pointer"
              style={{ opacity: 0 }}
            >
              Open clinical workspace
            </a>
            <a
              data-hero-action
              href="#platform"
              className="btn-secondary inline-block cursor-pointer"
              style={{ opacity: 0 }}
            >
              Read the pipeline
            </a>
            <a
              data-hero-action
              href={apiDocsUrl()}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost cursor-pointer text-sm font-medium"
              style={{ opacity: 0 }}
            >
              API docs
            </a>
          </div>
        </div>

        <div
          data-hero-panel
          className="code-panel overflow-hidden"
          style={{ opacity: 0 }}
        >
          <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2 text-[11px] text-slate-400">
            <span className="h-2 w-2 rounded-full bg-red-400/80" />
            <span className="h-2 w-2 rounded-full bg-amber-400/80" />
            <span className="h-2 w-2 rounded-full bg-emerald-400/80" />
            <span className="ml-2 font-mono">POST /v1/query</span>
            <span className="ml-auto font-mono text-emerald-300">200 OK</span>
          </div>
          <pre className="overflow-x-auto p-4 text-[var(--color-graphite-ink)]">{`{
  "query": "First-line therapy for type 2 diabetes?",
  "confidence": 0.91,
  "validation_verdict": "SUPPORTED",
  "flagged": false,
  "latency_mode": "fast",
  "cache_hit": false,
  "response_time_ms": 4200
}`}</pre>
          <div className="border-t border-white/10 px-4 py-3 text-[11px] text-slate-400">
            <Image
              src="/logo.png"
              alt="Sentinel-RAG workspace preview"
              width={900}
              height={420}
              className="mt-2 rounded-md border border-white/10 opacity-90"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
