# Sentinel-RAG Design System — Master

> **Authority order:** `sentinel-rag/design.md` (Hallmark Veridian) wins for brand tokens and typography.
> This file adds UI UX Pro Max rules for components, accessibility, and page structure.
> For a specific page, check `design-system/pages/[page].md` first — page rules override this file.

**Project:** Sentinel-RAG · Clinical Protocol Guardian  
**Industry:** Healthcare / clinical SaaS  
**Stack:** Next.js 15 + Tailwind (landing) · Streamlit workbench (app)

---

## Locked brand (from `design.md` — do not override)

| Token | Value |
|-------|--------|
| Theme | Veridian · modern-minimal |
| Display font | Space Grotesk 600 |
| Body font | Inter 400/500 |
| Mono | JetBrains Mono |
| Accent | `--color-accent` oklch veridian teal |
| Paper / ink | `--color-paper`, `--color-ink` via `tokens.css` |

**Macrostructures**
- Landing: Stat-Led hero + asymmetric validation panel
- Streamlit app: Workbench (sidebar + workspace) — no marketing chrome
- Docs: Long-document rhythm inside tokens

---

## UI UX Pro Max — healthcare pattern

**Pattern:** Social proof + trust (eval metrics, audit trail, safety layers)  
**Style:** Accessible & Ethical — WCAG AA minimum, 16px+ body, visible focus rings  
**Section order (landing):** Hero → pipeline / proof → features → pricing → CTA

### Component rules (both stacks)

- SVG icons only (Lucide / Heroicons) — no emoji icons
- `cursor-pointer` on all click targets
- Transitions 150–300ms — no `transition-all`
- Hover must not shift layout (no scale on cards in clinical UI)
- `prefers-reduced-motion`: opacity-only, ≤150ms
- Responsive breakpoints: 375, 768, 1024, 1440
- Honest metrics only (from `data/eval/eval_results.json`)

### Pre-delivery checklist

- [ ] Safety disclaimer before clinical actions (Streamlit)
- [ ] Contrast ≥ 4.5:1 on body text
- [ ] Focus visible on keyboard nav
- [ ] No AI purple/pink gradients
- [ ] Hallmark stamp in CSS artifacts

---

## 21st.dev Magic — where generated components go

| Surface | Path | Notes |
|---------|------|--------|
| Landing UI | `landing/components/` | Map to Cobalt tokens in `tokens.css` |
| shadcn primitives | `landing/components/ui/` | Install via `npx shadcn@latest add <component>` |
| Streamlit | `ui/theme.py`, `ui/command_center.py` | Manual port — Magic is React-only |

After Magic generates a component: replace hardcoded hex with `var(--color-*)` from `tokens.css`.

---

## Commands

```powershell
# UI UX Pro Max — refresh recommendations
python .cursor/skills/ui-ux-pro-max/scripts/search.py "healthcare clinical SaaS dashboard" --design-system -p "Sentinel-RAG"

# Stack-specific (landing)
python .cursor/skills/ui-ux-pro-max/scripts/search.py "dashboard stat cards" --stack nextjs

# Hallmark slop audit
# Streamlit → Build studio → audit
```
