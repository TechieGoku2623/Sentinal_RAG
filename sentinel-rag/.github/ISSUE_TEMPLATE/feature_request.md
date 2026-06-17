---
name: Feature request
about: Suggest an improvement or new capability for Sentinel-RAG
title: "[FEATURE] "
labels: enhancement
assignees: ''
---

## Problem / motivation

What problem are you trying to solve? What's the use case? A feature request
grounded in a real need is much easier to prioritize.

> Is your request related to a frustration? e.g. "It's hard to ... because ..."

## Proposed solution

Describe what you'd like to happen. Be as concrete as you can.

## Area affected

- [ ] Confidence scorer / safety logic (`src/reflection.py`)
- [ ] Agent state machine / routing (`src/agent.py`)
- [ ] Retrieval / vector store (`src/retriever.py`)
- [ ] LLM / prompts (`src/chains.py`)
- [ ] Ingestion / new file format (`src/ingest.py`)
- [ ] UI (`app.py`)
- [ ] Docs / tests / tooling
- [ ] Other

## Safety considerations

Does this change what gets surfaced to a clinician, how confidence is computed,
or when answers are flagged? If so, how do we keep the safety guarantees
(deterministic, auditable, human-in-the-loop) intact?

## Alternatives considered

Any other approaches you thought about, and why this one is preferable.

## Additional context

Links, papers, screenshots, or examples that support the request.
