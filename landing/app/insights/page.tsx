import type { Metadata } from "next";

import Link from "next/link";

import { INSIGHT_TOPICS } from "@/content/insights";

import { Nav } from "@/components/Nav";

import { FadeIn } from "@/components/FadeIn";

import { SITE } from "@/lib/site";



export const metadata: Metadata = {

  title: "Insights · Sentinel-RAG",

  description:

    "LangGraph, HIPAA health data pipelines, and clinical AI safety — engineering notes for regulated AI systems.",

};



export default function InsightsPage() {

  return (

    <div className="min-h-screen bg-[var(--bg-base)]">

      <Nav />

      <section className="graphite-band border-b border-[var(--color-rule)] px-6 pb-16 pt-16">

        <div className="mx-auto max-w-3xl">

          <p className="section-label text-[var(--color-accent)]">Insights</p>

          <h1 className="font-display mt-2 text-4xl font-semibold text-[var(--color-graphite-ink)]">

            Clinical AI engineering in public

          </h1>

          <p className="mt-4 text-[var(--color-graphite-ink)] opacity-80">

            Long-form notes on LangGraph orchestration, HIPAA-aware pipelines, and building

            systems that stop instead of hallucinate.

          </p>

          <div className="mt-8 flex flex-wrap gap-3">

            <Link href="/#demo" className="btn-primary inline-block">

              Watch demo

            </Link>

            <a

              href={SITE.linkedinUrl}

              target="_blank"

              rel="noopener noreferrer"

              className="btn-secondary inline-block border-white/20 text-[var(--color-graphite-ink)]"

            >

              Connect on LinkedIn

            </a>

          </div>

        </div>

      </section>



      <div className="mx-auto max-w-3xl px-6 py-16">

        {INSIGHT_TOPICS.map((topic, index) => (

          <article

            key={topic.slug}

            id={topic.slug}

            className={index > 0 ? "mt-20 border-t border-[var(--color-rule)] pt-20" : ""}

          >

            <FadeIn>

              <span className="font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-accent)]">

                Topic {topic.number} · {topic.readMinutes} min read

              </span>

              <h2 className="font-display mt-2 text-2xl font-semibold text-[var(--color-ink)] md:text-3xl">

                {topic.title}

              </h2>

              <p className="mt-2 text-lg text-[var(--color-ink-2)]">{topic.subtitle}</p>

              <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">

                <strong>Angle:</strong> {topic.linkedInAngle}

              </p>

              <div className="mt-4 flex flex-wrap gap-2">

                {topic.tags.map((tag) => (

                  <span

                    key={tag}

                    className="rounded-md border border-[var(--color-rule)] bg-[var(--color-paper-2)] px-3 py-1 text-xs font-medium text-[var(--color-ink-2)]"

                  >

                    #{tag.replace(/\s+/g, "")}

                  </span>

                ))}

              </div>

            </FadeIn>



            <div className="mt-8 space-y-8">

              {topic.sections.map((section) => (

                <FadeIn key={section.heading}>

                  <h3 className="text-lg font-semibold text-[var(--color-ink)]">{section.heading}</h3>

                  <p className="mt-2 leading-relaxed text-[var(--color-ink-2)]">{section.body}</p>

                </FadeIn>

              ))}

            </div>

          </article>

        ))}



        <FadeIn>

          <div className="surface-card mt-20 p-8">

            <h3 className="font-display text-xl font-semibold text-[var(--color-ink)]">

              Continue on the platform

            </h3>

            <p className="mt-2 text-[var(--color-ink-2)]">

              Open the clinical workspace or read the full documentation suite on GitHub.

            </p>

            <div className="mt-4 flex flex-wrap gap-3">

              <a href={SITE.workspaceUrl} className="btn-primary inline-block">

                Open workspace

              </a>

              <a href={SITE.docsUrl} className="btn-secondary inline-block" target="_blank" rel="noopener noreferrer">

                Documentation

              </a>

            </div>

          </div>

        </FadeIn>

      </div>

    </div>

  );

}


