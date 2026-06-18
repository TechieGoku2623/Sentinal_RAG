"use client";

import Link from "next/link";
import { INSIGHT_TOPICS } from "@/content/insights";
import { FadeIn, StaggerContainer, StaggerItem } from "./FadeIn";

export function ThoughtLeadership() {
  return (
    <section id="insights" className="mx-auto max-w-6xl px-6 py-20">
      <FadeIn>
        <p className="section-label">Thought leadership</p>
        <h2 className="mt-2 text-3xl font-bold text-navy md:text-4xl">
          Built in public — for inbound AI roles
        </h2>
        <p className="mt-4 max-w-2xl text-slate-muted">
          Three topics recruiters search for when hiring LangGraph, HIPAA-aware, and
          clinical AI engineers. Pair with the Loom demo and GitHub repo on LinkedIn.
        </p>
      </FadeIn>

      <StaggerContainer className="mt-12 grid gap-6 lg:grid-cols-3">
        {INSIGHT_TOPICS.map((topic) => (
          <StaggerItem key={topic.slug}>
            <Link
              href={`/insights#${topic.slug}`}
              className="group flex h-full flex-col surface-card p-6"
            >
              <span className="text-xs font-semibold uppercase tracking-widest text-brand">
                Topic {topic.number}
              </span>
              <h3 className="mt-3 text-lg font-semibold text-navy group-hover:text-brand">
                {topic.title}
              </h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-muted">
                {topic.hook}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {topic.tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600"
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <span className="mt-4 text-sm font-medium text-brand">
                Read + LinkedIn draft →
              </span>
            </Link>
          </StaggerItem>
        ))}
      </StaggerContainer>

      <FadeIn delay={0.15}>
        <div className="mt-10 rounded-xl border border-brand/20 bg-brand-pale p-6 text-center">
          <p className="text-sm text-slate-700">
            Each article above expands on a core theme from the Sentinel-RAG platform.
          </p>
        </div>
      </FadeIn>
    </section>
  );
}
