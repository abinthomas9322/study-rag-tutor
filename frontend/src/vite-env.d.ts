/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the backend API in deployed builds (unset in dev → "/api"). */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
