import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import '@shoelace-style/shoelace/dist/components/card/card.js';
import '@shoelace-style/shoelace/dist/components/badge/badge.js';
import '@shoelace-style/shoelace/dist/components/spinner/spinner.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import './auth-form.js';
import './data-chart.js';
import './report-view.js';

interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  timestamp: string;
  checks: {
    database: boolean;
    redis: boolean;
    minio: boolean;
  };
}

interface DatasetSummary {
  dataset_id: number;
  name: string;
  status: string;
  project_name: string;
  created_at: string;
}

interface ProxyResult {
  proxy_id: string;
  label: string;
  sample_id: string;
  value: number | null;
  unit: string | null;
}

interface AnalysisResponse {
  dataset_id: number;
  pack: string;
  version: number;
  results: ProxyResult[];
}

type View = 'home' | 'upload' | 'dataset' | 'report';

@customElement('app-root')
export class AppRoot extends LitElement {
  @state()
  private healthStatus: HealthResponse | null = null;

  @state()
  private loading = true;

  @state()
  private datasets: DatasetSummary[] = [];

  @state()
  private error: string | null = null;

  @state()
  private currentView: View = 'home';

  @state()
  private selectedDatasetId = 0;

  @state()
  private analysisResults: AnalysisResponse | null = null;

  @state()
  private isDark = document.documentElement.classList.contains('sl-theme-dark');

