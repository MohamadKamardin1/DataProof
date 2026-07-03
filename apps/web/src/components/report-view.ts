import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import '@shoelace-style/shoelace/dist/components/card/card.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/alert/alert.js';
import '@shoelace-style/shoelace/dist/components/spinner/spinner.js';
import '@shoelace-style/shoelace/dist/components/textarea/textarea.js';
import './data-chart.js';

interface Citation {
  authors: string;
  year: number | null;
  title: string;
  venue: string | null;
  doi_or_url: string | null;
  verified: boolean;
}

interface PerSampleInterpretation {
  sample_id: string;
  classification: string;
  rationale: string;
}

interface InterpretationResult {
  per_sample: PerSampleInterpretation[];
  overall_narrative: string;
  citations: Citation[];
}

interface ChartSpec {
  figure_json: object;
  title: string;
  chart_type: string;
}

interface ChartsResponse {
  pack_id: string;
  pack_name: string;
  charts: ChartSpec[];
}

@customElement('report-view')
export class ReportView extends LitElement {
  @property({ type: Number })
  datasetId = 0;

  @property({ type: String })
  packId = 'paleoclimate_xrf';

  @property({ type: Object })
  analysisResults: unknown = null;

  @state()
  private charts: ChartSpec[] = [];

  @state()
  private loadingCharts = false;

  @state()
  private interpretation: InterpretationResult | null = null;

  @state()
  private reportId: number | null = null;

  @state()
  private exportingPdf = false;

  @state()
  private exportingDocx = false;

  @state()
  private error: string | null = null;

  @state()
  private narrative = '';

  static styles = css`
    :host {
      display: block;
    }

    .report-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
      gap: 0.75rem;
    }

    .report-header h2 {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.8rem;
      margin: 0;
    }

    .disclosure-banner {
      border: 3px solid var(--sl-color-warning-500);
      padding: 0.75rem 1rem;
      margin-bottom: 1.5rem;
      font-weight: 700;
      color: var(--sl-color-warning-500);
      background: var(--sl-color-warning-50);
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .watermark {
      text-align: center;
      padding: 1rem;
      margin-bottom: 1.5rem;
      border: 3px solid var(--sl-color-primary-500);
      background: var(--sl-color-primary-50);
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1rem;
      font-weight: 700;
      color: var(--sl-color-primary-500);
      letter-spacing: 0.02em;
    }

    .export-bar {
      display: flex;
      gap: 0.75rem;
    }

    .section-title {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.3rem;
      margin: 2rem 0 0.75rem;
      padding-bottom: 0.4rem;
      border-bottom: 3px solid var(--sl-color-neutral-200);
    }

    .charts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
      gap: 1.25rem;
      margin-top: 1rem;
    }

    .chart-wrapper {
      border: 3px solid var(--sl-color-neutral-200);
      background: var(--sl-color-neutral-50);
      box-shadow: 4px 4px 0 0 var(--sl-color-neutral-100);
    }

    .chart-title {
      font-weight: 700;
      padding: 0.6rem 0.75rem;
      background: var(--sl-color-neutral-100);
      border-bottom: 2px solid var(--sl-color-neutral-200);
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .narrative-area {
      width: 100%;
      min-height: 180px;
      padding: 1rem;
      border: 3px solid var(--sl-color-neutral-200);
      font-family: 'Space Grotesk', system-ui, sans-serif;
      font-size: 0.95rem;
      line-height: 1.7;
      resize: vertical;
      background: var(--sl-color-neutral-50);
      color: var(--sl-color-neutral-900);
      box-shadow: inset 2px 2px 0 0 var(--sl-color-neutral-100);
    }

    .per-sample-list {
      margin-top: 1rem;
    }

    .per-sample {
      border: 2px solid var(--sl-color-neutral-200);
      padding: 0.75rem 1rem;
      margin-bottom: 0.5rem;
      background: var(--sl-color-neutral-50);
    }

    .per-sample strong {
      font-weight: 700;
    }

    .per-sample em {
      color: var(--sl-color-primary-500);
      font-style: normal;
      font-weight: 600;
    }

    .citations-list {
      list-style: none;
      padding: 0;
      margin-top: 1rem;
    }

    .citation-item {
      padding: 0.75rem 1rem;
      margin-bottom: 0.5rem;
      font-size: 0.9rem;
      border-left: 4px solid;
    }

    .citation-item.verified {
      background: var(--sl-color-success-50);
      border-left-color: var(--sl-color-success-500);
    }

    .citation-item.unverified {
      background: var(--sl-color-danger-50);
      border-left-color: var(--sl-color-danger-500);
    }

    .verified-badge {
      color: var(--sl-color-success-500);
      font-weight: 700;
      font-size: 0.8rem;
      text-transform: uppercase;
    }

    .unverified-badge {
      color: var(--sl-color-danger-500);
      font-weight: 700;
      font-size: 0.8rem;
      text-transform: uppercase;
    }

    .placeholder {
      color: var(--sl-color-neutral-400);
      font-style: italic;
      text-align: center;
      padding: 2.5rem;
      border: 3px dashed var(--sl-color-neutral-200);
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.1rem;
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

  connectedCallback() {
    super.connectedCallback();
    if (this.datasetId > 0) {
      this._loadCharts();
      this._loadInterpretation();
      this._createReport();
    }
  }

  private async _loadCharts() {
    this.loadingCharts = true;
    try {
      const response = await fetch(
        `/api/v1/datasets/${this.datasetId}/charts?pack_id=${this.packId}`
      );
      if (response.ok) {
        const data: ChartsResponse = await response.json();
        this.charts = data.charts || [];
      }
    } catch (err) {
      console.error('Failed to load charts:', err);
    } finally {
      this.loadingCharts = false;
    }
  }

  private async _loadInterpretation() {
    try {
      const jobsResponse = await fetch(`/api/v1/datasets/${this.datasetId}/interpret?pack_id=${this.packId}`, {
        method: 'POST',
      });
      if (jobsResponse.status === 202) {
        const data = await jobsResponse.json();
        await this._pollJob(data.status_url);
      }
    } catch (err) {
      console.error('Failed to start interpretation:', err);
    }
  }

  private async _pollJob(statusUrl: string) {
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 2000));
      try {
        const response = await fetch(statusUrl);
        const data = await response.json();
        if (data.status === 'completed') {
          this.interpretation = data.result;
          this.narrative = data.result?.overall_narrative || '';
          return;
        }
        if (data.status === 'failed') {
          console.error('Interpretation failed:', data.error);
          return;
        }
      } catch {
        return;
      }
    }
  }

  private async _createReport() {
    try {
      const response = await fetch(
        `/api/v1/datasets/${this.datasetId}/report?pack_id=${this.packId}`,
        { method: 'POST' }
      );
      if (response.ok) {
        const data = await response.json();
        this.reportId = data.report_id;
      }
    } catch (err) {
      console.error('Failed to create report:', err);
    }
  }

  private async _exportPdf() {
    if (!this.reportId) return;
    this.exportingPdf = true;
    try {
      const response = await fetch(`/api/v1/reports/${this.reportId}/export?format=pdf`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dataproof_report_${this.datasetId}_${this.packId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Export failed';
    } finally {
      this.exportingPdf = false;
    }
  }

  private async _exportDocx() {
    if (!this.reportId) return;
    this.exportingDocx = true;
    try {
      const response = await fetch(`/api/v1/reports/${this.reportId}/export?format=docx`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dataproof_report_${this.datasetId}_${this.packId}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Export failed';
    } finally {
      this.exportingDocx = false;
    }
  }

  render() {
    return html`
      <div class="report-header">
        <h2>Report</h2>
        <div class="export-bar">
          <sl-button
            variant="primary"
            ?loading="${this.exportingPdf}"
            ?disabled="${!this.reportId}"
            @click="${this._exportPdf}"
          >
            ▣ Export PDF
          </sl-button>
          <sl-button
            ?loading="${this.exportingDocx}"
            ?disabled="${!this.reportId}"
            @click="${this._exportDocx}"
          >
            ▣ Export DOCX
          </sl-button>
        </div>
      </div>

