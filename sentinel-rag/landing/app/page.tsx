import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { FeatureGrid } from "@/components/FeatureGrid";
import { ArchitectureDiagram } from "@/components/ArchitectureDiagram";
import { EvalMetrics } from "@/components/EvalMetrics";
import { Footer } from "@/components/Footer";
import { FadeIn } from "@/components/FadeIn";
import { SITE } from "@/lib/site";

const DOCS = [
  { href: `${SITE.docsUrl}/README.md`, label: "Documentation index" },
  { href: `${SITE.docsUrl}/PRD.md`, label: "Product requirements" },
  { href: `${SITE.docsUrl}/TRD.md`, label: "Technical requirements" },
  { href: `${SITE.docsUrl}/CLINICAL_SAFETY.md`, label: "Clinical safety" },
  { href: `${SITE.docsUrl}/ARCHITECTURE.md`, label: "Architecture" },
];

export default function HomePage() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-[var(--bg-base)]">
      <Nav />
      <Hero />
      <FeatureGrid />
      <ArchitectureDiagram />
      <EvalMetrics />

      <section id="docs" className="graphite-band px-10 py-24">
        <div className="mx-auto max-w-6xl">
          <div className="grid gap-12 lg:grid-cols-2">
            <FadeIn direction="left">
              <p className="section-label">Documentation</p>
              <h2 className="mt-2 font-display text-3xl font-bold text-[var(--text-primary)]">
                Enterprise documentation suite
              </h2>
              <p className="mt-4 text-[var(--text-secondary)]">
                PRD, TRD, application flows, architecture deep dive, and clinical safety
                philosophy — ready for product, engineering, and compliance review.
              </p>
              <ul className="mt-8 space-y-3">
                {DOCS.map((d) => (
                  <li key={d.href}>
                    <a
                      href={d.href}
                      className="group inline-flex items-center gap-2 text-[var(--teal)] no-underline transition-colors hover:text-[var(--text-primary)]"
                    >
                      <span className="transition-transform duration-200 group-hover:translate-x-1">
                        →
                      </span>
                      {d.label}
                    </a>
                  </li>
                ))}
              </ul>
            </FadeIn>
            <FadeIn direction="right" delay={0.1}>
              <div className="rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-elevated)] p-8">
                <h3 className="text-xl font-semibold text-[var(--text-primary)]">
                  Run the live demo (recommended for GitHub)
                </h3>
                <pre className="mt-4 overflow-x-auto rounded-lg bg-[var(--bg-base)] p-4 font-mono text-sm text-[var(--text-secondary)]">
{`uvicorn src.api.main:app --reload --port 8000
cd landing && npm install && npm run dev
# Open http://localhost:3000/workspace`}
                </pre>
                <p className="mt-4 text-sm text-[var(--text-muted)]">
                  Internal Streamlit workspace:{" "}
                  <code className="text-[var(--teal)]">streamlit run app.py</code>
                </p>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
