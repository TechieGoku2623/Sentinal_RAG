# Sentinel-RAG landing (Next.js)

Portfolio site and **live clinical workspace** for the Clinical Protocol Guardian prototype.

## Run locally

Terminal 1 — API backend:

```powershell
cd ..
uvicorn src.api.main:app --reload --port 8000
```

Terminal 2 — Next.js (portfolio + live demo):

```powershell
npm install
npm run dev
```

| URL | Purpose |
| --- | ------- |
| http://localhost:3000 | Portfolio / investor landing |
| http://localhost:3000/workspace | **Live demo** (calls FastAPI `/v1/query`) |
| http://localhost:8000/docs | OpenAPI / integrators |

Copy `.env.example` to `.env.local` if you need a remote API or API key.

## Deploy (Vercel)

1. Import the `landing/` directory as a Next.js project.
2. Set `SENTINEL_API_URL` to your hosted FastAPI URL.
3. Set `SENTINEL_API_KEY` if the API requires it.
4. Primary demo link for GitHub README: `/workspace`

## Static assets

Brand assets are generated into `../docs/brand/` and copied to `public/`:

```powershell
cd ..
python scripts/generate_brand_assets.py
```

Demo GIF for the Loom placeholder lives at `public/demo.gif` (generate with `python scripts/generate_demo_gif.py`).

## Build

```powershell
npm run build
npm start
```
