import Plotly from 'plotly.js-dist-min';
import './components/app-root';
import './components/auth-form';
import './components/dataset-upload';
import './components/dataset-detail';
import './components/analysis-panel';
import './components/data-chart';
import './components/chart-gallery';
import './components/report-view';
import './styles/global.css';

// ── Shoelace Theme Setup ─────────────────────────────────
import '@shoelace-style/shoelace/dist/themes/light.css';
import '@shoelace-style/shoelace/dist/themes/dark.css';
import { setBasePath } from '@shoelace-style/shoelace/dist/utilities/base-path.js';

setBasePath(
  'https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.17.0/cdn/'
);

// ── Dark Mode Detection ──────────────────────────────────
const stored = localStorage.getItem('dataproof-theme');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
const isDark = stored ? stored === 'dark' : prefersDark;

if (isDark) {
  document.documentElement.classList.add('sl-theme-dark');
}

// ── Global fetch wrapper: auto-attach Bearer + refresh ──
function getToken(): string | null {
  return localStorage.getItem('dataproof-token');
}

function setToken(access: string, refresh: string): void {
  localStorage.setItem('dataproof-token', access);
  localStorage.setItem('dataproof-refresh', refresh);
}

function clearToken(): void {
  localStorage.removeItem('dataproof-token');
  localStorage.removeItem('dataproof-refresh');
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = localStorage.getItem('dataproof-refresh');
  if (!refresh) return null;
  try {
    const res = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) { clearToken(); return null; }
    const data = await res.json();
    setToken(data.access_token, data.refresh_token);
    return data.access_token;
  } catch { clearToken(); return null; }
}

const originalFetch = window.fetch.bind(window);
window.fetch = async (input: RequestInfo | URL, init: RequestInit = {}) => {
  const url = typeof input === 'string' ? input : input instanceof Request ? input.url : (input as URL).href;
  const isApi = url.startsWith('/api/') || url.startsWith('/health');

  if (isApi) {
    const token = getToken();
    if (token) {
      const headers = new Headers(init.headers);
      headers.set('Authorization', `Bearer ${token}`);
      init = { ...init, headers };
    }
  }

  let response = await originalFetch(input, init);

  // Auto-refresh on 401
  if (isApi && response.status === 401 && getToken()) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const headers = new Headers(init.headers);
      headers.set('Authorization', `Bearer ${newToken}`);
      response = await originalFetch(input, { ...init, headers });
    }
  }

  return response;
};

// ── Plotly ────────────────────────────────────────────────
(window as unknown as Record<string, unknown>).Plotly = Plotly;