  @state()
  private authenticated = !!localStorage.getItem('dataproof-token');

  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem 2rem;
      border-bottom: 4px solid var(--sl-color-neutral-900);
      background: var(--sl-color-neutral-50);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      text-decoration: none;
      color: var(--sl-color-neutral-900);
    }

    .brand-icon {
      font-size: 1.6rem;
      line-height: 1;
    }

    .brand-name {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.5rem;
      font-weight: 900;
      letter-spacing: -0.02em;
      margin: 0;
    }

    .brand-tagline {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--sl-color-neutral-500);
      margin: 0;
      display: none;
    }

    @media (min-width: 640px) {
      .brand-tagline {
        display: block;
      }
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .status-dot {
      width: 10px;
      height: 10px;
      border-radius: 0;
      border: 2px solid var(--sl-color-neutral-900);
    }

    .status-dot.healthy {
      background: var(--sl-color-success-500);
    }

    .status-dot.degraded {
      background: var(--sl-color-warning-500);
    }

    .status-dot.unhealthy {
      background: var(--sl-color-danger-500);
    }

    .nav {
      display: flex;
      gap: 0;
      padding: 0.75rem 2rem;
      background: var(--sl-color-neutral-100);
      border-bottom: 3px solid var(--sl-color-neutral-200);
      overflow-x: auto;
      flex-wrap: wrap;
    }

    .nav-btn {
      background: none;
      border: 3px solid transparent;
      font-family: 'Space Grotesk', sans-serif;
      font-weight: 700;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 0.5rem 1rem;
      cursor: pointer;
      color: var(--sl-color-neutral-600);
      transition: all 0.15s;
      white-space: nowrap;
    }

    .nav-btn:hover {
      color: var(--sl-color-neutral-900);
      background: var(--sl-color-neutral-50);
    }

    .nav-btn.active {
      color: var(--sl-color-neutral-900);
      border-color: var(--sl-color-neutral-900);
      background: var(--sl-color-neutral-50);
      box-shadow: 3px 3px 0 0 var(--sl-color-neutral-900);
    }

    .main {
      padding: 2rem;
      max-width: 1200px;
      margin: 0 auto;
      overflow-x: hidden;
    }

    .hero {
      margin-bottom: 2.5rem;
    }

    .hero h1 {
      font-size: 3rem;
      margin: 0 0 0.5rem;
      line-height: 1.05;
    }

    .hero p {
      font-size: 1.1rem;
      color: var(--sl-color-neutral-600);
      max-width: 600px;
      line-height: 1.6;
    }

    .hero-actions {
      display: flex;
      gap: 0.75rem;
      margin-top: 1.5rem;
      flex-wrap: wrap;
    }

    .section-title {
      font-family: 'Playfair Display', Georgia, serif;
      font-weight: 700;
    }

    .section-title.large { font-size: 1.5rem; margin: 2rem 0 1rem; }
    .section-title.medium { font-size: 1.2rem; margin: 0 0 0.75rem; }

    .dataset-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
    }

    .dataset-card {
      border: 3px solid var(--sl-color-neutral-200);
      padding: 1rem 1.25rem;
      cursor: pointer;
      background: var(--sl-color-neutral-50);
      box-shadow: 4px 4px 0 0 var(--sl-color-neutral-100);
      transition: transform 0.15s, box-shadow 0.15s;
    }

    .dataset-card:hover {
      transform: translate(-2px, -2px);
      box-shadow: 6px 6px 0 0 var(--sl-color-neutral-200);
    }

    .dataset-card h4 {
      font-family: 'Playfair Display', Georgia, serif;
      margin: 0 0 0.35rem;
      font-size: 1.05rem;
    }

    .dataset-card .meta {
      font-size: 0.8rem;
      color: var(--sl-color-neutral-500);
      display: flex;
      gap: 0.75rem;
      align-items: center;
    }

    .empty-state {
      color: var(--sl-color-neutral-500);
      font-style: italic;
    }

    .features {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 1.25rem;
      margin-top: 2rem;
    }

    .feature-card {
      border: 3px solid var(--sl-color-neutral-200);
      padding: 1.25rem;
      background: var(--sl-color-neutral-50);
      box-shadow: 4px 4px 0 0 var(--sl-color-neutral-200);
      transition: transform 0.15s, box-shadow 0.15s;
    }

    .feature-card:hover {
      transform: translate(-2px, -2px);
      box-shadow: 6px 6px 0 0 var(--sl-color-neutral-200);
    }

    .feature-card h3 {
      font-size: 1.1rem;
      margin: 0 0 0.5rem;
    }

    .feature-card p {
      font-size: 0.9rem;
      color: var(--sl-color-neutral-600);
      margin: 0;
      line-height: 1.5;
    }

    .feature-icon {
      font-size: 1.8rem;
      margin-bottom: 0.5rem;
      display: block;
    }

    .dataset-layout {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      overflow-x: hidden;
    }

    .dataset-layout > * {
      min-width: 0;
    }

    .dataset-stage {
      border: 3px solid var(--sl-color-neutral-900);
      padding: 1.25rem;
      background: var(--sl-color-neutral-50);
      box-shadow: 5px 5px 0 0 var(--sl-color-neutral-900);
      overflow: hidden;
    }

    .dataset-stage-title {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.2rem;
      font-weight: 700;
      margin: 0 0 1rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .charts-section {
      margin-top: 1.5rem;
    }

    .inline-charts {
      width: 100%;
      overflow: hidden;
    }

    .error {
      color: var(--sl-color-danger-500);
      font-weight: 600;
      margin-top: 1rem;
      padding: 0.75rem;
      border: 2px solid var(--sl-color-danger-500);
      background: var(--sl-color-danger-50);
    }
  `;

  async connectedCallback() {
    super.connectedCallback();
    window.addEventListener('auth-change', this._onAuthChange);
    if (this.authenticated) {
      this._restoreState();
      await this.fetchHealth();
      await this._fetchDatasets();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('auth-change', this._onAuthChange);
  }

  private _onAuthChange = () => {
    this.authenticated = !!localStorage.getItem('dataproof-token');
    if (this.authenticated) {
      this._restoreState();
      this.currentView = 'home';
      this.fetchHealth();
      this._fetchDatasets();
    }
  };

  private _restoreState() {
    const ds = localStorage.getItem('dataproof-dataset-id');
    if (ds) this.selectedDatasetId = parseInt(ds, 10);
    const ar = localStorage.getItem('dataproof-analysis');
    if (ar) {
      try { this.analysisResults = JSON.parse(ar); } catch {}
    }
  }

  private _saveState() {
    localStorage.setItem('dataproof-dataset-id', String(this.selectedDatasetId));
    if (this.analysisResults) {
      localStorage.setItem('dataproof-analysis', JSON.stringify(this.analysisResults));
    } else {
      localStorage.removeItem('dataproof-analysis');
    }
  }

  private _logout() {
    localStorage.removeItem('dataproof-token');
    localStorage.removeItem('dataproof-refresh');
    localStorage.removeItem('dataproof-dataset-id');
    localStorage.removeItem('dataproof-analysis');
    this.authenticated = false;
    this.currentView = 'home';
    this.healthStatus = null;
    this.selectedDatasetId = 0;
    this.analysisResults = null;
    this.datasets = [];
  }

  private async fetchHealth() {
    try {
      this.loading = true;
      this.error = null;
      const response = await fetch('/health');
      if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      this.healthStatus = await response.json();
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Failed to fetch health status';
    } finally {
      this.loading = false;
    }
  }

  private async _fetchDatasets() {
    try {
      const response = await fetch('/api/v1/datasets');
      if (!response.ok) return;
      this.datasets = await response.json();
    } catch {}
  }

  private _toggleTheme() {
    const html = document.documentElement;
    this.isDark = !this.isDark;
    html.classList.toggle('sl-theme-dark', this.isDark);
    localStorage.setItem('dataproof-theme', this.isDark ? 'dark' : 'light');
  }

  private _navigate(view: View) {
    this.currentView = view;
  }

  private _openDataset(id: number) {
    this.selectedDatasetId = id;
    this._saveState();
    this.currentView = 'dataset';
  }

  private _onDatasetConfirmed(e: CustomEvent) {
    this.selectedDatasetId = e.detail.datasetId;
    this._saveState();
    this.currentView = 'dataset';
    this._fetchDatasets();
  }

  private _onAnalysisComplete(e: CustomEvent) {
    this.analysisResults = e.detail as AnalysisResponse;
    this._saveState();
  }

  private _openReport() {
    this.currentView = 'report';
  }

  render() {
    if (!this.authenticated) {
      return html`<auth-form></auth-form>`;
    }

    const healthOk = this.healthStatus?.status === 'healthy';
    const healthDegraded = this.healthStatus?.status === 'degraded';
    const statusClass = healthOk ? 'healthy' : healthDegraded ? 'degraded' : 'unhealthy';

    return html`
      <header class="header">
        <a class="brand" href="/">
          <span class="brand-icon">◆</span>
          <div>
            <h1 class="brand-name">DataProof</h1>
            <p class="brand-tagline">Scientific Data Intelligence</p>
          </div>
        </a>

        <div class="header-right">
          ${!this.loading
            ? html`
                <div class="status-indicator">
                  <span class="status-dot ${statusClass}"></span>
                  ${healthOk ? 'Online' : healthDegraded ? 'Degraded' : 'Offline'}
                </div>
              `
            : html`<sl-spinner></sl-spinner>`}

          <button class="theme-toggle" @click="${this._toggleTheme}" title="Toggle theme">
            ${this.isDark ? '☀' : '☾'}
          </button>

          <sl-button size="small" @click="${this._logout}">Sign Out</sl-button>
        </div>
      </header>

      <nav class="nav">
        <button
          class="nav-btn ${this.currentView === 'home' ? 'active' : ''}"
          @click="${() => this._navigate('home')}"
        >
          ◆ Home
        </button>
        <button
          class="nav-btn ${this.currentView === 'upload' ? 'active' : ''}"
          @click="${() => this._navigate('upload')}"
        >
          ⚇ Upload
        </button>
        ${this.selectedDatasetId > 0
          ? html`
              <button
                class="nav-btn ${this.currentView === 'dataset' ? 'active' : ''}"
                @click="${() => this._navigate('dataset')}"
              >
                ◇ Dataset #${this.selectedDatasetId}
              </button>
              <button
                class="nav-btn ${this.currentView === 'report' ? 'active' : ''} ${this.analysisResults ? '' : 'disabled'}"
                @click="${this._openReport}"
                ?disabled="${!this.analysisResults}"
              >
                ▣ Report
              </button>
            `
          : null}
      </nav>

      <main class="main">
        ${this.currentView === 'home'
          ? this._renderHome()
          : this.currentView === 'upload'
          ? this._renderUpload()
          : this.currentView === 'dataset'
          ? this._renderDataset()
          : this._renderReport()}
      </main>

      <footer style="border-top: 3px solid var(--sl-color-neutral-200); padding: 1.5rem 2rem; text-align: center; font-size: 0.8rem; color: var(--sl-color-neutral-400); letter-spacing: 0.04em; text-transform: uppercase;">
        DataProof &mdash; Trustworthy Scientific Data Intelligence
      </footer>
    `;
  }

  private _renderHome() {
    return html`
      <section class="hero">
        <h1>From raw data<br />to published insight.</h1>
        <p>
          Upload tabular lab data, get instant analysis, AI-narrated interpretation,
          and export-ready scientific reports. The LLM never computes numbers &mdash;
          only interprets pre-computed results.
        </p>
        <div class="hero-actions">
          <sl-button variant="primary" size="large" @click="${() => this._navigate('upload')}">
            ⚇ Upload Your Data
          </sl-button>
          ${this.error && !this.healthStatus
            ? html`<sl-button @click="${this.fetchHealth}">⟳ Retry Connection</sl-button>`
            : ''}
        </div>
        ${this.error
          ? html`<div class="error">${this.error}</div>`
          : ''}
      </section>

      ${this.datasets.length > 0 ? html`
        <section>
          <h2 class="section-title large">My Datasets</h2>
          <div class="dataset-grid">
            ${this.datasets.map(ds => html`
              <div class="dataset-card" @click="${() => this._openDataset(ds.dataset_id)}">
                <h4>${ds.name}</h4>
                <div class="meta">
                  <sl-badge variant="${ds.status === 'mapped' ? 'success' : 'warning'}">${ds.status}</sl-badge>
                  <span>ID ${ds.dataset_id}</span>
                  <span>${new Date(ds.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            `)}
          </div>
        </section>
      ` : html`
        <section>
          <h2 class="section-title">My Datasets</h2>
          <p class="empty-state">No datasets yet — upload your first file to get started.</p>
        </section>
      `}

      <section class="features">
        <div class="feature-card">
          <span class="feature-icon">◇</span>
          <h3>Smart Mapping</h3>
          <p>AI-detected schema mapping for sample IDs, measurements, and units &mdash; review and confirm before processing.</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">▤</span>
          <h3>Proxy Analysis</h3>
          <p>Apply domain-specific analysis packs (paleoclimate, geochemistry) with pre-computed proxy formulas.</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">◉</span>
          <h3>AI Narrative</h3>
          <p>LLM-powered interpretation grounded in your computed results, with verified citations from CrossRef.</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">▣</span>
          <h3>Export Ready</h3>
          <p>Generate publication-quality PDF and DOCX reports with embedded charts, tables, and references.</p>
        </div>
      </section>
    `;
  }

  private _renderUpload() {
    return html`<dataset-upload @dataset-confirmed="${this._onDatasetConfirmed}"></dataset-upload>`;
  }

  private _renderDataset() {
    return html`
      <div class="dataset-layout">
        <!-- Stage 1: Analysis Packs -->
        <div class="dataset-stage">
          <h3 class="dataset-stage-title">1. Analysis Packs</h3>
          <analysis-panel
            .datasetId="${this.selectedDatasetId}"
            @analysis-complete="${this._onAnalysisComplete}"
          ></analysis-panel>
        </div>

        <!-- Stage 2: Data Table (full width, scrollable) -->
        <div class="dataset-stage">
          <h3 class="dataset-stage-title">2. Data</h3>
          <dataset-detail .datasetId="${this.selectedDatasetId}"></dataset-detail>
        </div>

        <!-- Stage 3: Visualizations & Report -->
        ${this.analysisResults ? html`
          <div class="dataset-stage">
            <h3 class="dataset-stage-title">3. Visualizations</h3>
            <div class="inline-charts">
              <chart-gallery .datasetId="${this.selectedDatasetId}"></chart-gallery>
            </div>
          </div>

          <div class="dataset-stage" style="text-align: center;">
            <h3 class="dataset-stage-title">4. Professional AI Report</h3>
            <p style="margin: 0 0 1rem; color: var(--sl-color-neutral-500); font-size: 0.9rem;">
              Generate a full scientific report with AI narration, charts, verified citations, and export to PDF/DOCX.
            </p>
            <sl-button variant="primary" size="large" @click="${this._openReport}">
              ▣ Generate AI Professional Report
            </sl-button>
            <p style="margin: 0.75rem 0 0; font-size: 0.75rem; color: var(--sl-color-neutral-400); font-style: italic;">
              Powered by DeepSeek · Watermarked "Created by Mohamad Kamardin with DataProof Engine"
            </p>
          </div>
        ` : ''}
      </div>
    `;
  }

  private _renderReport() {
    if (!this.selectedDatasetId) {
      return html`<p>No dataset selected.</p>`;
    }
    return html`
      <report-view
        .datasetId="${this.selectedDatasetId}"
        .analysisResults="${this.analysisResults}"
      ></report-view>
    `;
  }
}
