import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('token');
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

export function extractError(err, fallback = 'Something went wrong.') {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((m) => `${(m.loc || []).slice(1).join('.')}: ${m.msg}`)
      .join(' · ');
  }
  if (err?.response?.data?.message) return err.response.data.message;
  if (err?.message?.includes('Network Error')) return 'Cannot reach the server — is it running?';
  return fallback;
}

export default api;
