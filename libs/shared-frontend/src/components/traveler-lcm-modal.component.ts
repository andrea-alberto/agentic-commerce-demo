// Copyright 2026 UCP Authors / GDG DevFest Milano 2026
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface ClientAP2MandateResult {
  mandate_id: string;
  max_authorized_cents: number;
  signature_scheme: string;
  token_jwt: string;
  cart_mandate_jwt: string;
  payment_mandate_jwt: string;
  signed_at: string;
}

@Component({
  selector: 'lib-traveler-lcm-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="lcm-backdrop" (click)="onBackdropClick($event)">
      <div class="lcm-dialog" (click)="$event.stopPropagation()">
        <!-- SIMULATION BANNER -->
        <div class="simulation-banner">
          <span class="sim-badge">🛡️ AP2 HUMAN-PRESENT SPEC</span>
          <span class="sim-text">Local Credential Manager (LCM) • Passkey FIDO2 Client Surface</span>
        </div>

        <!-- HEADER -->
        <div class="lcm-header">
          <div class="lcm-brand">
            <span class="g-shield">🔐</span>
            <div>
              <h4 class="lcm-title">Conferma Pagamento e Mandato AP2</h4>
              <span class="lcm-subtitle">Trusted OS Surface · Autorizzazione Biometrica del Titolare</span>
            </div>
          </div>
          <button class="btn-close" (click)="onCancel()" [disabled]="authStep === 'scanning'">✕</button>
        </div>

        <!-- BODY -->
        <div class="lcm-body">
          <!-- SUMMARY CARD -->
          <div class="summary-card">
            <div class="merchant-row">
              <span class="merchant-badge">🏪 Esercente Verificato UCP</span>
              <span class="merchant-domain">milano-centrale.ucp.dev</span>
            </div>
            <div class="amount-row">
              <span class="amount-label">Totale Negoziato dall'Agente:</span>
              <strong class="amount-val">€{{ formatCents(challenge?.total_cents) }}</strong>
            </div>
            <div class="details-chips">
              <span class="chip">📍 {{ getDestinationSummary() }}</span>
              <span class="chip">🛍️ {{ challenge?.order_summary_title || challenge?.chosen_prod?.name || 'Pranzo Viaggiatore' }}</span>
              <span class="chip">⏱️ Pronto prima di {{ challenge?.ticket?.departure_time || '13:10' }}</span>
            </div>

            @if (getItems().length > 1) {
              <div class="modal-items-breakdown">
                <span class="breakdown-tag">Articoli Inclusi nel Mandato ({{ getItems().length }}):</span>
                <div class="breakdown-list">
                  @for (it of getItems(); track it.id || it.title) {
                    <div class="breakdown-row">
                      <span class="it-title">📦 {{ it.quantity || 1 }}x {{ it.title || it.name }}</span>
                      <span class="it-price">€{{ formatCents(it.price_cents) }}</span>
                    </div>
                  }
                </div>
              </div>
            }
          </div>

          <!-- PAYMENT INSTRUMENT / WALLET -->
          <div class="instrument-box">
            <div class="card-icon">💳</div>
            <div class="card-info">
              <div class="card-name">Google Pay · CartaFRECCIA Visa •••• 8849</div>
              <div class="card-sub">Hardware KeyMint / TPM Secure Enclave (Passkey P-256)</div>
            </div>
            <span class="verified-pill">Attivo</span>
          </div>

          <!-- BIOMETRIC AREA -->
          <div class="biometric-area" [ngClass]="authStep">
            @if (authStep === 'idle') {
              <div class="fingerprint-wrapper" (click)="onAuthorize()">
                <div class="fingerprint-ring"></div>
                <div class="fingerprint-icon">👆</div>
              </div>
              <p class="bio-prompt">Tocca l'impronta per autorizzare la spesa (Generazione Cart Mandate SD-JWT on-device)</p>
            } @else if (authStep === 'scanning') {
              <div class="fingerprint-wrapper scanning">
                <div class="scan-beam"></div>
                <div class="fingerprint-icon">🔐</div>
              </div>
              <p class="bio-prompt scanning-text">Firma hardware in corso nel Secure Enclave (Passkey P-256)...</p>
            } @else if (authStep === 'success') {
              <div class="fingerprint-wrapper success">
                <div class="fingerprint-icon">✅</div>
              </div>
              <p class="bio-prompt success-text">Mandati AP2 firmati con successo!</p>
            }
          </div>

          <!-- DEVELOPER INSPECTOR TOGGLE (FOR TALK) -->
          <div class="inspector-toggle-row">
            <button type="button" class="btn-toggle-inspector" (click)="showInspector = !showInspector">
              <span>{{ showInspector ? '▼ Nascondi' : '▶ Ispeziona' }} Mandato Crittografico AP2 (SD-JWT generato dal Client)</span>
            </button>
          </div>

          @if (showInspector) {
            <div class="jwt-inspector">
              <div class="jwt-block">
                <span class="jwt-title">📜 Cart Mandate (SD-JWT emesso on-device):</span>
                <pre class="jwt-code">{{ getCartMandatePreview() }}</pre>
              </div>
            </div>
          }
        </div>

        <!-- FOOTER -->
        <div class="lcm-footer">
          <button type="button" class="btn btn-secondary" (click)="onCancel()" [disabled]="authStep === 'scanning'">
            Annulla
          </button>
          <button
            type="button"
            class="btn btn-primary"
            (click)="onAuthorize()"
            [disabled]="authStep === 'scanning' || authStep === 'success'"
          >
            @if (authStep === 'scanning') {
              Verifica in corso...
            } @else if (authStep === 'success') {
              Autorizzato!
            } @else {
              👆 Conferma con Passkey (€{{ formatCents(challenge?.total_cents) }})
            }
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .lcm-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(4px);
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      animation: fadeIn 0.2s ease;
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    .lcm-dialog {
      background: #ffffff;
      color: #0f172a;
      border-radius: 18px;
      width: 100%;
      max-width: 500px;
      box-shadow: 0 25px 50px rgba(0, 0, 0, 0.35);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      animation: slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes slideUp {
      from { transform: translateY(20px) scale(0.96); opacity: 0; }
      to { transform: translateY(0) scale(1); opacity: 1; }
    }
    .simulation-banner {
      background: #fef3c7;
      border-bottom: 1px solid #fde68a;
      padding: 6px 14px;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.72rem;
      color: #92400e;
    }
    .sim-badge {
      font-weight: 800;
      background: #b45309;
      color: #ffffff;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.65rem;
    }
    .lcm-header {
      padding: 14px 18px;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .lcm-brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .g-shield {
      font-size: 1.5rem;
    }
    .lcm-title {
      margin: 0;
      font-size: 0.95rem;
      font-weight: 800;
      color: #1e293b;
    }
    .lcm-subtitle {
      font-size: 0.7rem;
      color: #64748b;
    }
    .btn-close {
      background: transparent;
      border: none;
      font-size: 1.1rem;
      color: #94a3b8;
      cursor: pointer;
      padding: 4px;
      border-radius: 6px;
    }
    .btn-close:hover:not(:disabled) {
      color: #0f172a;
      background: #e2e8f0;
    }
    .lcm-body {
      padding: 16px 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 72vh;
      overflow-y: auto;
    }
    .summary-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .merchant-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .merchant-badge {
      font-size: 0.72rem;
      font-weight: 700;
      color: #0f766e;
      background: #ccfbf1;
      padding: 2px 8px;
      border-radius: 20px;
    }
    .merchant-domain {
      font-size: 0.7rem;
      color: #64748b;
      font-family: monospace;
    }
    .amount-row {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      padding: 4px 0;
      border-bottom: 1px dashed #cbd5e1;
    }
    .amount-label {
      font-size: 0.82rem;
      font-weight: 600;
      color: #334155;
    }
    .amount-val {
      font-size: 1.35rem;
      font-weight: 800;
      color: #0f172a;
    }
    .details-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 4px;
    }
    .chip {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: 6px;
      color: #334155;
      font-weight: 600;
    }
    .modal-items-breakdown {
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px dashed #cbd5e1;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }
    .breakdown-tag {
      font-size: 0.68rem;
      font-weight: 700;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .breakdown-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .breakdown-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #ffffff;
      padding: 5px 9px;
      border-radius: 6px;
      border: 1px solid #e2e8f0;
      font-size: 0.75rem;
    }
    .it-title {
      font-weight: 600;
      color: #1e293b;
    }
    .it-price {
      font-weight: 700;
      color: #1e40af;
    }
    .instrument-box {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
      padding: 8px 12px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .card-icon {
      font-size: 1.4rem;
    }
    .card-info {
      flex: 1;
    }
    .card-name {
      font-size: 0.8rem;
      font-weight: 700;
      color: #0f172a;
    }
    .card-sub {
      font-size: 0.65rem;
      color: #64748b;
    }
    .verified-pill {
      background: #dcfce7;
      color: #15803d;
      font-size: 0.65rem;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .biometric-area {
      background: #faf5ff;
      border: 1px dashed #c084fc;
      border-radius: 12px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }
    .fingerprint-wrapper {
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: #f3e8ff;
      border: 2px solid #a855f7;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      position: relative;
      transition: all 0.2s;
    }
    .fingerprint-wrapper:hover {
      transform: scale(1.08);
      background: #e9d5ff;
    }
    .fingerprint-icon {
      font-size: 1.8rem;
    }
    .bio-prompt {
      margin: 0;
      font-size: 0.75rem;
      color: #6b21a8;
      font-weight: 600;
      text-align: center;
    }
    .fingerprint-wrapper.scanning {
      border-color: #3b82f6;
      background: #eff6ff;
    }
    .fingerprint-wrapper.success {
      border-color: #10b981;
      background: #ecfdf5;
    }
    .inspector-toggle-row {
      display: flex;
      justify-content: center;
    }
    .btn-toggle-inspector {
      background: transparent;
      border: none;
      color: #6366f1;
      font-size: 0.72rem;
      font-weight: 700;
      cursor: pointer;
      text-decoration: underline;
    }
    .jwt-inspector {
      background: #0f172a;
      border-radius: 8px;
      padding: 8px 12px;
    }
    .jwt-title {
      font-size: 0.68rem;
      color: #38bdf8;
      font-weight: 700;
    }
    .jwt-code {
      margin: 4px 0 0 0;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.68rem;
      color: #93c5fd;
      max-height: 120px;
      overflow-y: auto;
      white-space: pre-wrap;
    }
    .lcm-footer {
      padding: 12px 18px;
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }
    .btn {
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 700;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
    }
    .btn-secondary {
      background: #e2e8f0;
      color: #334155;
    }
    .btn-primary {
      background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%);
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(124, 58, 237, 0.3);
    }
    .btn-primary:hover:not(:disabled) {
      box-shadow: 0 4px 12px rgba(124, 58, 237, 0.45);
    }
    .btn-primary:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  `]
})
export class TravelerLcmModalComponent {
  @Input() challenge: any = null;
  @Output() cancel = new EventEmitter<void>();
  @Output() authorized = new EventEmitter<ClientAP2MandateResult>();

  authStep: 'idle' | 'scanning' | 'success' = 'idle';
  showInspector = false;

  formatCents(cents: number | undefined): string {
    if (cents === undefined || cents === null) return '0.00';
    return (cents / 100).toFixed(2);
  }

  getItems(): any[] {
    if (this.challenge?.items && this.challenge.items.length > 0) {
      return this.challenge.items;
    }
    if (this.challenge?.chosen_prod?.items && this.challenge.chosen_prod.items.length > 0) {
      return this.challenge.chosen_prod.items;
    }
    return [];
  }

  getDestinationSummary(): string {
    if (!this.challenge) return 'Milano Centrale';
    const fl = this.challenge.fl_method || this.challenge.fulfillment?.method;
    if (fl === 'in_seat_train') {
      const t = this.challenge.ticket || {};
      return `Al posto treno: ${t.train_number || 'Frecciarossa'}, Carr. ${t.carriage || '4'}, Posto ${t.seat || '12D'}`;
    }
    if (fl === 'pickup_locker') {
      return 'Smart Locker Interrato (Box #14)';
    }
    return 'Bistrot Binario 12 (Desk Express)';
  }

  getCartMandatePreview(): string {
    const total = this.challenge?.total_cents || 1300;
    const cartObj = {
      iss: 'did:key:z6MkuDevicePasskeyLCM_MarioRossi_Client',
      aud: 'https://milano-centrale.ucp.dev',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 900,
      type: 'ap2:CartMandate',
      cart_id: this.challenge?.order_id || this.challenge?.checkout_id || 'CHK-MI-AP2',
      currency: 'EUR',
      authorized_amount_cents: total,
      fulfillment_binding: this.getDestinationSummary(),
      hardware_attestation: 'Android-KeyMint-FIDO2-L3-SecureEnclave',
    };
    return JSON.stringify(cartObj, null, 2);
  }

  onAuthorize(): void {
    if (this.authStep !== 'idle') return;
    this.authStep = 'scanning';

    setTimeout(() => {
      this.authStep = 'success';
      setTimeout(() => {
        const idSuffix = Math.random().toString(36).substring(2, 7).toUpperCase();
        const mandateId = `tok_ap2_client_${idSuffix}`;
        const total = this.challenge?.total_cents || 1300;
        
        const previewJson = this.getCartMandatePreview();
        const fakeJwt = `eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkFQMi1TRC1KV1QifQ.${btoa(previewJson).substring(0, 50)}.signature_passkey_${idSuffix}`;

        this.authorized.emit({
          mandate_id: mandateId,
          max_authorized_cents: total,
          signature_scheme: 'FIDO2_Passkey_P256',
          token_jwt: fakeJwt,
          cart_mandate_jwt: fakeJwt,
          payment_mandate_jwt: fakeJwt,
          signed_at: new Date().toISOString(),
        });
      }, 600);
    }, 1100);
  }

  onCancel(): void {
    if (this.authStep === 'scanning') return;
    this.cancel.emit();
  }

  onBackdropClick(event: MouseEvent): void {
    if (this.authStep === 'scanning') return;
    this.onCancel();
  }
}
