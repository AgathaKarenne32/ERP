// API base URL. In dev the Angular server proxies to the backend on :8000.
// For the Nginx prod build this is replaced at container start (see DEPLOY.md).
export const environment = {
  production: false,
  apiBase: 'http://localhost:8000',
};
