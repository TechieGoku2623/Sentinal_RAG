---
name: Bug report
about: Report incorrect behavior, a wrong confidence score, or a crash
title: "[BUG] "
labels: bug
assignees: ''
---

## Describe the bug

A clear and concise description of what went wrong.

## Query that caused the issue

```
<Paste the exact clinical query you submitted>
```

> If the query or any uploaded document contains real PHI, **do not paste it** —
> describe it generically or use a redacted/synthetic version instead.

## Confidence score: expected vs. actual

| | Value |
| --- | --- |
| **Expected** confidence | e.g. should have been LOW / flagged |
| **Actual** confidence   | e.g. 0.91 (returned as authoritative) |
| Was it flagged for review? | yes / no |
| Retry count (re-queries)   | e.g. 0 |

## What was wrong with the answer

- [ ] Hallucinated / ungrounded content
- [ ] Contradicted the source guideline
- [ ] Wrong confidence (too high / too low)
- [ ] Should have been flagged but wasn't (or vice versa)
- [ ] Crash / exception
- [ ] Other (describe)

## Steps to reproduce

1. Guidelines loaded (file names / type, or "sample_diabetes_guideline.txt"):
2. Query submitted:
3. Observed result:

## Relevant logs / traceback

```
<Paste console logs or the Python traceback here>
```

## Environment

- OS: e.g. Windows 11
- Python version (`python --version`): e.g. 3.11.x
- Install method: pip / Docker
- Key package versions (`pip show langgraph chromadb langchain-groq | findstr Version`):
  - langgraph:
  - langchain / langchain-groq:
  - chromadb:
  - sentence-transformers:
- Running via: `streamlit run app.py` / `run_agent()` directly / tests

## Additional context

Anything else that might help — number of guideline chunks loaded, whether
LangSmith tracing was on, a trace link, etc.
