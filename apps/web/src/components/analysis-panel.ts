import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import '@shoelace-style/shoelace/dist/components/card/card.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/spinner/spinner.js';
import '@shoelace-style/shoelace/dist/components/badge/badge.js';

interface PackSummary {
  id: string;
  name: string;
  description: string | null;
  required_columns: string[];
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

@customElement('analysis-panel')
export class AnalysisPanel extends LitElement {
  @property({ type: Number })
  datasetId = 0;

  @property({ type: Array })
  datasetColumns: string[] = [];

  @state()
  private compatiblePacks: PackSummary[] = [];

  @state()
  private loadingPacks = true;

  @state()
  private analyzing = false;

  @state()
  private analysisResults: AnalysisResponse | null = null;

  @state()
  private selectedPack: string | null = null;

  @state()
  private error: string | null = null;

  static styles = css`
    :host {
      display: block;
    }

    .section-title {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.3rem;
      margin: 0 0 1rem;
    }

    .pack-card {
      border: 3px solid var(--sl-color-neutral-200);
      padding: 1rem 1.25rem;
      margin-bottom: 0.75rem;
      cursor: pointer;
      transition: all 0.15s;
      background: var(--sl-color-neutral-50);
      box-shadow: 3px 3px 0 0 var(--sl-color-neutral-100);
    }

    .pack-card:hover {
      transform: translate(-1px, -1px);
      box-shadow: 5px 5px 0 0 var(--sl-color-neutral-200);
    }

    .pack-card.selected {
      border-color: var(--sl-color-primary-500);
      box-shadow: 4px 4px 0 0 var(--sl-color-primary-200);
      background: var(--sl-color-primary-50);
    }

    .pack-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.35rem;
    }

    .pack-name {
      font-weight: 700;
      font-size: 1rem;
    }

    .pack-desc {
      color: var(--sl-color-neutral-600);
      font-size: 0.9rem;
      margin: 0 0 0.5rem;
    }

    .pack-requires {
      font-size: 0.8rem;
      color: var(--sl-color-neutral-500);
      margin: 0 0 0.75rem;
    }

    .proxy-table-wrapper {
      margin-top: 1.5rem;
      border: 3px solid var(--sl-color-neutral-200);
      overflow-x: auto;
      max-width: 100%;
      box-shadow: 4px 4px 0 0 var(--sl-color-neutral-100);
    }

    .proxy-table {
      min-width: 100%;
      width: auto;
      border-collapse: collapse;
    }

    .proxy-table th, .proxy-table td {
      padding: 0.6rem 0.75rem;
      text-align: left;
      border-bottom: 2px solid var(--sl-color-neutral-100);
      white-space: nowrap;
    }

    .proxy-table th {
      background: var(--sl-color-neutral-100);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-size: 0.8rem;
      position: sticky;
      top: 0;
    }

    .proxy-table .numeric {
      text-align: right;
      font-family: 'JetBrains Mono', monospace;
      font-weight: 500;
    }

    .proxy-table .null-value {
      color: var(--sl-color-neutral-400);
      font-style: italic;
    }

    .results-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-top: 1.5rem;
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
      this._fetchCompatiblePacks();
    }
  }

  private async _fetchCompatiblePacks() {
    try {
      this.loadingPacks = true;
      const response = await fetch(`/api/v1/datasets/${this.datasetId}/compatible-packs`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      this.compatiblePacks = await response.json();
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Failed to load packs';
    } finally {
      this.loadingPacks = false;
    }
  }

  private async _runAnalysis(packId: string) {
    this.analyzing = true;
    this.error = null;
    this.selectedPack = packId;

    try {
      const response = await fetch(`/api/v1/datasets/${this.datasetId}/analyze?pack_id=${packId}`, {
        method: 'POST',
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || `Analysis failed: ${response.status}`);
      }
      this.analysisResults = await response.json();
      this.dispatchEvent(new CustomEvent('analysis-complete', {
        detail: this.analysisResults,
        bubbles: true,
        composed: true,
      }));
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Analysis failed';
    } finally {
      this.analyzing = false;
    }
  }

  private _proxyIds(): string[] {
    if (!this.analysisResults) return [];
    const ids = new Set<string>();
    for (const r of this.analysisResults.results) {
      ids.add(r.proxy_id);
    }
    return Array.from(ids);
  }

  private _sampleIds(): string[] {
    if (!this.analysisResults) return [];
    const ids = new Set<string>();
    for (const r of this.analysisResults.results) {
      ids.add(r.sample_id);
    }
    return Array.from(ids);
  }

  private _valueFor(sampleId: string, proxyId: string): number | null | undefined {
    if (!this.analysisResults) return undefined;
    return this.analysisResults.results.find(
      r => r.sample_id === sampleId && r.proxy_id === proxyId
    )?.value;
  }

  private _labelFor(proxyId: string): string {
    if (!this.analysisResults) return proxyId;
    return this.analysisResults.results.find(r => r.proxy_id === proxyId)?.label || proxyId;
  }

  render() {
    return html`
      <h3 class="section-title">Analysis Packs</h3>

      ${this.loadingPacks
        ? html`<sl-spinner></sl-spinner>`
        : this.compatiblePacks.length === 0
        ? html`<p style="color: var(--sl-color-neutral-500);">No compatible analysis packs for this dataset.</p>`
        : html`
            ${this.compatiblePacks.map(pack => html`
              <div class="pack-card ${this.selectedPack === pack.id ? 'selected' : ''}">
                <div class="pack-header">
                  <span class="pack-name">${pack.name}</span>
                  ${this.selectedPack === pack.id
                    ? html`<sl-badge variant="primary" pill>Selected</sl-badge>`
                    : html`<sl-badge variant="success" pill>Compatible</sl-badge>`}
                </div>
                ${pack.description ? html`<p class="pack-desc">${pack.description}</p>` : ''}
                <p class="pack-requires">Requires: ${pack.required_columns.join(', ')}</p>
                ${this.analyzing && this.selectedPack === pack.id
                  ? html`<sl-spinner></sl-spinner>`
                  : html`<sl-button @click="${() => this._runAnalysis(pack.id)}" variant="primary">
                      ▤ Run Analysis
                    </sl-button>`}
              </div>
            `)}
          `}

      ${this.error ? html`<div class="error">${this.error}</div>` : null}

      ${this.analysisResults ? this._renderResults() : null}
    `;
  }

  private _renderResults() {
    if (!this.analysisResults) return html``;
    const proxyIds = this._proxyIds();
    const sampleIds = this._sampleIds();

    return html`
      <div class="results-header">
        <h3 style="font-family: 'Playfair Display', Georgia, serif; font-size: 1.1rem; margin: 0;">Results</h3>
        <sl-badge variant="neutral" pill>v${this.analysisResults.version}</sl-badge>
      </div>
      <div class="proxy-table-wrapper">
        <table class="proxy-table">
          <thead>
            <tr>
              <th>Sample ID</th>
              ${proxyIds.map(pid => html`<th>${this._labelFor(pid)}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${sampleIds.map(sid => html`
              <tr>
                <td style="font-weight: 600;">${sid}</td>
                ${proxyIds.map(pid => {
                  const val = this._valueFor(sid, pid);
                  return html`
                    <td class="numeric">
                      ${val !== null && val !== undefined
                        ? val.toFixed(4)
                        : html`<span class="null-value">N/A</span>`}
                    </td>
                  `;
                })}
              </tr>
            `)}
          </tbody>
        </table>
      </div>
    `;
  }
}
