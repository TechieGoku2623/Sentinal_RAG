"use client";

import { FadeIn, StaggerContainer, StaggerItem } from "./FadeIn";
import { SITE } from "@/lib/site";

const PLANS = [
  {
    id: "starter",
    name: "Starter",
    price: "Free",
    period: "forever",
    description: "For individual clinicians exploring protocol validation.",
    features: [
      "500 validations / month",
      "10 guideline documents",
      "3 team seats",
      "Audit trail export",
      "Clinical recollection",
    ],
    cta: "Start free",
    href: SITE.workspaceUrl,
    highlighted: false,
  },
  {
    id: "professional",
    name: "Professional",
    price: "$299",
    period: "/ month",
    description: "For clinics and quality teams running daily protocol checks.",
    features: [
      "5,000 validations / month",
      "100 guideline documents",
      "15 team seats",
      "REST API access",
      "PubMed & OpenFDA ingest",
      "Priority support",
    ],
    cta: "Start trial",
    href: SITE.workspaceUrl,
    highlighted: true,
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For health systems requiring SSO, BAA, and dedicated infrastructure.",
    features: [
      "Unlimited validations",
      "Unlimited documents",
      "SSO / SAML",
      "Per-tenant vector isolation",
      "HIPAA-ready deployment",
      "Dedicated success manager",
    ],
    cta: "Contact sales",
    href: "mailto:sales@sentinel-rag.dev",
    highlighted: false,
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="bg-white px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <FadeIn>
          <p className="section-label">Pricing</p>
          <h2 className="mt-2 text-3xl font-bold text-navy md:text-4xl">
            SaaS plans that scale with your clinical team
          </h2>
          <p className="mt-4 max-w-2xl text-slate-muted">
            Metered by validation queries. Every tier includes the five-layer safety pipeline,
            audit logging, and human-in-the-loop escalation.
          </p>
        </FadeIn>

        <StaggerContainer className="mt-12 grid gap-6 lg:grid-cols-3">
          {PLANS.map((plan) => (
            <StaggerItem key={plan.id}>
              <div
                className={`flex h-full flex-col rounded-xl border p-8 ${
                  plan.highlighted
                    ? "border-brand bg-navy text-white shadow-glow"
                    : "border-slate-line bg-[#F4F6F9] text-navy"
                }`}
              >
                <p
                  className={`text-xs font-semibold uppercase tracking-widest ${
                    plan.highlighted ? "text-brand-light" : "text-brand"
                  }`}
                >
                  {plan.name}
                </p>
                <p className="mt-4 flex items-baseline gap-1">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  {plan.period && (
                    <span className={plan.highlighted ? "text-slate-300" : "text-slate-muted"}>
                      {plan.period}
                    </span>
                  )}
                </p>
                <p
                  className={`mt-3 text-sm ${plan.highlighted ? "text-slate-300" : "text-slate-muted"}`}
                >
                  {plan.description}
                </p>
                <ul className="mt-6 flex-1 space-y-2.5 text-sm">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <span className={plan.highlighted ? "text-brand-light" : "text-brand"}>✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <a
                  href={plan.href}
                  className={`mt-8 block rounded-lg py-2.5 text-center text-sm font-semibold transition-colors ${
                    plan.highlighted
                      ? "bg-brand text-white hover:bg-brand-light"
                      : "bg-navy text-white hover:bg-navy-mid"
                  }`}
                >
                  {plan.cta}
                </a>
              </div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </section>
  );
}
