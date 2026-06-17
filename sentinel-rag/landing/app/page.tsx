import Image from "next/image";
import { Pricing } from "@/components/Pricing";
import { LoomDemo } from "@/components/LoomDemo";
import { ThoughtLeadership } from "@/components/ThoughtLeadership";
import { AnimatedMetric } from "@/components/AnimatedCounter";
import { FadeIn, StaggerContainer, StaggerItem } from "@/components/FadeIn";
import { HeroMotion } from "@/components/HeroMotion";
import { NavMotion } from "@/components/NavMotion";
import { PipelineMotion } from "@/components/PipelineMotion";

const METRICS = {
  questions: 50,
  keywordMatch: "65%",
  keywordMatchNum: 65,
  avgConfidence: "53%",
  avgConfidenceNum: 53,
  flagRate: "100%",
  avgLatency: "25978ms",
  validationAgreement: "46%",
  validationAgreementNum: 46,
  note: "Measured by scripts/run_eval.py on 2026-06-10 — diabetes-only corpus; unsupported categories correctly flagged.",
};

const PILLARS = [
  {
    title: "Grounded answers",
    body: "Strict context-only generation with dated source citations and provenance metadata.",
    icon: "◆",
  },
  {
    title: "Self-audit loop",
    body: "Deterministic four-factor confidence scoring before any answer reaches a clinician.",
    icon: "◎",
  },
  {
    title: "Human escalation",
    body: "Low-confidence outputs are flagged for review — uncertainty is a safety success.",
    icon: "⚑",
  },
  {
    title: "Privacy-first",
    body: "Local ChromaDB, CPU embeddings, and a self-hostable open-weights LLM path.",
    icon: "⬡",
  },
];

const DOCS = [
  { href: "../docs/PRD.md", label: "Product requirements" },
  { href: "../docs/TRD.md", label: "Technical requirements" },
  { href: "../docs/APP_FLOW.md", label: "Application flow" },
  { href: "../docs/ARCHITECTURE.md", label: "Architecture" },
  { href: "../docs/CLINICAL_SAFETY.md", label: "Clinical safety" },
];

export default function HomePage() {
  return (
    <div className="min-h-screen overflow-x-hidden">
      <NavMotion />
      <HeroMotion />
      <LoomDemo />
      <Pricing />

      <section className="mx-auto max-w-6xl px-6 py-20">
        <FadeIn>
          <p className="section-label">Why Sentinel-RAG</p>
          <h2 className="mt-2 text-3xl font-bold text-navy md:text-4xl">
            Built for clinical trust, not chatbot fluency
          </h2>
        </FadeIn>
        <StaggerContainer className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((p) => (
            <StaggerItem key={p.title}>
              <div className="group h-full pro-card p-6">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-brand-pale text-lg text-brand">
                  {p.icon}
                </span>
                <h3 className="mt-4 font-semibold text-navy">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-muted">{p.body}</p>
              </div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </section>

      <section id="platform" className="bg-white px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <FadeIn>
            <p className="section-label">Safety architecture</p>
            <h2 className="mt-2 text-3xl font-bold text-navy md:text-4xl">
              Five-layer validation pipeline
            </h2>
            <p className="mt-4 max-w-2xl text-slate-muted">
              A LangGraph state machine replaces linear RAG with a cycle that can
              re-retrieve, self-correct, or escalate — mirroring how careful clinicians
              reason under uncertainty.
            </p>
          </FadeIn>
          <PipelineMotion />
        </div>
      </section>

      <section id="metrics" className="mx-auto max-w-6xl px-6 py-20">
        <FadeIn>
          <p className="section-label">Reproducible evaluation</p>
          <h2 className="mt-2 text-3xl font-bold text-navy md:text-4xl">Measured, not marketed</h2>
          <p className="mt-4 max-w-2xl text-slate-muted">
            Metrics from{" "}
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-sm">scripts/run_eval.py</code>{" "}
            over a 50-question dataset — not hand-picked demos.
          </p>
        </FadeIn>
        <StaggerContainer className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StaggerItem>
            <AnimatedMetric label="Questions evaluated" display="50" numericValue={METRICS.questions} />
          </StaggerItem>
          <StaggerItem>
            <AnimatedMetric
              label="Keyword match rate"
              display={METRICS.keywordMatch}
              numericValue={METRICS.keywordMatchNum}
              suffix="%"
            />
          </StaggerItem>
          <StaggerItem>
            <AnimatedMetric
              label="Average confidence"
              display={METRICS.avgConfidence}
              numericValue={METRICS.avgConfidenceNum}
              suffix="%"
            />
          </StaggerItem>
          <StaggerItem>
            <AnimatedMetric label="Flag rate" display={METRICS.flagRate} />
          </StaggerItem>
          <StaggerItem>
            <AnimatedMetric label="Avg response time" display={METRICS.avgLatency} />
          </StaggerItem>
          <StaggerItem>
            <AnimatedMetric
              label="Validation agreement"
              display={METRICS.validationAgreement}
              numericValue={METRICS.validationAgreementNum}
              suffix="%"
            />
          </StaggerItem>
        </StaggerContainer>
        <FadeIn delay={0.2}>
          <p className="mt-6 text-sm text-amber-700">{METRICS.note}</p>
        </FadeIn>
      </section>

      <ThoughtLeadership />

      <section id="docs" className="bg-navy px-6 py-20 text-white">
        <div className="mx-auto max-w-6xl">
          <div className="grid gap-12 lg:grid-cols-2">
            <FadeIn direction="left">
              <p className="section-label text-brand-light">Documentation</p>
              <h2 className="mt-2 text-3xl font-bold">Enterprise documentation suite</h2>
              <p className="mt-4 text-slate-300">
                PRD, TRD, application flows, architecture deep dive, and clinical
                safety philosophy — ready for product, engineering, and compliance review.
              </p>
              <ul className="mt-8 space-y-3">
                {DOCS.map((d, i) => (
                  <li key={d.href}>
                    <a
                      href={d.href}
                      className="group inline-flex items-center gap-2 text-brand-light transition-colors hover:text-white"
                      style={{ animationDelay: `${i * 0.05}s` }}
                    >
                      <span className="transition-transform duration-200 group-hover:translate-x-1">→</span>
                      {d.label}
                    </a>
                  </li>
                ))}
              </ul>
            </FadeIn>
            <FadeIn direction="right" delay={0.1}>
              <div className="rounded-xl border border-white/10 bg-white/5 p-8">
                <h3 className="text-xl font-semibold">Run the clinical workspace</h3>
                <pre className="mt-4 overflow-x-auto rounded-lg bg-navy-dark p-4 font-mono text-sm text-brand-light">
{`pip install -r requirements.txt
python -m src.ingest
streamlit run app.py`}
                </pre>
                <p className="mt-4 text-sm text-slate-400">
                  Investor demo:{" "}
                  <code className="text-brand-light">cd landing && npm run dev</code>
                </p>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      <footer className="border-t border-slate-200 bg-slate-50 px-6 py-10">
        <FadeIn>
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-sm text-slate-muted md:flex-row">
            <div className="flex items-center gap-3">
              <Image src="/logo.png" alt="" width={28} height={28} className="rounded-[6px]" />
              <span>Sentinel-RAG · Research prototype — not a medical device</span>
            </div>
            <p>
              Built by{" "}
              <a
                href="https://www.linkedin.com/in/devasai-pranatheswar"
                className="text-brand transition-colors hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Devasai Pranatheswar
              </a>
            </p>
          </div>
        </FadeIn>
      </footer>
    </div>
  );
}
