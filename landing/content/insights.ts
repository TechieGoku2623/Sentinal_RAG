export type InsightTopic = {
  slug: string;
  number: number;
  title: string;
  subtitle: string;
  hook: string;
  tags: string[];
  readMinutes: number;
  linkedInAngle: string;
  sections: { heading: string; body: string }[];
};

export const INSIGHT_TOPICS: InsightTopic[] = [
  {
    slug: "stop-instead-of-hallucinate",
    number: 1,
    title: "Why I built Sentinel-RAG to stop — not hallucinate",
    subtitle: "Clinical AI should escalate uncertainty, not perform confidence.",
    hook: "The most dangerous output in healthcare isn't a wrong answer spoken quietly — it's a wrong answer spoken fluently.",
    tags: ["Clinical AI", "LangGraph", "RAG", "AI Safety", "Healthcare"],
    readMinutes: 4,
    linkedInAngle: "Portfolio proof that you design for refusal + escalation, not demo magic.",
    sections: [
      {
        heading: "The problem with confident RAG",
        body:
          "Most retrieval-augmented systems optimize for a smooth answer on the first pass. In consumer search, that's fine. In clinical protocol review, it's a liability: the model's fluency is uncorrelated with whether the retrieved guideline actually supports the recommendation.",
      },
      {
        heading: "Stop as a first-class outcome",
        body:
          "Sentinel-RAG treats 'I cannot answer safely from these guidelines' as a successful outcome — not a failure state. A deterministic reflection layer scores grounding before release. Cross-model validation checks the draft against sources. When confidence is insufficient, the system flags for human review instead of shipping an unverified protocol step.",
      },
      {
        heading: "What I implemented",
        body:
          "A LangGraph cyclic agent: retrieve → generate → reflect → (re-retrieve | flag | output). Deterministic confidence scoring, recency penalties on aging evidence, audit logging, and a clinician-facing UI that separates validated prose from safety metadata. The goal isn't the smartest chatbot — it's the most accountable one.",
      },
      {
        heading: "Why recruiters should care",
        body:
          "If you're hiring for production AI in regulated domains, you need engineers who design escalation paths — not demos that hide uncertainty. This repo is my public proof of that instinct.",
      },
    ],
  },
  {
    slug: "hipaa-pipelines-clinical-ai",
    number: 2,
    title: "What 4 months of HIPAA health data pipelines taught me about clinical AI",
    subtitle: "Compliance isn't a slide deck — it's where your architecture starts.",
    hook: "HIPAA didn't teach me to fear AI in healthcare. It taught me where the real engineering work begins.",
    tags: ["HIPAA", "Health Data", "Clinical AI", "Data Engineering", "Compliance"],
    readMinutes: 5,
    linkedInAngle: "Shows you understand regulated data — not just model APIs.",
    sections: [
      {
        heading: "Pipelines before prompts",
        body:
          "Four months inside health data pipelines reframed how I think about clinical AI. Before you debate prompt wording, you need: provenance on every document, retention boundaries, least-privilege access, and an audit trail that survives a compliance review. If your RAG stack can't answer 'where did this chunk come from and who ingested it?', you're not ready for clinical workflows.",
      },
      {
        heading: "Local-first is a feature, not a shortcut",
        body:
          "Sentinel-RAG uses on-prem-capable ChromaDB and CPU embeddings so guideline text doesn't have to leave the trust boundary to be searchable. Groq-hosted Llama is a dev convenience — the architecture preserves a path to air-gapped vLLM/Ollama. That portability is a direct lesson from BAA conversations and data residency requirements.",
      },
      {
        heading: "Auditability beats accuracy theater",
        body:
          "HIPAA environments punish black boxes. I built SQLite audit stores, interaction logs, document registry metadata, and CSV reward-model features so every validation run is traceable. Escalation isn't just UX — it's governance.",
      },
      {
        heading: "Clinical AI ≠ consumer chat",
        body:
          "Trainee recollection, spaced repetition, and protocol validation are different jobs than 'ask me anything.' The product surface should match the risk: study mode for learning, validation mode for decision support, explicit disclaimers that this is research infrastructure — not a medical device.",
      },
    ],
  },
  {
    slug: "langgraph-vs-langchain",
    number: 3,
    title: "LangGraph vs LangChain — when to use each",
    subtitle: "Chains compose steps. Graphs compose decisions.",
    hook: "If your agent only moves forward, you don't have an agent — you have a script with an LLM in the middle.",
    tags: ["LangGraph", "LangChain", "AI Agents", "LLM Engineering", "Python"],
    readMinutes: 4,
    linkedInAngle: "Direct signal for teams hiring LangGraph engineers.",
    sections: [
      {
        heading: "LangChain: the right default for linear workflows",
        body:
          "LangChain excels when your pipeline is retrieve → prompt → parse → return. Document Q&A, summarization, structured extraction, single-pass RAG — use chains. They're readable, testable, and fast to ship.",
      },
      {
        heading: "LangGraph: when you need cycles and policy",
        body:
          "Sentinel-RAG's reflection loop is the textbook case for a graph: after generation, a scoring node decides retrieve again, flag for human review, or emit output. That conditional routing is awkward in a linear chain and natural in LangGraph state machines.",
      },
      {
        heading: "Decision matrix",
        body:
          "Use LangChain when: one direction, fixed steps, minimal branching. Use LangGraph when: retries, human-in-the-loop, multi-agent handoffs, persistent state, or safety gates that can loop. In clinical AI, I default to LangGraph because uncertainty handling is policy — not an afterthought.",
      },
      {
        heading: "What this repo demonstrates",
        body:
          "Open-source LangGraph agent with typed state, conditional edges, bounded retries, cross-validation node, and Streamlit + FastAPI clients on the same core. If you're evaluating LangGraph talent, this is the shape of work I deliver.",
      },
    ],
  },
];

export function getInsightBySlug(slug: string): InsightTopic | undefined {
  return INSIGHT_TOPICS.find((t) => t.slug === slug);
}
