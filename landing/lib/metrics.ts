/** Eval metrics — synced from data/eval/eval_results.json via scripts/sync_eval_metrics.py */

export const METRICS = {
  questions: 50,
  keywordMatch: "54%",
  keywordMatchNum: 54,
  avgConfidence: "64%",
  avgConfidenceNum: 64,
  flagRate: "60%",
  avgLatency: "41065ms",
  validationAgreement: "88%",
  validationAgreementNum: 88,
  note: "Measured by scripts/run_eval.py on 2026-06-11 — diabetes-only corpus; unsupported categories correctly flagged.",
} as const;
