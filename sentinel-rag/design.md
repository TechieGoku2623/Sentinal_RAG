# Design — Sentinel-RAG · Clinical Protocol Guardian

Locked design system for this app. Every Hallmark run reads this file before emitting code.

## Genre
modern-minimal (Veridian register — calm clinical teal, accessible healthcare)

## Macrostructure family
- Marketing / landing: **Stat-Led** — hero metric + qualifier headline + asymmetric code/validation panel
- Streamlit app: **Workbench** — tool-first sidebar + primary workspace
- Content / docs links: **Long Document** rhythm within system tokens

## Theme — Veridian (clinical teal)
- `--color-paper`   oklch(99% 0.006 185)
- `--color-paper-2` oklch(96% 0.014 188)
- `--color-ink`     oklch(27% 0.045 200)
- `--color-ink-2`   oklch(40% 0.035 195)
- `--color-rule`    oklch(72% 0.04 190)
- `--color-accent`  oklch(50% 0.13 192)
- `--color-accent-ink` oklch(99% 0.01 185)
- `--color-focus`   oklch(50% 0.13 192)
- `--color-graphite` oklch(24% 0.04 200)
- `--color-success` oklch(48% 0.12 155)

## Typography
- Display: Space Grotesk, weight 600, style normal
- Body: Inter, weight 400/500 (body only — never hero display)
- Mono: JetBrains Mono, weight 400/500 — labels, code, audit timestamps
- Display tracking: -0.03em on h1
- Type scale anchor: clamp(2.25rem, 5vw, 3.25rem) for stat figures

## Spacing
4-point named scale via `tokens.css`. Use `var(--space-*)` only.

## Motion
- Easings: cubic-bezier(0.16, 1, 0.3, 1) as `--ease-out`
- Reveal: fade + 10px rise, one-shot
- Reduced-motion: opacity-only, ≤ 150ms

## Microinteractions stance
- Silent success for visible validation outcomes
- Hover delay 800ms on tooltips; focus delay 0ms
- No `transition-all`; no uniform hover-scale

## CTA voice
- Primary: solid teal fill, 6px radius, verb + destination ("Open clinical workspace")
- Secondary: hairline border, typographic weight only

## Per-page allowances
- Landing MAY use one graphite band (quickstart / API mock)
- Streamlit app MUST NOT use marketing enrichment — function carries the page

## What pages MUST share
- Wordmark + teal accent ≤ 5% viewport
- Space Grotesk display + Inter body + JetBrains labels
- Safety disclaimer before clinical actions
- Honest metrics only (from eval harness — no invented conversion stats)

## Hallmark stamp
Every CSS artifact: `/* Hallmark · genre: modern-minimal · theme: veridian · macrostructure: <name> · design-system: design.md · designed-as-app */`
