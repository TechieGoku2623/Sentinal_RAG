# Video Walkthrough — Sentinel-RAG

Record a **3–4 minute** product demo for GitHub, LinkedIn, and your landing page.
This guide includes a word-for-word script, pre-flight checklist, and embed instructions.

---

## Before you record (5 minutes)

### 1. Start the stack

Open **three terminals** from `sentinel-rag/`:

```powershell
# Terminal 1 — ingest once (if chroma_db is empty)
python -m src.ingest

# Terminal 2 — API
uvicorn src.api.main:app --reload --port 8000

# Terminal 3 — Next.js portfolio + live workspace
cd landing
npm install
npm run dev
```

Verify:

| Check | URL |
| ----- | --- |
| API health | http://localhost:8000/health |
| Live workspace | http://localhost:3000/workspace |
| Portfolio | http://localhost:3000 |

### 2. Browser setup

- Resolution: **1920×1080** (or 1280×720 minimum)
- Zoom: **100%**
- Close unrelated tabs and notifications
- Use **dark mode** if your OS forces light chrome around the app

### 3. Recording tool (pick one)

| Tool | Best for | Free tier |
| ---- | -------- | --------- |
| [Loom](https://www.loom.com) | GitHub README embed, quick share | Yes |
| OBS Studio | Highest quality, YouTube | Yes |
| Windows Xbox Game Bar | Fast local capture (`Win + G`) | Yes |

**Recommended:** Loom → embed on landing page in under 2 minutes.

---

## Shot list (what to show on screen)

| Time | Scene | Screen |
| ---- | ----- | ------ |
| 0:00–0:20 | Hook + problem | Landing hero OR talking head + logo |
| 0:20–0:50 | Architecture | Scroll to pipeline diagram on `/` |
| 0:50–2:30 | Live demo | `/workspace` — run 3 queries |
| 2:30–3:00 | Safety / flag case | Low-confidence query + red banner |
| 3:00–3:30 | API + repo | `/docs` Swagger + GitHub README |
| 3:30–3:45 | Close + disclaimer | Landing footer |

---

## Word-for-word script (~3:30)

Read naturally — pauses are fine. Demo actions are in **[brackets]**.

---

**[0:00 — Landing page, scroll slowly]**

> Hi — this is Sentinel-RAG, a clinical protocol guardian I built for regulated AI.
>
> The core idea is simple: **healthcare AI cannot afford a confident hallucination.** Standard RAG returns whatever the model says on the first pass. Sentinel-RAG **self-audits every answer** before it ships.

**[0:20 — Scroll to architecture / pipeline section]**

> Under the hood it’s a LangGraph agent: **retrieve** from your own guidelines in local ChromaDB, **generate** with a strict context-only prompt, then **reflect** with deterministic confidence scoring.
>
> If grounding is strong, the answer goes out with citations. If not, the system **re-queries with expanded retrieval** — or **flags for human review** instead of guessing.

**[0:50 — Navigate to http://localhost:3000/workspace]**

> Let’s run it live. This is the production-style Next.js workspace wired to the FastAPI backend — not a mock UI.

**[Click example chip: “What is the first-line treatment for Type 2 diabetes?”]**

> First question: first-line Type 2 diabetes treatment. Watch the pipeline — retrieve, generate, reflect, output.
>
> **[Wait for answer]** High confidence, grounded in the ingested guideline, with source citations and latency metrics.

**[Click: “Can metformin be used with kidney disease?”]**

> Second — metformin in kidney disease. This often triggers a **self-correction retry** when retrieval needs a wider search. Notice the retry count and the confidence arc.

**[Click: “What happens if a patient misses a dose?”]**

> Third — a question **outside the guideline corpus**. This is the safety feature: the system **flags for clinical review** rather than inventing a missed-dose protocol.
>
> **[Point to red flagged banner and confidence arc]** Low confidence, explicit escalation — that’s the product.

**[2:30 — Optional: Streamlit at localhost:8501 for 15 seconds, or skip]**

> For internal prototyping there’s also a Streamlit workspace with patient context and export — but for GitHub and recruiters, this Next.js demo is the primary surface.

**[3:00 — Open http://localhost:8000/docs in new tab]**

> Integrators get a full REST API — query, batch jobs, audit, workspace management — with OpenAPI docs.
>
> **[Switch to GitHub repo]** The repo includes PRD, architecture deep dive, clinical safety philosophy, and a reproducible eval harness — not just a demo app.

**[3:30 — Back to landing footer]**

> Sentinel-RAG is a **research prototype** — not a medical device. It’s built to show how clinical AI should **refuse to be confidently wrong**.
>
> Link in the description: repo, live workspace, and docs. Thanks for watching.

---

## Demo queries (guaranteed story arc)

Use these in order — they exercise **pass**, **retry**, and **flag** paths:

1. `What is the first-line treatment for Type 2 diabetes?` → high confidence
2. `Can metformin be used with kidney disease?` → often retries
3. `What happens if a patient misses a dose?` → flagged / out of scope

Backup if API is slow: use the animated carousel on the landing hero (`/#demo`).

---

## After recording

### Embed on the landing page

1. Upload to [Loom](https://www.loom.com) (or YouTube).
2. Copy the **embed URL** (Loom) or **video ID** (YouTube).
3. Create `landing/.env.local`:

```env
# Loom (preferred for portfolio)
NEXT_PUBLIC_LOOM_EMBED_URL=https://www.loom.com/embed/YOUR_VIDEO_ID
NEXT_PUBLIC_LOOM_SHARE_URL=https://www.loom.com/share/YOUR_VIDEO_ID

# Or YouTube (alternative)
NEXT_PUBLIC_YOUTUBE_EMBED_ID=dQw4j9KnQXI
```

4. Restart `npm run dev` — the **Video walkthrough** section on the homepage will show your recording.

### Add to GitHub README

After Loom/YouTube is live, add near the top of `README.md`:

```markdown
[![Watch the demo](https://img.shields.io/badge/▶_Watch-3_min_walkthrough-0EC788?style=for-the-badge)](YOUR_LOOM_OR_YOUTUBE_URL)
```

### LinkedIn post template

> Built Sentinel-RAG — clinical AI that knows when to say “I don’t know.”
>
> LangGraph · self-reflective RAG · deterministic confidence · human escalation
>
> 3-min walkthrough: [link]
> Code: [GitHub link]
>
> #ClinicalAI #LangGraph #RAG #HealthTech #AIEngineering

---

## Troubleshooting while recording

| Issue | Fix |
| ----- | --- |
| “API offline” on workspace | Start `uvicorn src.api.main:app --port 8000` |
| Empty knowledge base warning | Run `python -m src.ingest` |
| Slow first query | Normal — Groq cold start; mention it on camera or pre-warm with one query |
| 401 from API | Unset `SENTINEL_API_KEY` locally or set matching key in `landing/.env.local` |

---

## Optional: animated GIF for README (no video)

```powershell
python scripts/generate_demo_gif.py
# Output: docs/demo.gif — copied to landing/public/demo.gif
```

Use this as a README preview until the Loom recording is ready.
