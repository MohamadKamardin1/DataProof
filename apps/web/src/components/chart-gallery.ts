import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import '@shoelace-style/shoelace/dist/components/spinner/spinner.js';
import './data-chart.js';

interface ChartSpec {
  figure_json: object;
  title: string;
  chart_type: string;
}

@customElement('chart-gallery')
export class ChartGallery extends LitElement {
  @property({ type: Number })
  datasetId = 0;

  @state()
  private charts: ChartSpec[] = [];

  @state()
  private loading = true;

  static styles = css`
    :host {
      display: block;
    }

    .chart-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }

    @media (min-width: 900px) {
      .chart-grid {
        grid-template-columns: 1fr 1fr;
      }
    }

    .chart-card {
      border: 3px solid var(--sl-color-neutral-900);
      background: var(--sl-color-neutral-50);
      box-shadow: 5px 5px 0 0 var(--sl-color-neutral-900);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .chart-card .chart-title {
      font-weight: 700;
      padding: 0.75rem 1rem;
      background: var(--sl-color-neutral-900);
      color: var(--sl-color-neutral-50);
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-family: 'Playfair Display', Georgia, serif;
      flex-shrink: 0;
    }

    .chart-card .chart-body {
      flex: 1;
      min-height: 0;
      padding: 0.5rem;
    }

    /* ── Proxy Comparison: full-width, scrollable ── */
    .comparison-card {
      grid-column: 1 / -1;
      border: 3px solid var(--sl-color-neutral-900);
      background: var(--sl-color-neutral-50);
      box-shadow: 5px 5px 0 0 var(--sl-color-neutral-900);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      height: 600px;
    }

    .comparison-card .chart-title {
      font-weight: 700;
      padding: 0.75rem 1rem;
      background: var(--sl-color-neutral-900);
      color: var(--sl-color-neutral-50);
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-family: 'Playfair Display', Georgia, serif;
      flex-shrink: 0;
    }

    .comparison-card .scroll-body {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
    }

    .placeholder {
      color: var(--sl-color-neutral-400);
      font-style: italic;
      text-align: center;
      padding: 2rem;
      border: 3px dashed var(--sl-color-neutral-200);
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1rem;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    this._loadCharts();
  }

  private async _loadCharts() {
    this.loading = true;
    try {
      const response = await fetch(`/api/v1/datasets/${this.datasetId}/charts?pack_id=paleoclimate_xrf`);
      if (response.ok) {
        const data = await response.json();
        this.charts = data.charts || [];
      }
    } catch {
      // charts unavailable
    } finally {
      this.loading = false;
    }
  }

  render() {
    if (this.loading) {
      return html`<sl-spinner></sl-spinner>`;
    }

    if (this.charts.length === 0) {
      return html`<div class="placeholder">Run analysis to see visualizations</div>`;
    }

    // Separate the Proxy Comparison chart from others
    const comparison = this.charts.find(c => c.title.startsWith('Proxy Comparison'));
    const others = this.charts.filter(c => !c.title.startsWith('Proxy Comparison'));

    return html`
      <div class="chart-grid">
        ${others.map(chart => html`
          <div class="chart-card">
            <div class="chart-title">${chart.title}</div>
            <div class="chart-body">
              <data-chart .figureJson="${chart.figure_json}" .chartTitle="${chart.title}"></data-chart>
            </div>
          </div>
        `)}
      </div>

      ${comparison ? html`
        <div class="comparison-card" style="margin-top: 1.5rem;">
          <div class="chart-title">${comparison.title}</div>
          <div class="scroll-body">
            <data-chart .figureJson="${comparison.figure_json}" .chartTitle="${comparison.title}"></data-chart>
          </div>
        </div>
      ` : ''}
    `;
  }
}
