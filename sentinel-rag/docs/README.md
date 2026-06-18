# Sentinel-RAG Documentation



Enterprise documentation for the Clinical Protocol Guardian platform.



---



## Product & requirements



| Document | Audience | Description |

| -------- | -------- | ----------- |

| [PRD.md](PRD.md) | Product, clinical stakeholders | Product requirements — goals, user stories, safety policy, success metrics |

| [APP_FLOW.md](APP_FLOW.md) | Product, UX, engineering | End-to-end application flows — ingest, agent loop, UI, feedback |



## Engineering



| Document | Audience | Description |

| -------- | -------- | ----------- |

| [TRD.md](TRD.md) | Engineering, architecture review | Technical requirements — components, data model, algorithms, config, deployment |

| [END_TO_END.md](END_TO_END.md) | Engineering, DevOps | REST API, audit DB, external ingest, Docker stack |

| [ARCHITECTURE.md](ARCHITECTURE.md) | Engineering, security review | Deep dive — LangGraph design, scoring algorithm, ChromaDB schema, LangSmith traces |

| [SAAS_ARCHITECTURE.md](SAAS_ARCHITECTURE.md) | Product, engineering, investors | Top-tier SaaS blueprint — multi-tenancy, billing, onboarding, deployment |



## Safety & compliance



| Document | Audience | Description |

| -------- | -------- | ----------- |

| [CLINICAL_SAFETY.md](CLINICAL_SAFETY.md) | Clinical, legal, AI safety | Design philosophy, limitations, responsible AI framework |



---



## Platform at a glance



```

┌─────────────────────────────────────────────────────────────────┐

│                    SENTINEL-RAG PLATFORM                         │

├─────────────────────────────────────────────────────────────────┤

│  INGEST          │  Parent-child chunking → local ChromaDB      │

│  RETRIEVE        │  Semantic search over clinical guidelines      │

│  GENERATE        │  Context-only LLM with strict prompt contract  │

│  REFLECT         │  Deterministic four-factor grounding score     │

│  VALIDATE        │  Independent second-model fact-check         │

│  GOVERN          │  Recency warnings · audit logs · human feedback│

└─────────────────────────────────────────────────────────────────┘

```



## Quick links



- **Run the app:** `streamlit run app.py`

- **Build knowledge base:** `python -m src.ingest`

- **Run evaluation:** `python scripts/run_eval.py`

- **Generate demo output:** `python scripts/generate_demo_data.py`



---



> ⚠️ Sentinel-RAG is a research prototype. It is **not** a medical device and must

> **not** be used for actual clinical decision-making.

