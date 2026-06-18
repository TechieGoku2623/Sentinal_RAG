/** Public site URLs and embed config (set in .env.local for production). */

export const SITE = {
  githubUrl: "https://github.com/TechieGoku2623/Sentinal_RAG",
  linkedinUrl: "https://www.linkedin.com/in/devasai-pranatheswar",
  /** Primary live demo — Next.js workspace (Vercel / localhost:3000). */
  workspaceUrl: process.env.NEXT_PUBLIC_WORKSPACE_URL ?? "/workspace",
  /** Optional Streamlit internal workspace (localhost:8501). */
  streamlitUrl: process.env.NEXT_PUBLIC_STREAMLIT_URL ?? "http://localhost:8501",
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  docsUrl:
    process.env.NEXT_PUBLIC_DOCS_URL ??
    "https://github.com/TechieGoku2623/Sentinal_RAG/tree/main/sentinel-rag/docs",
  loomEmbedUrl: process.env.NEXT_PUBLIC_LOOM_EMBED_URL ?? "",
  loomShareUrl: process.env.NEXT_PUBLIC_LOOM_SHARE_URL ?? "",
  youtubeEmbedId: process.env.NEXT_PUBLIC_YOUTUBE_EMBED_ID ?? "",
  youtubeWatchUrl: process.env.NEXT_PUBLIC_YOUTUBE_WATCH_URL ?? "",
};

export function apiDocsUrl(): string {
  return `${SITE.apiUrl.replace(/\/$/, "")}/docs`;
}
