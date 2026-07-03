import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

interface PlotlyType {
  newPlot(el: HTMLElement, data: unknown[], layout: unknown, config: unknown): void;
  purge(el: HTMLElement): void;
}

@customElement('data-chart')
export class DataChart extends LitElement {
  @property({ type: Object })
  figureJson: object | null = null;

  @property({ type: String })
  chartTitle = '';

  private _container: HTMLElement | null = null;

  static styles = css`
    :host {
      display: block;
      min-height: 300px;
    }
    .chart-container {
      width: 100%;
      height: 400px;
    }
    .placeholder {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 300px;
      background: var(--sl-color-neutral-50);
      border: 3px dashed var(--sl-color-neutral-200);
      color: var(--sl-color-neutral-400);
      font-style: italic;
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.1rem;
    }
  `;

  protected firstUpdated() {
    this._container = this.shadowRoot!.querySelector('.chart-container');
    this._renderChart();
  }

  updated(changedProperties: Map<string, unknown>) {
    if (changedProperties.has('figureJson')) {
      this._renderChart();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._container) {
      try {
        const pw = (window as unknown as Record<string, unknown>);
        (pw.Plotly as PlotlyType | undefined)?.purge(this._container);
      } catch {
        // ignore purge errors
      }
    }
  }

  private _renderChart() {
    if (!this._container || !this.figureJson) return;

    const pw = (window as unknown as Record<string, unknown>);
    const Plotly = pw.Plotly as PlotlyType | undefined;
    if (!Plotly) {
      console.warn('Plotly not loaded');
      return;
    }

    const fig = this.figureJson as {
      data?: unknown[];
      layout?: Record<string, unknown>;
    };

    if (!fig.data && !fig.layout) {
      return;
    }

    try {
      Plotly.newPlot(
        this._container,
        fig.data || [],
        {
          ...(fig.layout || {}),
          title: this.chartTitle || (fig.layout as Record<string, unknown>)?.title || '',
          autosize: true,
          font: {
            family: 'Space Grotesk, system-ui, sans-serif',
          },
        },
        {
          responsive: true,
          displayModeBar: true,
          displaylogo: false,
          modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d'],
        }
      );
    } catch (err) {
      console.error('Plotly render error:', err);
    }
  }

  render() {
    if (!this.figureJson) {
      return html`<div class="placeholder">No chart data available</div>`;
    }
    return html`<div class="chart-container"></div>`;
  }
}
