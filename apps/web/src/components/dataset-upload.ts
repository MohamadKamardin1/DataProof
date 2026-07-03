import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import '@shoelace-style/shoelace/dist/components/card/card.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/select/select.js';
import '@shoelace-style/shoelace/dist/components/option/option.js';
import '@shoelace-style/shoelace/dist/components/spinner/spinner.js';
import '@shoelace-style/shoelace/dist/components/alert/alert.js';

interface ColumnMapping {
  name: string;
  role: string;
  confidence: number;
  unit: string | null;
  data_type: string | null;
}

interface UploadResponse {
  dataset_id: number;
  name: string;
  status: string;
  detected_schema: ColumnMapping[];
  s3_key: string;
}

interface ConfirmMappingRequest {
  mappings: ColumnMapping[];
}

@customElement('dataset-upload')
export class DatasetUpload extends LitElement {
  @state()
  private isDragging = false;

  @state()
  private uploading = false;

  @state()
  private error: string | null = null;

  @state()
  private uploadResult: UploadResponse | null = null;

  @state()
  private editedMappings: ColumnMapping[] = [];

  @state()
  private confirming = false;

  static styles = css`
    :host {
      display: block;
      max-width: 800px;
      margin: 0 auto;
    }

    h2 {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.8rem;
      margin: 0 0 0.25rem;
    }

    .subtitle {
      color: var(--sl-color-neutral-500);
      margin: 0 0 1.5rem;
      font-size: 0.95rem;
    }

    .drop-zone {
      border: 3px dashed var(--sl-color-neutral-300);
      padding: 3rem 2rem;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      background: var(--sl-color-neutral-50);
      box-shadow: 4px 4px 0 0 var(--sl-color-neutral-100);
    }

    .drop-zone.dragging {
      border-color: var(--sl-color-primary-500);
      background: var(--sl-color-primary-50);
      border-style: solid;
      box-shadow: 6px 6px 0 0 var(--sl-color-primary-200);
    }

    .drop-zone:hover {
      border-color: var(--sl-color-primary-500);
      box-shadow: 6px 6px 0 0 var(--sl-color-primary-100);
    }

    .drop-zone-icon {
      font-size: 2.5rem;
      margin-bottom: 0.75rem;
      display: block;
    }

    .drop-zone p {
      margin: 0.25rem 0;
      color: var(--sl-color-neutral-600);
    }

    .drop-zone .main-text {
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--sl-color-neutral-800);
    }

    .mapping-section {
      margin-top: 2rem;
    }

    .mapping-section h3 {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.3rem;
      margin: 0 0 0.5rem;
    }

    .mapping-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
      border: 3px solid var(--sl-color-neutral-200);
    }

    .mapping-table th,
    .mapping-table td {
      padding: 0.75rem;
      text-align: left;
      border-bottom: 2px solid var(--sl-color-neutral-100);
    }

    .mapping-table th {
      background: var(--sl-color-neutral-100);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-size: 0.8rem;
    }

    .confidence {
      font-size: 0.85rem;
      font-weight: 600;
    }

    .actions {
      margin-top: 1.5rem;
      display: flex;
      gap: 1rem;
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

  render() {
    return html`
      <h2>Upload Dataset</h2>
      <p class="subtitle">Drag and drop a CSV or XLSX file, or click to browse.</p>
      ${this.uploadResult
        ? this._renderMappingEditor()
        : this._renderDropZone()}
    `;
  }

  private _renderDropZone() {
    return html`
      <div
        class="drop-zone ${this.isDragging ? 'dragging' : ''}"
        @dragover="${this._onDragOver}"
        @dragleave="${this._onDragLeave}"
        @drop="${this._onDrop}"
        @click="${this._onClick}"
      >
        ${this.uploading
          ? html`<sl-spinner style="font-size: 2rem;"></sl-spinner><p>Uploading...</p>`
          : html`
              <span class="drop-zone-icon">⬆</span>
              <p class="main-text">Drop your file here</p>
              <p>or click to browse — CSV or XLSX</p>
            `}
      </div>
      <input
        type="file"
        id="fileInput"
        style="display: none;"
        accept=".csv,.xlsx"
        @change="${this._onFileSelected}"
      />
      ${this.error ? html`<div class="error">${this.error}</div>` : null}
    `;
  }

  private _renderMappingEditor() {
    if (!this.uploadResult) return html``;

    return html`
      <div class="mapping-section">
        <h3>${this.uploadResult.name}</h3>
        <p style="color: var(--sl-color-neutral-500); margin: 0 0 1rem;">
          Review and adjust the column mapping before confirming.
        </p>
        <table class="mapping-table">
          <thead>
            <tr>
              <th>Column</th>
              <th>Role</th>
              <th>Confidence</th>
              <th>Unit</th>
            </tr>
          </thead>
          <tbody>
            ${this.editedMappings.map(
              (mapping, index) => html`
                <tr>
                  <td style="font-weight: 600;">${mapping.name}</td>
                  <td>
                    <sl-select
                      value="${mapping.role}"
                      @sl-change="${(e: Event) => this._updateRole(index, (e.target as HTMLSelectElement).value)}"
                      size="small"
                    >
                      <sl-option value="sample_id">Sample ID</sl-option>
                      <sl-option value="measurement">Measurement</sl-option>
                      <sl-option value="ignore">Ignore</sl-option>
                    </sl-select>
                  </td>
                  <td class="confidence">${(mapping.confidence * 100).toFixed(0)}%</td>
                  <td>${mapping.unit || '—'}</td>
                </tr>
              `
            )}
          </tbody>
        </table>
        <div class="actions">
          <sl-button
            variant="primary"
            @click="${this._confirmMapping}"
            ?loading="${this.confirming}"
          >
            ⚇ Confirm Mapping
          </sl-button>
          <sl-button @click="${this._reset}">Cancel</sl-button>
        </div>
      </div>
      ${this.error ? html`<div class="error">${this.error}</div>` : null}
    `;
  }

  private _onDragOver(e: DragEvent) {
    e.preventDefault();
    this.isDragging = true;
  }

  private _onDragLeave() {
    this.isDragging = false;
  }

  private _onDrop(e: DragEvent) {
    e.preventDefault();
    this.isDragging = false;
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      this._uploadFile(files[0]);
    }
  }

  private _onClick() {
    const input = this.shadowRoot?.getElementById('fileInput') as HTMLInputElement;
    if (input) {
      input.click();
    }
  }

  private _onFileSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this._uploadFile(input.files[0]);
    }
  }

  private async _uploadFile(file: File) {
    this.uploading = true;
    this.error = null;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/v1/datasets/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Upload failed: ${response.status}`);
      }

      const data: UploadResponse = await response.json();
      this.uploadResult = data;
      this.editedMappings = [...data.detected_schema];
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Upload failed';
      console.error('Upload failed:', err);
    } finally {
      this.uploading = false;
    }
  }

  private _updateRole(index: number, role: string) {
    this.editedMappings = this.editedMappings.map((m, i) =>
      i === index ? { ...m, role } : m
    );
  }

  private async _confirmMapping() {
    if (!this.uploadResult) return;

    this.confirming = true;
    this.error = null;

    try {
      const request: ConfirmMappingRequest = {
        mappings: this.editedMappings,
      };

      const response = await fetch(`/api/v1/datasets/${this.uploadResult.dataset_id}/confirm-mapping`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Confirm failed: ${response.status}`);
      }

      const data = await response.json();
      this.dispatchEvent(new CustomEvent('dataset-confirmed', {
        detail: { datasetId: data.dataset_id },
        bubbles: true,
        composed: true,
      }));
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Confirm mapping failed';
      console.error('Confirm mapping failed:', err);
    } finally {
      this.confirming = false;
    }
  }

  private _reset() {
    this.uploadResult = null;
    this.editedMappings = [];
    this.error = null;
  }
}
