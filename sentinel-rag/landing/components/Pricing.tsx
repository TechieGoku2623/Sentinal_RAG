"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { FadeIn, StaggerContainer, StaggerItem } from "./FadeIn";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
] as const;

export function Pricing() {
  return (
    <section id="pricing" className="bg-[var(--color-paper)] px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <FadeIn>
          <p className="section-label">Pricing</p>
          <h2 className="font-display mt-2 text-3xl font-semibold text-[var(--color-ink)] md:text-4xl">
            SaaS plans that scale with your clinical team
          </h2>
          <p className="mt-4 max-w-2xl text-[var(--color-ink-2)]">
            Metered by validation queries. Every tier includes the five-layer safety pipeline,
            audit logging, and human-in-the-loop escalation.
          </p>
        </FadeIn>

        <StaggerContainer className="mt-12 grid gap-6 lg:grid-cols-3">
          {PLANS.map((plan) => (
            <StaggerItem key={plan.id}>
              <Card
                className={
                  plan.highlighted
                    ? "relative h-full border-[var(--color-accent)] bg-[var(--color-graphite)] text-[var(--color-graphite-ink)] ring-2 ring-[var(--color-accent)]/30"
                    : "h-full border-2 border-[var(--color-rule)] bg-white shadow-sm"
                }
              >
                {plan.highlighted && (
                  <Badge className="absolute -top-2.5 left-4 bg-[var(--color-accent)] text-[var(--color-accent-ink)]">
                    Most popular
                  </Badge>
                )}
                <CardHeader className="pt-8">
                  <CardTitle
                    className={
                      plan.highlighted
                        ? "font-mono text-xs uppercase tracking-widest text-[var(--color-accent)]"
                        : "font-mono text-xs uppercase tracking-widest text-[var(--color-accent)]"
                    }
                  >
                    {plan.name}
                  </CardTitle>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="font-display text-4xl font-semibold tabular-nums">
                      {plan.price}
                    </span>
                    {plan.period && (
                      <span
                        className={
                          plan.highlighted ? "text-[var(--color-graphite-ink)]/70" : "text-[var(--color-ink-2)]"
                        }
                      >
                        {plan.period}
                      </span>
                    )}
                  </div>
                  <CardDescription
                    className={
                      plan.highlighted ? "text-[var(--color-graphite-ink)]/80" : "text-[var(--color-ink-2)]"
                    }
                  >
                    {plan.description}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2.5 text-sm">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-2">
                        <Check
                          className="mt-0.5 size-4 shrink-0 text-[var(--color-accent)]"
                          aria-hidden
                        />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
                <CardFooter>
                  <Button
                    render={<Link href={plan.href} />}
                    variant={plan.highlighted ? "default" : "outline"}
                    size="lg"
                    className="w-full cursor-pointer border-2 border-[var(--color-rule)]"
                  >
                    {plan.cta}
                  </Button>
                </CardFooter>
              </Card>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </section>
  );
}
