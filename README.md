<div align="center">

# Sentinel-RAG

**Clinical Protocol Guardian**

Guideline-grounded answers that **refuse to be confidently wrong**. Retrieve from your own protocol documents, generate a draft, score grounding, then either show the answer, retry, or FLAG a clinician.

This GitHub repository keeps the runnable product in [`sentinel-rag/`](sentinel-rag/).

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](sentinel-rag/README.md)
[![Next.js](https://img.shields.io/badge/Landing-Next.js-000000?logo=nextdotjs)](sentinel-rag/landing)
[![License](https://img.shields.io/badge/License-MIT-green)](sentinel-rag/LICENSE)
[![Demo](https://img.shields.io/badge/Demo-plays%20on%20this%20page-14B8A6)](#watch-the-demo)

**Full product README → [sentinel-rag/README.md](sentinel-rag/README.md)**

</div>

---

## The problem

In clinical protocol work, a fluent hallucination is not a UX bug. It is a safety event: a confident wrong dose, contraindication, or “first-line” step.

Standard RAG retrieves chunks, stuffs them into a prompt, and returns whatever the model produces on the **first pass**. The model’s tone is not a measure of grounding. Supervisors cannot see *why* the system was sure.

## What this software does

Sentinel-RAG answers questions **only from ingested guideline text**, then **audits the draft before anyone sees it**:

```text
Question  →  Retrieve guideline chunks (local ChromaDB)
          →  Generate a draft (context only, Groq Llama 3.1 8B)
          →  Reflect (deterministic confidence — not a second LLM)
          →  high    →  show the answer + citations
          →  medium  →  retrieve more and retry
          →  low     →  FLAG for clinical review
```

The scorer in `src/reflection.py` is inspectable (coverage, hedging, specificity, contradiction). Using another model as the only safety check would stack hallucination on hallucination.

*Research prototype — not a medical device. Do not use for clinical decisions.*

---

## Watch the demo

The walkthrough **plays on this page**.

<p align="center">
  <img src="sentinel-rag/docs/demo.gif" alt="Sentinel-RAG walkthrough — plays inline" width="920"/>
</p>

| In the clip | Why it matters |
| --- | --- |
| Hero | Safety layer, not a fluent chatbot |
| Pipeline | Retrieve → generate → reflect → FLAG |
| Eval | Metrics from `scripts/run_eval.py` |
| Workspace | Same idea, interactive (`/workspace`) |

The GIF is the **portfolio + workspace chrome**. Live answers also need FastAPI with `GROQ_API_KEY`. The bundled corpus is a **sample diabetes guideline**; other topics will FLAG often, by design.

---

## Repository map

```text
sentinal_rag/                         ← GitHub root
└── sentinel-rag/                     ← runnable product
    ├── src/                          agent, retrieval, reflection, FastAPI
    ├── landing/                      Next.js portfolio + /workspace
    ├── app.py                        Streamlit workspace
    ├── data/guidelines/
    ├── docs/                         PRD, architecture, clinical safety
    │   └── demo.gif
    └── README.md
```

---

## Quick start

```bash
cd sentinel-rag
pip install -r requirements.txt
cp .env.example .env          # add GROQ_API_KEY
python -m src.ingest

# Terminal 1
uvicorn src.api.main:app --reload --port 8000

# Terminal 2
cd landing && npm install && npm run dev
```

| Surface | URL |
| --- | --- |
| Portfolio | http://localhost:3000 |
| Live workspace | http://localhost:3000/workspace |
| API docs | http://localhost:8000/docs |
| Streamlit (optional) | `streamlit run app.py` → :8501 |

---

<p align="center"><sub>Sentinel-RAG · grounded, self-auditing, willing to escalate</sub></p>
