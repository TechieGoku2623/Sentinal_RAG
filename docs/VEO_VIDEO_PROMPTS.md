# Sentinel-RAG — Veo video creation prompts

Full storyboard for cinematic walkthrough clips. Use with **Google Veo 3.1** (Gemini app, Flow, or API), or generate the **Python equivalent** locally:

```powershell
pip install -r requirements-video.txt
python scripts/generate_walkthrough_video.py
```

See [VIDEO_WALKTHROUGH.md](VIDEO_WALKTHROUGH.md) for Loom recording and assembly guides.

---

## How to use these prompts

| Option | Steps |
| ------ | ----- |
| **A — Gemini App** | gemini.google.com → Veo 3.1 → paste one clip at a time → download → edit in CapCut |
| **B — Google Flow** | flow.google.com → scene cards → Extend to chain → export |
| **C — Gemini API** | `python scripts/generate_veo_walkthrough.py` |
| **D — MoviePy (free, local)** | `python scripts/generate_walkthrough_video.py` |

**Settings for all Veo clips:** 1080p · 16:9 · 8 seconds · seed **4821937**

---

## Story arc (7 clips)

| Clip | Title | Scene |
| ---- | ----- | ----- |
| 01 | Hook | Wrong confident AI dose on tablet |
| 02 | Problem | Doctor skeptical, compares to guideline |
| 03 | Activates | Sentinel-RAG pipeline lights up |
| 04 | Demo A | 98% high-confidence diabetes answer |
| 05 | Demo B | Amber retry loop → 88% |
| 06 | Demo C | 27% flagged for review |
| 07 | Close | Doctor trusts the system |

### Bonus clips (LinkedIn / extended cut)

| Clip | Title | Scene |
| ---- | ----- | ----- |
| bonus_a | Architecture | Abstract pipeline with data packets + retry loop |
| bonus_b | Privacy first | Server rack, teal padlock, on-prem boundary |
| bonus_c | Guideline source | Document scan + teal highlight extraction |

```powershell
# All 10 clips as separate MP4s + full ~82s video
python scripts/generate_walkthrough_video.py --export-clips --with-bonus
```

Outputs: `docs/walkthrough_clips/clip_01.mp4` ... `bonus_c.mp4` and `docs/walkthrough-full.mp4`

**Title card (edit in post):** SENTINEL-RAG · Clinical Protocol Guardian · GitHub URL on `#060D14`

**Final runtime:** ~75s with transitions + title card

---

## Clip prompts (paste into Veo)

### CLIP 01 — THE HOOK

Extreme close-up shot of a dark modern medical tablet screen displaying a clinical chat interface. The screen shows a question typed in white text on a near-black background: What is the correct metformin dose for this patient? Below it, an AI response text animates in, reading: The standard dose is 1000mg twice daily. The camera holds on the screen for 2 seconds, then slowly pulls back to reveal the screen glowing in a dimly lit hospital room. A blurred doctor's hand in the foreground reaches toward the screen but freezes. The scene cuts to a single red pixel pulsing on the edge of the screen — wrong, but presented with false confidence. Cinematic color grade: deep navy shadows, cold blue ambient light from equipment, a faint red warning glow from the tablet edge. Mood: tense, quiet unease. Camera: macro lens, shallow depth of field, very slow dolly pull-back. No faces. Photorealistic.

**Caption:** Healthcare AI can't afford to hallucinate.

### CLIP 02 — THE PROBLEM

Medium shot of a female doctor in her 40s, short dark hair, white hospital scrubs, at a dark desk in a modern hospital office at night. She stares at a monitor showing a clinical AI chat with a confident wrong answer. Skeptical expression — tilts head, narrows eyes, compares printed guideline to screen. Cold steel-blue tones, teal monitor glow. Camera slowly pushes in. Photorealistic.

**Caption:** Standard AI fails silently.

### CLIP 03 — SENTINEL-RAG ACTIVATES

Close-up macro of ultrawide dark monitor on minimal desk. White monospaced text types: SENTINEL-RAG · CLINICAL PROTOCOL GUARDIAN. Horizontal pipeline animates in teal: RETRIEVE → GENERATE → REFLECT → OUTPUT. Nodes light sequentially. Slow dolly push into screen. Near-black room, monitor-only light. No people.

**Caption:** Sentinel-RAG self-audits every answer.

### CLIP 04 — HIGH CONFIDENCE (98%)

Dark clinical interface. Question: What is the first-line treatment for Type 2 diabetes? Answer renders in grey. Teal radial arc fills to 98%. Pills: RETURNED · Retries: 0 · Sources: 3. Deep navy, single teal glow. Static then slow pull-back.

**Caption:** High confidence → instant return.

### CLIP 05 — SELF-CORRECTION

Pipeline tracker: RETRIEVE, GENERATE, REFLECT, OUTPUT. REFLECT pulses amber at 74%. Teal arrows loop back to RETRIEVE. Re-query. Arc fills 74% → 88%. OUTPUT illuminates teal. Static camera.

**Caption:** Borderline → automatic re-query.

### CLIP 06 — FLAGGED

Question: What happens if a patient misses a dose? Red warning card. Arc stops at 27%. FLAGGED FOR CLINICAL REVIEW. Body: guidelines do not address this scenario. Pulsing red left border. No teal. Controlled uncertainty.

**Caption:** Uncertain → flagged for human review.

### CLIP 07 — THE CLOSE

Same doctor from clip 02, calm at desk, teal monitor glow. Nods once, annotates document. Monitor shows pipeline at rest: 4 answered, 1 escalated. Slow zoom-out. Fade to black last 2 seconds.

**Caption:** Safe AI that knows its limits.

---

## Editing assembly

```
[Clip 01] → 0.5s black → [Clip 02] → 0.3s dissolve → [Clip 03]
→ [Clip 04] → 0.5s pause → [Clip 05] → [Clip 06] → [Clip 07]
→ 2s fade → [Title card 4s]
```

## LinkedIn cut

- **Native upload:** all 7 clips + title + captions (~75s)
- **Hybrid:** Veo clips 01 + 07 as bookends, Loom screen recording in middle

## README cut

```powershell
python scripts/generate_walkthrough_video.py --product-only
```

Clips 03–06 only (~32s) — pure product demo for technical audiences.
