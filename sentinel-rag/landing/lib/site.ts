/** Public site URLs and embed config (set in .env.local for production). */

export const SITE = {
  githubUrl: "https://github.com/devasai/sentinel-rag",
  linkedinUrl: "https://www.linkedin.com/in/devasai-pranatheswar",
  /** Streamlit clinical workspace URL */
  workspaceUrl: process.env.NEXT_PUBLIC_WORKSPACE_URL ?? "http://localhost:8501",
  /** Loom embed URL, e.g. https://www.loom.com/embed/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx */
  loomEmbedUrl: process.env.NEXT_PUBLIC_LOOM_EMBED_URL ?? "",
  /** Optional public Loom share link for LinkedIn posts */
  loomShareUrl: process.env.NEXT_PUBLIC_LOOM_SHARE_URL ?? "",
};