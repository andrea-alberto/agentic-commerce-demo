import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Checkout } from '../models';

@Component({
  selector: 'app-lcm-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="lcm-backdrop" (click)="onBackdropClick($event)">
      <div class="lcm-dialog" (click)="$event.stopPropagation()">
        <!-- Simulation Notice Banner -->
        <div class="simulation-banner">
          <span class="sim-badge">🧪 SIMULAZIONE DIDATTICA</span>
          <span class="sim-text">Local Credential Manager (LCM) • GDG DevFest 2026</span>
        </div>

        <!-- Header: Simulated Credential Manager Style -->
        <div class="lcm-header">
          <div class="lcm-brand">
            <svg class="g-icon" viewBox="0 0 24 24" width="22" height="22">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
            </svg>
            <div>
              <h4 class="lcm-title">Simulatore Credential Manager (AP2)</h4>
              <span class="lcm-subtitle">Emulazione Trusted Surface Client • FIDO2 Passkey</span>
            </div>
          </div>
          <button class="btn-close" (click)="onCancel()" [disabled]="authStep === 'scanning'">✕</button>
        </div>

        <!-- Body -->
        <div class="lcm-body">
          <!-- Summary Box with Dynamic Linking -->
          <div class="summary-card">
            <div class="merchant-row">
              <span class="merchant-badge">🏪 Esercente Verificato</span>
              <span class="merchant-domain">milano-centrale.ucp.dev</span>
            </div>
            <div class="amount-row">
              <span class="amount-label">Totale Autorizzato:</span>
              <span class="amount-val">€ {{ formatCurrency(getGrandTotal()) }}</span>
            </div>
            <div class="details-chips">
              <span class="chip">📍 {{ getDestinationSummary() }}</span>
              <span class="chip">⏱️ {{ getFulfillmentTimeSummary() }}</span>
              <span class="chip">🛍️ {{ checkout.line_items.length }} articoli nel carrello</span>
            </div>
          </div>

          <!-- Payment Instrument Card -->
          <div class="instrument-box">
            <div class="card-icon">💳</div>
            <div class="card-info">
              <div class="card-name">Mastercard Debit •••• 4242</div>
              <div class="card-sub">Mock Token Wallet Locale • Emulazione KeyMint/TPM Hardware</div>
            </div>
            <span class="verified-pill">Simulato</span>
          </div>

          <!-- Biometric Authenticator Visual -->
          <div class="biometric-area" [ngClass]="authStep">
            @if (authStep === 'idle') {
              <div class="fingerprint-wrapper" (click)="onAuthorize()">
                <div class="fingerprint-ring"></div>
                <div class="fingerprint-icon">👆</div>
              </div>
              <p class="bio-prompt">Clicca per simulare il tocco dell'impronta (Firma hardware asimmetrica emulata)</p>
            } @else if (authStep === 'scanning') {
              <div class="fingerprint-wrapper scanning">
                <div class="scan-beam"></div>
                <div class="fingerprint-icon">🔐</div>
              </div>
              <p class="bio-prompt scanning-text">Emulazione firma Secure Element in corso (TPM/TEE)...</p>
            } @else if (authStep === 'success') {
              <div class="fingerprint-wrapper success">
                <div class="fingerprint-icon">✅</div>
              </div>
              <p class="bio-prompt success-text">Mandati crittografici AP2 generati e firmati!</p>
            }
          </div>

          <!-- Developer Inspector Toggle (For DevFest talk) -->
          <div class="inspector-toggle-row">
            <button type="button" class="btn-toggle-inspector" (click)="toggleInspector()">
              <span>{{ showInspector ? '▼ Nascondi' : '▶ Ispeziona' }} Mandati Crittografici AP2 (SD-JWT)</span>
              <span class="dev-badge">Dev View</span>
            </button>
          </div>

          <!-- Collapsible Inspector Content -->
          @if (showInspector) {
            <div class="jwt-inspector">
              <div class="jwt-block">
                <span class="jwt-title">📜 Cart Mandate (SD-JWT):</span>
                <pre class="jwt-code">{{ getCartMandatePreview() }}</pre>
              </div>
              <div class="jwt-block">
                <span class="jwt-title">🔑 Payment Mandate (SD-JWT con Dynamic Linking):</span>
                <pre class="jwt-code">{{ getPaymentMandatePreview() }}</pre>
              </div>
            </div>
          }

          <!-- Educational Disclaimer Note -->
          <div class="disclaimer-note">
            ⚠️ <strong>Nota per il pubblico:</strong> Questa interfaccia emula a scopo didattico la <em>Trusted Surface</em> del sistema operativo (W3C Digital Credentials API / Android Credential Manager) per mostrare l'autorizzazione crittografica non-ripudiabile dei Mandati AP2.
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="lcm-footer">
          <button class="btn btn-secondary" (click)="onCancel()" [disabled]="authStep === 'scanning'">
            Annulla
          </button>
          <button
            class="btn btn-primary"
            (click)="onAuthorize()"
            [disabled]="authStep === 'scanning' || authStep === 'success'"
          >
            @if (authStep === 'scanning') {
              Verifica in corso...
            } @else if (authStep === 'success') {
              Completato!
            } @else {
              👆 Conferma con Impronta / Passkey
            }
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .lcm-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(15, 23, 42, 0.65);
      backdrop-filter: blur(4px);
      z-index: 9999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      animation: fadeIn 0.2s ease;
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    .lcm-dialog {
      background: #ffffff;
      border-radius: 18px;
      width: 100%;
      max-width: 480px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      animation: slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes slideUp {
      from { transform: translateY(24px) scale(0.96); opacity: 0; }
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
      letter-spacing: 0.04em;
    }
    .sim-text {
      font-weight: 600;
    }
    .lcm-header {
      padding: 16px 20px;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .lcm-brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .lcm-title {
      margin: 0;
      font-size: 0.95rem;
      font-weight: 700;
      color: #1e293b;
    }
    .lcm-subtitle {
      font-size: 0.72rem;
      color: #64748b;
      font-weight: 500;
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
      color: #334155;
      background: #e2e8f0;
    }
    .lcm-body {
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      max-height: 75vh;
      overflow-y: auto;
    }
    .summary-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .merchant-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .merchant-badge {
      font-size: 0.73rem;
      font-weight: 700;
      color: #0f766e;
      background: #ccfbf1;
      padding: 2px 8px;
      border-radius: 9999px;
    }
    .merchant-domain {
      font-size: 0.73rem;
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
      font-size: 0.85rem;
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
      font-size: 0.72rem;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 3px 8px;
      color: #475569;
      font-weight: 500;
    }
    .instrument-box {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
    }
    .card-icon {
      font-size: 1.4rem;
    }
    .card-info {
      flex: 1;
    }
    .card-name {
      font-size: 0.84rem;
      font-weight: 700;
      color: #0f172a;
    }
    .card-sub {
      font-size: 0.68rem;
      color: #64748b;
    }
    .verified-pill {
      font-size: 0.68rem;
      font-weight: 700;
      color: #15803d;
      background: #dcfce7;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .biometric-area {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px 12px;
      background: #eff6ff;
      border: 1px dashed #93c5fd;
      border-radius: 12px;
      text-align: center;
      gap: 8px;
    }
    .fingerprint-wrapper {
      width: 56px;
      height: 56px;
      background: #3b82f6;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      position: relative;
      transition: transform 0.15s ease, background 0.2s ease;
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
    }
    .fingerprint-wrapper:hover {
      transform: scale(1.05);
    }
    .fingerprint-icon {
      font-size: 1.6rem;
    }
    .fingerprint-wrapper.scanning {
      background: #f59e0b;
      box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
      animation: pulse 1s infinite alternate;
    }
    @keyframes pulse {
      from { transform: scale(0.98); }
      to { transform: scale(1.06); }
    }
    .fingerprint-wrapper.success {
      background: #16a34a;
      box-shadow: 0 4px 12px rgba(22, 163, 74, 0.4);
    }
    .bio-prompt {
      margin: 0;
      font-size: 0.78rem;
      font-weight: 600;
      color: #1e40af;
      max-width: 280px;
    }
    .scanning-text {
      color: #b45309;
    }
    .success-text {
      color: #15803d;
    }
    .inspector-toggle-row {
      display: flex;
      justify-content: center;
      margin-top: 2px;
    }
    .btn-toggle-inspector {
      background: none;
      border: none;
      font-size: 0.75rem;
      color: #2563eb;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 8px;
      border-radius: 6px;
    }
    .btn-toggle-inspector:hover {
      background: #f1f5f9;
    }
    .dev-badge {
      font-size: 0.65rem;
      background: #e0e7ff;
      color: #3730a3;
      padding: 1px 5px;
      border-radius: 4px;
      text-transform: uppercase;
      font-weight: 700;
    }
    .jwt-inspector {
      background: #0f172a;
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      border: 1px solid #334155;
    }
    .jwt-block {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .jwt-title {
      font-size: 0.7rem;
      font-weight: 700;
      color: #38bdf8;
      font-family: monospace;
    }
    .jwt-code {
      margin: 0;
      font-family: 'Consolas', 'Courier New', monospace;
      font-size: 0.68rem;
      color: #cbd5e1;
      background: #1e293b;
      padding: 8px;
      border-radius: 6px;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .disclaimer-note {
      font-size: 0.68rem;
      color: #64748b;
      background: #f1f5f9;
      padding: 8px 12px;
      border-radius: 8px;
      border: 1px dashed #cbd5e1;
      line-height: 1.35;
      margin-top: 4px;
    }
    .lcm-footer {
      padding: 14px 20px;
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }
    .btn {
      padding: 10px 18px;
      border-radius: 8px;
      font-size: 0.84rem;
      font-weight: 700;
      border: none;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .btn-secondary {
      background: #e2e8f0;
      color: #334155;
    }
    .btn-secondary:hover:not(:disabled) {
      background: #cbd5e1;
    }
    .btn-primary {
      background: #1a73e8;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .btn-primary:hover:not(:disabled) {
      background: #1557b0;
    }
    .btn:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
  `]
})
export class LcmModalComponent implements OnInit {
  @Input({ required: true }) checkout!: Checkout;
  @Output() confirm = new EventEmitter<{
    mandateId: string;
    cartMandateJwt: string;
    paymentMandateJwt: string;
  }>();
  @Output() cancel = new EventEmitter<void>();

  authStep: 'idle' | 'scanning' | 'success' = 'idle';
  showInspector = false;

  ngOnInit(): void {
    this.authStep = 'idle';
  }

  formatCurrency(cents: number): string {
    return (cents / 100).toFixed(2);
  }

  getGrandTotal(): number {
    const tot = this.checkout.totals.find((t) => t.type === 'total');
    return tot ? tot.amount : 0;
  }

  getFulfillmentMethods(): any[] {
    if (!this.checkout?.fulfillment) return [];
    const f: any = this.checkout.fulfillment;
    if (Array.isArray(f.methods)) return f.methods;
    if (f.root && Array.isArray(f.root.methods)) return f.root.methods;
    return [];
  }

  getDestinationSummary(): string {
    const methods = this.getFulfillmentMethods();
    if (methods.length > 0 && methods[0].destinations && methods[0].destinations.length > 0) {
      const rawDest: any = methods[0].destinations[0];
      const dest = rawDest.root || rawDest;
      return dest.extended_address || dest.street_address || 'Milano Centrale';
    }
    return 'Stazione Milano Centrale';
  }

  getFulfillmentTimeSummary(): string {
    const methods = this.getFulfillmentMethods();
    if (methods && methods.length > 0 && methods[0].groups && methods[0].groups.length > 0) {
      const g = methods[0].groups[0];
      const opt = g.options?.find((o: any) => o.id === g.selected_option_id);
      if (opt?.earliest_fulfillment_time) {
        try {
          const dt = new Date(opt.earliest_fulfillment_time);
          if (!isNaN(dt.getTime())) {
            return `Finestra: ${dt.toTimeString().substring(0, 5)}`;
          }
        } catch (_) {}
      }
    }
    return 'Finestra confermata';
  }

  toggleInspector(): void {
    this.showInspector = !this.showInspector;
  }

  getCartMandatePreview(): string {
    const cartObj = {
      iss: 'did:key:z6MkuDevicePasskeyLCM_Milano_Centrale',
      aud: 'https://milano-centrale.ucp.dev',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 900,
      type: 'ap2:CartMandate',
      cart_id: this.checkout.id,
      cart_hash: `sha256:${this.checkout.id.substring(0, 8)}...8a4f`,
      currency: 'EUR',
      authorized_amount: this.getGrandTotal(),
      fulfillment_binding: this.getDestinationSummary(),
      hardware_attestation: 'Android-KeyMint-FIDO2-L3-SecureEnclave',
    };
    return JSON.stringify(cartObj, null, 2);
  }

  getPaymentMandatePreview(): string {
    const paymentObj = {
      iss: 'did:key:z6MkuDevicePasskeyLCM_Milano_Centrale',
      aud: 'did:web:payment-processor.ucp.dev',
      iat: Math.floor(Date.now() / 1000),
      type: 'ap2:PaymentMandate',
      payment_instrument: {
        id: 'instr_devfest_card_01',
        brand: 'Mastercard',
        last_digits: '4242',
      },
      dynamic_linking_hash: `sha256:cart-${this.checkout.id.substring(0, 8)}`,
      biometric_auth_type: 'user-presence-biometric-touchid',
      liability_shift: 'FIDO2_SCA_EXEMPT_DELEGATED',
    };
    return JSON.stringify(paymentObj, null, 2);
  }

  onAuthorize(): void {
    if (this.authStep !== 'idle') return;
    this.authStep = 'scanning';

    // Simulate real on-device cryptographic signing on Secure Enclave
    setTimeout(() => {
      this.authStep = 'success';
      setTimeout(() => {
        const mandateId = `mandate_ap2_${crypto.randomUUID().substring(0, 8)}`;
        this.confirm.emit({
          mandateId,
          cartMandateJwt: btoa(this.getCartMandatePreview()),
          paymentMandateJwt: btoa(this.getPaymentMandatePreview()),
        });
      }, 700);
    }, 1300);
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
