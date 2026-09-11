# Page override — Command Center (`ui/command_center.py`)

**Overrides MASTER for Streamlit mission-control dashboard.**

## Layout
- Workbench pattern: status tiles row → metrics → quick actions → two-column (recent validations | action queue)
- No hero marketing block — function-first
- Pill nav for section switching (already in `app.py`)

## Status tiles (6)
API · LLM · Knowledge base · Audit store · Hallmark score · Latency profile

## Action queue priorities
1. API offline → settings / start uvicorn
2. No guidelines → admin upload
3. Missing GROQ_API_KEY → .env
4. Quota >90% → upgrade plan
5. Flagged validations → audit trail
6. Hallmark critical findings → build studio

## Streamlit constraints
- Use `_html()` + existing `.sr-cc-*` classes in `command_center.py`
- Native `st.metric` / `st.dataframe` for data — HTML for tiles only
- Keep sidebar for uploads and workspace switch

## Do not
- Framer-motion-style animation in Streamlit
- shadcn components (React only) — port patterns manually
