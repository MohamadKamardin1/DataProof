import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import '@shoelace-style/shoelace/dist/components/card/card.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/alert/alert.js';
import '@shoelace-style/shoelace/dist/components/spinner/spinner.js';
function setToken(access: string, refresh: string): void {
  localStorage.setItem('dataproof-token', access);
  localStorage.setItem('dataproof-refresh', refresh);
}

function dispatchAuthChange(): void {
  window.dispatchEvent(new CustomEvent('auth-change', {
    detail: { authenticated: true },
  }));
}

@customElement('auth-form')
export class AuthForm extends LitElement {
  @state()
  private mode: 'login' | 'signup' = 'signup';

  @state()
  private email = '';

  @state()
  private password = '';

  @state()
  private error: string | null = null;

  @state()
  private loading = false;

  static styles = css`
    :host {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 80vh;
      padding: 2rem;
    }

    .auth-card {
      width: 100%;
      max-width: 420px;
      border: 3px solid var(--sl-color-neutral-900);
      box-shadow: 6px 6px 0 0 var(--sl-color-neutral-900);
      padding: 2rem;
      background: var(--sl-color-neutral-50);
    }

    .brand {
      text-align: center;
      margin-bottom: 2rem;
    }

    .brand-icon {
      font-size: 2rem;
    }

    .brand-name {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 1.8rem;
      font-weight: 900;
      margin: 0.25rem 0;
    }

    .brand-tagline {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--sl-color-neutral-500);
      margin: 0;
    }

    .tabs {
      display: flex;
      margin-bottom: 1.5rem;
      border: 3px solid var(--sl-color-neutral-900);
    }

    .tab {
      flex: 1;
      padding: 0.6rem;
      text-align: center;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-size: 0.85rem;
      cursor: pointer;
      background: var(--sl-color-neutral-100);
      color: var(--sl-color-neutral-500);
      transition: all 0.15s;
    }

    .tab.active {
      background: var(--sl-color-neutral-900);
      color: var(--sl-color-neutral-50);
    }

    .form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .error-msg {
      color: var(--sl-color-danger-500);
      font-weight: 600;
      font-size: 0.85rem;
      padding: 0.5rem 0.75rem;
      border: 2px solid var(--sl-color-danger-500);
      background: var(--sl-color-danger-50);
    }
  `;

  private _switchMode(mode: 'login' | 'signup') {
    this.mode = mode;
    this.error = null;
  }

  private async _submit() {
    this.error = null;
    this.loading = true;

    try {
      const endpoint = this.mode === 'signup' ? '/api/v1/auth/signup' : '/api/v1/auth/login';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: this.email,
          password: this.password,
        }),
      });

      let data: Record<string, unknown>;
      try {
        data = await res.json();
      } catch {
        this.error = `Server error (${res.status}) — is the API running?`;
        return;
      }

      if (!res.ok) {
        this.error = typeof data.detail === 'string' ? data.detail : 'Authentication failed';
        return;
      }

      setToken(data.access_token as string, data.refresh_token as string);
      dispatchAuthChange();
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Connection failed';
    } finally {
      this.loading = false;
    }
  }

  private _handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') this._submit();
  }

  render() {
    return html`
      <div class="auth-card">
        <div class="brand">
          <div class="brand-icon">◆</div>
          <h1 class="brand-name">DataProof</h1>
          <p class="brand-tagline">Scientific Data Intelligence</p>
        </div>

        <div class="tabs">
          <div class="tab ${this.mode === 'signup' ? 'active' : ''}" @click="${() => this._switchMode('signup')}">
            Sign Up
          </div>
          <div class="tab ${this.mode === 'login' ? 'active' : ''}" @click="${() => this._switchMode('login')}">
            Sign In
          </div>
        </div>

        <div class="form">
          <sl-input
            label="Email"
            type="email"
            placeholder="you@example.com"
            .value="${this.email}"
            @sl-input="${(e: CustomEvent) => { this.email = (e.target as HTMLInputElement).value; }}"
            @keydown="${this._handleKeydown}"
          ></sl-input>

          <sl-input
            label="Password"
            type="password"
            placeholder="········"
            .value="${this.password}"
            @sl-input="${(e: CustomEvent) => { this.password = (e.target as HTMLInputElement).value; }}"
            @keydown="${this._handleKeydown}"
          ></sl-input>

          ${this.error ? html`<div class="error-msg">${this.error}</div>` : ''}

          <sl-button
            variant="primary"
            size="large"
            ?loading="${this.loading}"
            ?disabled="${!this.email || !this.password}"
            @click="${this._submit}"
          >
            ${this.mode === 'signup' ? '⚇ Sign Up' : '⚇ Sign In'}
          </sl-button>
        </div>
      </div>
    `;
  }
}
