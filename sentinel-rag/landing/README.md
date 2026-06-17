# Sentinel-RAG Landing Page

Investor- and portfolio-facing marketing site for the Clinical Protocol Guardian platform.

## Quick start

```powershell
cd landing
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Assets

Static assets are synced from `../docs/screenshots/` and `../docs/demo.gif`:

```powershell
Copy-Item ../docs/screenshots/logo.png public/
Copy-Item ../docs/screenshots/favicon.ico public/
Copy-Item ../docs/screenshots/apple-touch-icon.png public/
Copy-Item ../docs/demo.gif public/
```

## Deploy

Deploy to Vercel, Netlify, or any static host:

```powershell
npm run build
npm run start
```

The main clinical application remains the Streamlit workspace (`streamlit run app.py`).