      <div class="watermark">
        ✦ Created by Mohamad Kamardin with DataProof Engine ✦
      </div>

      <div class="disclosure-banner">
        ⚠ AI-assisted draft — verify all content before publication
      </div>

      ${this.error ? html`<div class="error">${this.error}</div>` : null}

      <!-- Charts -->
      <h3 class="section-title">Charts</h3>
      ${this.loadingCharts
        ? html`<sl-spinner></sl-spinner>`
        : this.charts.length === 0
        ? html`<div class="placeholder">No charts available. Run analysis first.</div>`
        : html`
            <div class="charts-grid">
              ${this.charts.map(
                chart => html`
                  <div class="chart-wrapper">
                    <div class="chart-title">${chart.title}</div>
                    <data-chart .figureJson="${chart.figure_json}" .chartTitle="${chart.title}">
                    </data-chart>
                  </div>
                `
              )}
            </div>
          `}

      <!-- Narrative -->
      <h3 class="section-title">Interpretation Narrative</h3>
      ${this.interpretation
        ? html`
            <textarea
              class="narrative-area"
              .value="${this.narrative}"
              @input="${(e: InputEvent) => {
                this.narrative = (e.target as HTMLTextAreaElement).value;
              }}"
            ></textarea>

            <h4 style="font-family: 'Playfair Display', Georgia, serif; margin: 1.5rem 0 0.75rem;">
              Per-Sample Classifications
            </h4>
            <div class="per-sample-list">
              ${this.interpretation.per_sample.map(
                ps => html`
                  <div class="per-sample">
                    <strong>${ps.sample_id}:</strong>
                    <em>${ps.classification}</em> — ${ps.rationale}
                  </div>
                `
              )}
            </div>
          `
        : html`<div class="placeholder">Waiting for interpretation...</div>`}

      <!-- Citations -->
      ${this.interpretation && this.interpretation.citations.length > 0
        ? html`
            <h3 class="section-title">References</h3>
            <ul class="citations-list">
              ${this.interpretation.citations.map(
                c => html`
                  <li class="citation-item ${c.verified ? 'verified' : 'unverified'}">
                    ${c.authors} (${c.year || 'n.d.'}).
                    <em>${c.title}</em>.
                    ${c.venue || ''}.
                    ${c.doi_or_url ? html`<a href="${c.doi_or_url}" target="_blank">${c.doi_or_url}</a>` : ''}
                    <span class="${c.verified ? 'verified-badge' : 'unverified-badge'}">
                      ${c.verified ? '[VERIFIED]' : '[UNVERIFIED]'}
                    </span>
                  </li>
                `
              )}
            </ul>
          `
        : null}
    `;
  }
}
