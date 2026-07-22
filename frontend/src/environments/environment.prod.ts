// Production: same-origin relative calls. Nginx proxies /api to the backend
// (see frontend/nginx.conf), so no absolute host is needed here.
export const environment = {
  production: true,
  apiBase: '',
};
