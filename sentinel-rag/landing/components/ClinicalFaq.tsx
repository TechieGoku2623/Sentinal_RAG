"use client";

import { ChevronDown } from "lucide-react";
import { FadeIn } from "./FadeIn";

const FAQ = [
  {
    q: "Is Sentinel-RAG a medical device?",
    a: "No. It is a research prototype for guideline-grounded protocol validation. Outputs require clinician review and must not be used for direct patient care without institutional approval.",
  },
  {
    q: "Where does patient or PHI data go?",
    a: "By default, guidelines and queries stay local — ChromaDB on disk, SQLite audit store, optional Groq API for inference. Deploy on-prem or VPC for stricter isolation; no multi-tenant vector isolation in the prototype tier.",
  },
  {
    q: "What happens when confidence is low?",
    a: "The self-reflective loop flags the answer, surfaces the validation verdict, and logs the interaction for audit. Uncertainty is treated as a safety success, not hidden.",
  },
  {
    q: "Can we self-host without Groq?",
    a: "The architecture supports open-weights LLMs and CPU embeddings. Groq is the default demo path; swap the inference backend in config for air-gapped deployments.",
  },
  {
    q: "How are SaaS quotas enforced?",
    a: "Each workspace plan meters validation queries per month (Starter 500, Professional 5,000). Usage is tracked in SQLite and visible in the Command Center.",
  },
] as const;

export function ClinicalFaq() {
  return (
    <section id="faq" className="mx-auto max-w-3xl px-6 py-20">
      <FadeIn>
        <p className="section-label">Clinical safety & deployment</p>
        <h2 className="font-display mt-2 text-3xl font-semibold text-[var(--color-ink)] md:text-4xl">
          Questions compliance teams ask first
        </h2>
        <p className="mt-4 text-[var(--color-ink-2)]">
          Accessible answers — expand any item. Full policy docs ship in{" "}
          <code className="rounded bg-[var(--color-paper-2)] px-1.5 py-0.5 text-sm">
            docs/CLINICAL_SAFETY.md
          </code>
          .
        </p>
      </FadeIn>

      <div className="mt-10 space-y-3">
        {FAQ.map((item, i) => (
          <FadeIn key={item.q} delay={i * 0.04}>
            <details className="surface-card group overflow-hidden">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 font-medium text-[var(--color-ink)] transition-colors duration-200 hover:text-[var(--color-accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] [&::-webkit-details-marker]:hidden">
                <span>{item.q}</span>
                <ChevronDown
                  className="size-4 shrink-0 text-[var(--color-ink-2)] transition-transform duration-200 group-open:rotate-180"
                  aria-hidden
                />
              </summary>
              <div className="border-t border-[var(--color-rule)] px-5 pb-4 pt-3 text-sm leading-relaxed text-[var(--color-ink-2)]">
                {item.a}
              </div>
            </details>
          </FadeIn>
        ))}
      </div>
    </section>
  );
}
