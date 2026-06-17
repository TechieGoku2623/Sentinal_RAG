# LinkedIn playbook — inbound AI roles

Three copy-ready posts optimized for recruiter search: **LangGraph**, **HIPAA**, **Clinical AI**, **RAG**, **Healthcare**.

**Posting cadence:** one topic per week. Attach the [Loom demo](LOOM_DEMO.md) + GitHub link every time.

**Profile checklist before posting:**
- Headline mentions: `LangGraph · Clinical AI · RAG · Python`
- Featured: Loom demo, GitHub repo, this landing page
- About section: link to `/insights` on your deployed landing site

---

## Topic 1 — Why I built Sentinel-RAG to stop — not hallucinate

**Best day to post:** Tuesday or Wednesday, 8–10 AM local

```
The most dangerous output in healthcare isn't a quiet mistake.

It's a confident hallucination delivered like a protocol.

That's why I built Sentinel-RAG — a clinical RAG system designed to STOP when grounding is insufficient, not perform certainty.

What it does differently:
→ LangGraph cyclic agent (retrieve → generate → reflect → retry or flag)
→ Deterministic confidence scoring before any answer ships
→ Independent second-model cross-validation
→ Human escalation when evidence is weak — treated as success, not failure

This isn't a chatbot demo.
It's the architecture I'd want reviewing a protocol question in a regulated environment.

🎥 2-min walkthrough: [YOUR LOOM LINK]
📂 Open source: https://github.com/devasai/sentinel-rag

If you're building clinical AI or hiring engineers who design for refusal + audit trails — I'd love to connect.

#LangGraph #ClinicalAI #RAG #AISafety #HealthcareAI #LLM #Python #AIEngineering

---
Open to AI Engineer / ML Engineer / Applied Scientist roles (remote-friendly).
```

**First comment (post immediately):**
```
Architecture deep dive: LangGraph state machine + eval harness in the repo.
Docs: PRD, TRD, END_TO_END platform guide.
Happy to whiteboard the reflection loop on a call.
```

---

## Topic 2 — What 4 months of HIPAA health data pipelines taught me about clinical AI

**Best day to post:** Thursday, 8–10 AM local

```
Four months working HIPAA health data pipelines changed how I build clinical AI.

Lesson 1: Pipelines before prompts
If you can't trace a chunk to source, ingestion time, and access policy — you're not ready for clinical workflows.

Lesson 2: Local-first is compliance-aware engineering
Sentinel-RAG indexes guidelines in local ChromaDB with CPU embeddings. Dev uses Groq; production path stays open for on-prem Llama via vLLM/Ollama.

Lesson 3: Auditability beats accuracy theater
Every validation run logs to SQLite + CSV reward features. Document registry, audit events, API layer — governance is a feature.

Lesson 4: Different surfaces for different risk
Validation mode for protocol review.
Recollection mode for trainee/experienced spaced repetition.
Explicit research disclaimer — not a medical device.

HIPAA didn't teach me to fear AI in healthcare.
It taught me where the real engineering starts.

🎥 Demo: [YOUR LOOM LINK]
📂 Code: https://github.com/devasai/sentinel-rag

#HIPAA #HealthData #DataEngineering #ClinicalAI #LangGraph #Healthcare #Compliance #AIEngineering

---
Looking for roles where regulated data + production AI intersect.
```

**First comment:**
```
Built end-to-end: Streamlit UI, FastAPI, PubMed/OpenFDA ingest, clinical recollection module.
Ask me about BAA-aware architecture choices in the README.
```

---

## Topic 3 — LangGraph vs LangChain — when to use each

**Best day to post:** Tuesday, 8–10 AM local (2 weeks after Topic 1)

```
LangChain vs LangGraph — when to use each (from production clinical AI work):

Use LangChain when:
✓ Linear flow: retrieve → prompt → parse → return
✓ Single-pass RAG, summarization, extraction
✓ You need speed to ship, minimal branching

Use LangGraph when:
✓ Retries, loops, or policy-driven routing
✓ Human-in-the-loop escalation
✓ Persistent agent state across turns
✓ Safety gates that can re-retrieve or refuse to answer

Sentinel-RAG is my public LangGraph case study:
→ Conditional edges after a reflection node
→ Bounded re-retrieval (max 2 loops)
→ Output node with audit metadata
→ Same core agent behind Streamlit + FastAPI

If your job description says "LangGraph" — this repo is the shape of work I deliver.

🎥 Walkthrough: [YOUR LOOM LINK]
📂 https://github.com/devasai/sentinel-rag

#LangGraph #LangChain #AIAgents #LLM #Python #MachineLearning #AIEngineering #RAG

---
Open to LangGraph / agent engineering roles — let's connect.
```

**First comment:**
```
Graph code: src/agent.py
Comparison table in landing/insights Topic 3.
DM me if you want a 15-min architecture review.
```

---

## 30-day posting calendar

| Week | Post | CTA |
|------|------|-----|
| 1 | Topic 1 (stop vs hallucinate) | Loom + GitHub |
| 2 | Topic 3 (LangGraph vs LangChain) | Loom + invite DMs from LangGraph recruiters |
| 3 | Topic 2 (HIPAA pipelines) | Loom + compliance angle |
| 4 | Repost Topic 1 with eval metrics screenshot | "Measured, not marketed — 50-question harness" |

---

## Recruiter search keywords to include (profile + posts)

`LangGraph` · `LangChain` · `Clinical AI` · `Healthcare AI` · `RAG` · `Retrieval Augmented Generation` · `HIPAA` · `Health Data` · `FastAPI` · `Python` · `LLM` · `AI Safety` · `Agent` · `Groq` · `ChromaDB`

---

## DM reply template (when recruiters reach out)

```
Thanks for reaching out — happy to share more.

Quick context: Sentinel-RAG is an open-source LangGraph clinical RAG platform I built to demonstrate refusal/escalation patterns, HIPAA-aware data handling, and end-to-end delivery (UI + API + audit).

Demo: [LOOM LINK]
Repo: https://github.com/devasai/sentinel-rag

I'm interested in [ROLE TYPE] roles where [LangGraph / regulated AI / health data] is core to the work.

Are you open to a 20-min call this week?
```
