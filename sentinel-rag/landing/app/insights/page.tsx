import type { Metadata } from "next";
import Link from "next/link";
import { INSIGHT_TOPICS } from "@/content/insights";
import { NavMotion } from "@/components/NavMotion";
import { FadeIn } from "@/components/FadeIn";
import { SITE } from "@/lib/site";

export const metadata: Metadata = {
  title: "Insights · Sentinel-RAG",
  description:
    "LangGraph, HIPAA health data pipelines, and clinical AI safety — thought leadership for AI engineering roles.",
  keywords: [
    "LangGraph",
    "LangChain",
    "Clinical AI",
    "HIPAA",
    "Healthcare AI",
    "RAG",
    "AI Safety",
  ],
};

export default function InsightsPage() {
  return (
    <div className="min-h-screen">
      <NavMotion />
      <div className="gradient-hero px-6 pb-16 pt-24 text-white">
        <div className="mx-auto max-w-3xl text-center">
          <p className="section-label text-brand-light">Insights</p>
          <h1 className="mt-2 text-4xl font-bold">Clinical AI engineering in public</h1>
          <p className="mt-4 text-slate-300">
            Long-form notes + LinkedIn-ready angles on LangGraph, HIPAA pipelines, and
            building AI that stops instead of hallucinates.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link
              href="/#demo"
              className="rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white"
            >
              Watch demo
            </Link>
            <a
              href={SITE.linkedinUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="glass rounded-xl px-5 py-2.5 text-sm font-semibold"
            >
              Connect on LinkedIn
            </a>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-3xl px-6 py-16">
        {INSIGHT_TOPICS.map((topic, index) => (
          <article
            key={topic.slug}
            id={topic.slug}
            className={index > 0 ? "mt-20 border-t border-slate-200 pt-20" : ""}
          >
            <FadeIn>
              <span className="text-xs font-semibold uppercase tracking-widest text-brand">
                Topic {topic.number} · {topic.readMinutes} min read
              </span>
              <h2 className="mt-2 text-2xl font-bold text-navy md:text-3xl">{topic.title}</h2>
              <p className="mt-2 text-lg text-slate-muted">{topic.subtitle}</p>
              <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <strong>LinkedIn angle:</strong> {topic.linkedInAngle}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {topic.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600"
                  >
                    #{tag.replace(/\s+/g, "")}
                  </span>
                ))}
              </div>
            </FadeIn>

            <div className="mt-8 space-y-8">
              {topic.sections.map((section) => (
                <FadeIn key={section.heading}>
                  <h3 className="text-lg font-semibold text-navy">{section.heading}</h3>
                  <p className="mt-2 leading-relaxed text-slate-700">{section.body}</p>
                </FadeIn>
              ))}
            </div>
          </article>
        ))}

        <FadeIn>
          <div className="mt-20 rounded-2xl bg-navy p-8 text-white">
            <h3 className="text-xl font-semibold">Post on LinkedIn this week</h3>
            <p className="mt-2 text-slate-300">
              Use one topic per post. Attach the Loom demo + link to this repo. Recruiters
              searching LangGraph and clinical AI will find you.
            </p>
            <a
              href="../../docs/LINKEDIN_PLAYBOOK.md"
              className="mt-4 inline-block text-brand-light hover:underline"
            >
              → Copy posts from LINKEDIN_PLAYBOOK.md
            </a>
          </div>
        </FadeIn>
      </div>
    </div>
  );
}
