import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import '@shoelace-style/shoelace/dist/components/card/card.js';
import '@shoelace-style/shoelace/dist/components/spinner/spinner.js';
import '@shoelace-style/shoelace/dist/components/badge/badge.js';

interface DatasetDetailData {
  dataset_id: number;
  name: string;
  status: string;
  columns: string[];
  rows: Record<string, string | number | null>[];
}

@customElement('dataset-detail')
export class DatasetDetail extends LitElement {
  @property({ type: Number })
  datasetId = 0;

  @state()
  private detailData: DatasetDetailData | null = null;

  @state()
  private loading = true;

  @state()
  private error: string | null = null;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      min-width: 0;
    }

    .header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1rem;
      flex-wrap: wrap;
    }

    h2 {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.3rem;
      margin: 0;
    }

    .table-wrapper {
      border: 3px solid var(--sl-color-neutral-900);
      overflow-x: auto;
      width: 100%;
      box-shadow: 5px 5px 0 0 var(--sl-color-neutral-900);
    }

    .table-wrapper::-webkit-scrollbar {
      height: 12px;
    }

    .table-wrapper::-webkit-scrollbar-track {
      background: var(--sl-color-neutral-100);
    }

    .table-wrapper::-webkit-scrollbar-thumb {
      background: var(--sl-color-neutral-500);
      border: 2px solid var(--sl-color-neutral-100);
    }

    table {
      min-width: 100%;
      width: max-content;
      border-collapse: collapse;
    }

    th, td {
      padding: 0.65rem 1rem;
      text-align: left;
      border-bottom: 2px solid var(--sl-color-neutral-200);
      border-right: 2px solid var(--sl-color-neutral-100);
      white-space: nowrap;
    }

    th:last-child, td:last-child {
      border-right: none;
    }

    th {
      background: var(--sl-color-neutral-900);
      color: var(--sl-color-neutral-50);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-size: 0.75rem;
      position: sticky;
      top: 0;
      border-bottom: 3px solid var(--sl-color-neutral-900);
    }

    tr:nth-child(even) td {
      background: var(--sl-color-neutral-100);
    }

    tr:hover td {
      background: var(--sl-color-primary-200);
    }

    .numeric {
      text-align: right;
      font-family: 'JetBrains Mono', monospace;
      font-weight: 500;
    }

    .null-value {
      color: var(--sl-color-neutral-400);
      font-style: italic;
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
      this._fetchDataset();
    }
  }

  private async _fetchDataset() {
    try {
      this.loading = true;
      this.error = null;

      const response = await fetch(`/api/v1/datasets/${this.datasetId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      this.detailData = await response.json();
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Failed to load dataset';
      console.error('Failed to load dataset:', err);
    } finally {
      this.loading = false;
    }
  }

  render() {
    if (this.loading) {
      return html`<sl-spinner></sl-spinner>`;
    }

    if (this.error) {
      return html`<div class="error">Error: ${this.error}</div>`;
    }

    if (!this.detailData) {
      return html`<p style="color: var(--sl-color-neutral-500);">No dataset selected.</p>`;
    }

    return html`
      <div class="header">
        <h2>${this.detailData.name}</h2>
        <sl-badge variant="${this.detailData.status === 'mapped' ? 'success' : 'warning'}">
          ${this.detailData.status}
        </sl-badge>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              ${this.detailData.columns.map(col => html`<th>${col}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${this.detailData.rows.map(row => html`
              <tr>
                ${this.detailData!.columns.map(col => {
                  const value = row[col];
                  const isNumeric = typeof value === 'number';
                  return html`<td class="${isNumeric ? 'numeric' : ''}">${value !== null && value !== undefined ? value : html`<span class="null-value">—</span>`}</td>`;
                })}
              </tr>
            `)}
          </tbody>
        </table>
      </div>
    `;
  }
}
