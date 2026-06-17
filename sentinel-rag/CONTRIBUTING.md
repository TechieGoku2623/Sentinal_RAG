# Contributing to Sentinel-RAG

Thanks for your interest in improving Sentinel-RAG! This is a clinical-AI safety
project, so contributions are held to a high bar for correctness, transparency,
and honesty about limitations. Please read this guide before opening a PR.

> By contributing you agree your work is licensed under the project's
> [MIT License](LICENSE).

---

## Development setup (Windows / PowerShell)

```powershell
# 1. Fork & clone
git clone https://github.com/<your-username>/sentinel-rag.git
cd sentinel-rag

# 2. Virtual environment + dependencies
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Environment variables
copy .env.example .env
#    add GROQ_API_KEY (and optionally LangSmith keys)

# 4. Seed the vector store and run the app
python -m src.ingest
streamlit run app.py

# 5. Run the test suite (no API keys required — Groq/Chroma are mocked)
pytest
```

On macOS/Linux, replace the venv activation with `source .venv/bin/activate`.

---

## Where things live

| Area                     | File                  |
| ------------------------ | --------------------- |
| Agent state machine      | `src/agent.py`        |
| Vector store / retrieval | `src/retriever.py`    |
| LLM + clinical prompt    | `src/chains.py`       |
| Confidence scorer        | `src/reflection.py`   |
| Ingestion / chunking     | `src/ingest.py`       |
| UI                       | `app.py`              |
| Tests                    | `tests/test_agent.py` |

Architecture and safety rationale: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
and [`docs/CLINICAL_SAFETY.md`](docs/CLINICAL_SAFETY.md).

---

## How to add a new guideline format

Loaders live in `src/ingest.py`. To support a new format (e.g. `.docx`, `.html`):

1. Add a `load_<format>_file(filepath: str) -> str` function that returns plain
   text. Handle failures gracefully (log a warning, return `""`) — one bad file
   must never abort an ingest run.
2. Register the extension in `ingest_all_guidelines()` (the file filter and the
   loader dispatch).
3. Add any new dependency to `requirements.txt` with a **pinned** version.
4. Add a small fixture file under `tests/` and a test asserting extraction works.

Keep the output as clean text — downstream chunking assumes whitespace-separated
words.

---

## How to improve the confidence scorer

The scorer (`src/reflection.py`) is the heart of the safety layer. Changes here
get extra scrutiny.

**Ground rules:**

- **Keep it deterministic and explainable.** The same input must always produce
  the same score. Do not introduce an LLM as the *sole* judge — that stacks
  hallucination risk and breaks auditability. (An LLM/learned model is welcome
  as an *additional, optional* factor with a deterministic fallback.)
- **Document the rationale.** Every factor must have a clear clinical-safety
  justification in comments and in `docs/ARCHITECTURE.md`.
- **Justify weight changes with data.** If you re-weight factors or move
  thresholds, include before/after results on a set of example queries in the PR
  (false-flag rate and miss rate matter most).
- **Add tests.** New factors need unit tests showing they raise/lower scores in
  the intended direction, plus a regression test for any bug you're fixing.

---

## Code style

- **Python 3.11**, `from __future__ import annotations`.
- **Type hints on every function** signature.
- **Docstrings** on all public functions/modules; comments explain *why*, not
  *what*.
- **Logging, not `print`** — use `logging.getLogger(__name__)`.
- **Graceful failure** — wrap I/O and external calls (Groq, ChromaDB, file/CSV)
  in `try/except` and degrade safely; never crash a graph node or the UI.
- **Consistent imports** — use `src.`-package imports (`from src.retriever import ...`).
- Keep lines reasonably short (~88 cols) and run a formatter/linter before
  pushing. Ensure `pytest` passes and there are no linter errors.

---

## Pull request process

1. Branch from `main`: `git checkout -b feat/short-description`.
2. Make focused commits; one logical change per PR where possible.
3. Ensure `pytest` passes and no linter errors remain.
4. Update docs (`README.md`, `docs/`) if behavior or architecture changed.
5. Fill out the PR template below.

### PR template

```markdown
## Summary
<What does this change do, and why?>

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Confidence scorer / safety logic change
- [ ] New guideline format / loader
- [ ] Docs only

## Safety impact
<Does this affect confidence scoring, routing, or what gets surfaced to a
clinician? If yes, explain. If no, say "none".>

## Testing
- [ ] `pytest` passes locally
- [ ] No linter errors
- [ ] Added/updated tests
<For scorer/threshold changes: include before/after metrics on example queries.>

## Checklist
- [ ] Type hints + docstrings added
- [ ] Used logging (no stray prints)
- [ ] Docs updated if needed
- [ ] No secrets committed (.env stays local)
```

---

## Reporting safety issues

If you find a way to make the agent confidently return an ungrounded clinical
answer, please open a **bug report** with the exact query and the confidence
score it produced. Adversarial examples are one of the most valuable
contributions to this project.

Thank you for helping make clinical AI safer. 🩺
