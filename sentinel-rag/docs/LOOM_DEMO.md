# Loom screen-recording demo — Sentinel-RAG

Record a **2–3 minute** Loom walkthrough and embed it on the landing page + LinkedIn posts. This is the fastest way to convert recruiter profile views into inbound AI role conversations.

---

## Before you record

1. Start the app:
   ```bash
   pip install -r requirements.txt
   python -m src.ingest
   streamlit run app.py
   ```
2. Open [http://localhost:8501](http://localhost:8501) at **1280×720** or full screen.
3. Install [Loom](https://www.loom.com) (free tier is fine).
4. Close unrelated tabs; use light mode if possible.

---

## Shot list (2 min 30 sec)

| Time | What to show | What to say |
|------|----------------|-------------|
| **0:00–0:15** | Landing page or Streamlit hero | "I'm Devasai — I built Sentinel-RAG because clinical AI shouldn't hallucinate confidently. It should stop and escalate." |
| **0:15–0:45** | **Protocol validation** tab — run sample query: *"What is first-line therapy for type 2 diabetes?"* | "Five-layer pipeline: retrieve from local ChromaDB, generate with strict context-only prompts, deterministic confidence score, second-model validation, then flag or release." |
| **0:45–1:15** | Results panel — confidence ring, metrics, clinical answer (not raw HTML) | "Notice the grounding score and cross-validation verdict. If it's not supported, we flag for clinician review — that's a success, not a bug." |
| **1:15–1:45** | **Clinical recollection** tab — study queue, reveal guideline | "Trainees and experienced clinicians get spaced repetition and recall from past validations — not just one-off chat." |
| **1:45–2:05** | **Admin** or sidebar — Chroma counts, optional PubMed ingest | "End-to-end platform: FastAPI, SQLite audit log, external evidence ingest. Built for regulated workflows." |
| **2:05–2:30** | GitHub repo + architecture diagram in README | "Open source LangGraph agent. Link in description. If you're hiring for LangGraph or clinical AI — let's connect." |

---

## Recording tips

- **Speak to hiring managers**, not clinicians — emphasize architecture decisions.
- **Show one flagged example** if you have time (query outside diabetes corpus).
- **Don't read code** — show behavior.
- End with: *"Repo and docs in the description. Happy to walk through the LangGraph state machine on a call."*

---

## After recording

1. In Loom, copy the **Embed** link (`https://www.loom.com/embed/...`).
2. Create `landing/.env.local`:
   ```env
   NEXT_PUBLIC_LOOM_EMBED_URL=https://www.loom.com/embed/YOUR_VIDEO_ID
   NEXT_PUBLIC_LOOM_SHARE_URL=https://www.loom.com/share/YOUR_VIDEO_ID
   ```
3. Restart the landing dev server:
   ```bash
   cd landing && npm run dev
   ```
4. Verify embed at [http://localhost:3000/#demo](http://localhost:3000/#demo).

---

## LinkedIn post template (attach Loom)

```
I built Sentinel-RAG to stop — not hallucinate.

Clinical RAG shouldn't optimize for fluent wrong answers.
It should score grounding, cross-validate, and escalate.

2-min demo 👇
[LOOM LINK]

Open source LangGraph agent:
https://github.com/devasai/sentinel-rag

#LangGraph #ClinicalAI #RAG #AIEngineering #HealthcareAI

Open to AI Engineer / ML Engineer roles — DMs welcome.
```

---

## Thumbnail suggestion

Loom auto-thumbnail is fine. Optionally upload a frame showing the **confidence ring at 72%** with the title overlay: *"Sentinel-RAG — stops instead of hallucinates"*.
