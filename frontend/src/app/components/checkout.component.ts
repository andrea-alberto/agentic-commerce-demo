import { Component, Input, inject, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Checkout, FulfillmentOption, LineItem } from '../models';
import { ChatService } from '../services/chat.service';
import { LcmModalComponent } from './lcm-modal.component';

@Component({
  selector: 'app-checkout',
  standalone: true,
  imports: [CommonModule, FormsModule, LcmModalComponent],
  template: `
    <div class="checkout-card" [class.completed]="checkout.status === 'completed'">
      <!-- Header -->
      <div class="checkout-header">
        <div class="header-title">
          <span class="icon">{{ checkout.status === 'completed' ? '✅' : '🛒' }}</span>
          <h3>{{ checkout.status === 'completed' ? 'Ordine Confermato!' : 'Riepilogo Carrello UCP' }}</h3>
        </div>
        <span class="status-badge" [ngClass]="'status-' + checkout.status">
          {{ getStatusLabel() }}
        </span>
      </div>

      <!-- Order Details if completed -->
      @if (checkout.status === 'completed' && checkout.order?.id) {
        <div class="order-id-box">
          <div class="order-id-row">
            <span class="order-id-label">Numero Ordine:</span>
            <strong class="order-id-val">{{ checkout.order!.id }}</strong>
          </div>
          <div class="order-summary-meta">
            <div class="meta-row">
              <span class="meta-icon">📥</span>
              <span><strong>Data/Ora Inserimento:</strong> {{ getPlacedDateTimeDisplay() }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-icon">🚚</span>
              <span><strong>Modalità:</strong> {{ getSelectedOptionTitle() }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-icon">⏱️</span>
              <span><strong>Consegna Richiesta:</strong> {{ getFulfillmentWindowDisplay() }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-icon">📍</span>
              <span><strong>Dettagli Consegna:</strong> {{ getDestinationDisplay() }}</span>
            </div>
          </div>
          <p class="order-note">
            Riceverai una notifica push / SMS per il tracciamento in tempo reale a Milano Centrale.
          </p>
        </div>
      }

      <!-- Cart Items -->
      <div class="items-list">
        @for (item of checkout.line_items; track item.id) {
          <div class="item-row">
            <img [src]="item.item.image_url || 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=400&q=80'" class="item-thumb" [alt]="item.item.title" />
            <div class="item-info">
              <span class="item-title">{{ item.item.title }}</span>
              <span class="item-qty">Quantità: {{ item.quantity }}</span>
            </div>
            <span class="item-price">€ {{ formatCurrency(getItemTotal(item)) }}</span>
          </div>
        }
      </div>

      <!-- Fulfillment Methods Selection (if available and not completed) -->
      @if (hasFulfillmentOptions() && checkout.status !== 'completed') {
        <div class="fulfillment-section">
          <h4 class="section-title">Modalità e Orari di Ritiro / Consegna Milano Centrale:</h4>
          <div class="fulfillment-options">
            @for (opt of getFulfillmentOptions(); track opt.id) {
              <div
                class="fulfillment-option"
                [class.selected]="opt.id === getSelectedOptionId()"
                [class.disabled]="isOptionDisabled(opt.id)"
                (click)="onSelectOption(opt.id)"
              >
                <div class="option-header">
                  <div class="option-title-row">
                    <span class="radio-indicator">{{ opt.id === getSelectedOptionId() ? '◉' : '○' }}</span>
                    <strong>{{ opt.title }}</strong>
                  </div>
                  <span class="option-cost">
                    {{ getOptionCost(opt) === 0 ? 'Gratuito' : '€ ' + formatCurrency(getOptionCost(opt)) }}
                  </span>
                </div>
                <p class="option-desc">{{ opt.description }}</p>

                <!-- Hot item restriction message -->
                @if (isOptionDisabled(opt.id)) {
                  <span class="warning-tag">⚠️ Non disponibile per bevande o cibi caldi</span>
                }

                <!-- Sub-panel for Smart Locker: 10-Minute multiples slots -->
                @if (opt.id === getSelectedOptionId() && opt.id === 'pickup_locker') {
                  <div class="sub-panel" (click)="$event.stopPropagation()">
                    <div class="lead-time-badge warning-lead">
                      ⏳ <strong>Preavviso min. 30 minuti:</strong> tempo necessario per preparazione e carico nel locker.
                    </div>
                    <div class="sub-panel-title">
                      <span>📦 Seleziona Slot Locker (Multipli di 10 minuti):</span>
                    </div>
                    <div class="slots-chips-grid">
                      @for (slot of lockerSlots; track slot.start) {
                        <button
                          type="button"
                          class="slot-chip"
                          [class.selected]="isLockerSlotSelected(slot)"
                          (click)="onSelectLockerSlot(slot, $event)"
                          [disabled]="chatService.isLoading()"
                        >
                          {{ slot.start }} – {{ slot.end }}
                        </button>
                      }
                    </div>
                    <p class="sub-panel-info">
                      🔒 Lo Smart Locker si trova al piano interrato. Riceverai un codice PIN con validità di 10 minuti per il ritiro contactless.
                    </p>
                  </div>
                }

                <!-- Sub-panel for In-Seat Train Delivery: 1-minute precise courier wait window -->
                @if (opt.id === getSelectedOptionId() && opt.id === 'in_seat_train') {
                  <div class="sub-panel" (click)="$event.stopPropagation()">
                    <div class="lead-time-badge info-lead">
                      ⏳ <strong>Preavviso min. 30 minuti:</strong> richiesto prima dell'arrivo o partenza del treno.
                    </div>
                    <div class="sub-panel-title">
                      <span>🚄 Dettagli Consegna a Bordo Treno / Binario:</span>
                    </div>
                    <div class="form-grid">
                      <div class="form-group">
                        <label>Treno:</label>
                        <input
                          type="text"
                          [(ngModel)]="trainNumber"
                          placeholder="es. Frecciarossa 9540"
                          class="form-input"
                        />
                      </div>
                      <div class="form-group">
                        <label>Carrozza:</label>
                        <input
                          type="text"
                          [(ngModel)]="carriage"
                          placeholder="es. 4"
                          class="form-input"
                        />
                      </div>
                      <div class="form-group">
                        <label>Posto:</label>
                        <input
                          type="text"
                          [(ngModel)]="seat"
                          placeholder="es. 12D"
                          class="form-input"
                        />
                      </div>
                      <div class="form-group">
                        <label>Binario:</label>
                        <input
                          type="text"
                          [(ngModel)]="platform"
                          placeholder="es. Binario 14"
                          class="form-input"
                        />
                      </div>
                      <div class="form-group span-2">
                        <label>Orario Consegna al Binario:</label>
                        <input
                          type="text"
                          [(ngModel)]="trainTime"
                          placeholder="es. 17:15"
                          class="form-input"
                        />
                      </div>
                    </div>

                    <!-- Quick train time presets -->
                    <div class="train-time-presets">
                      <span class="presets-label">🕒 Orari consigliati (preavviso ≥ 30 min):</span>
                      <div class="presets-buttons">
                        <button type="button" class="preset-chip" (click)="setTrainTimeOffset(35, $event)">
                          Primo utile ({{ getTrainTimeOffsetDisplay(35) }})
                        </button>
                        <button type="button" class="preset-chip" (click)="setTrainTimeOffset(50, $event)">
                          +50 min ({{ getTrainTimeOffsetDisplay(50) }})
                        </button>
                        <button type="button" class="preset-chip" (click)="setTrainTimeOffset(65, $event)">
                          +65 min ({{ getTrainTimeOffsetDisplay(65) }})
                        </button>
                      </div>
                    </div>

                    <!-- Inline warning if time has < 25 min notice -->
                    @if (isTrainTimeTooSoon()) {
                      <div class="train-lead-warning">
                        <div class="warning-title">
                          ⚠️ Preavviso insufficiente (min. 30 minuti richiesti)
                        </div>
                        <p class="warning-desc">
                          L'orario <strong>{{ trainTime }}</strong> non lascia abbastanza tempo al fattorino per raggiungere il binario.
                          Il primo orario consentito è <strong>{{ getTrainTimeOffsetDisplay(35) }}</strong>.
                        </p>
                        <div class="warning-btn-row">
                          <button type="button" class="btn-warn-action" (click)="setTrainTimeOffset(35, $event)">
                            🕒 Imposta {{ getTrainTimeOffsetDisplay(35) }}
                          </button>
                          <button type="button" class="btn-warn-action express-highlight" (click)="onSelectOption('pickup_express')">
                            ⚡ Passa a Ritiro Express al Banco (5 min)
                          </button>
                        </div>
                      </div>
                    }

                    <div class="precision-badge">
                      ⏱️ <strong>Attesa massima fattorino: 1 minuto</strong> durante la fermata al binario
                      (Finestra: <strong>{{ trainTime || '17:15' }} – {{ getWaitOneMin(trainTime || '17:15') }}</strong>).
                    </div>
                    <button
                      type="button"
                      class="btn-apply-details"
                      (click)="onApplyTrainDetails($event)"
                      [disabled]="chatService.isLoading() || isTrainTimeTooSoon()"
                    >
                      Aggiorna Dettagli Treno
                    </button>
                  </div>
                }

                <!-- Sub-panel for Bistrot Table / Express: 5-minute interval -->
                @if (opt.id === getSelectedOptionId() && opt.id === 'pickup_express') {
                  <div class="sub-panel" (click)="$event.stopPropagation()">
                    <div class="lead-time-badge success-lead">
                      ⚡ <strong>Nessun preavviso richiesto:</strong> preparazione rapida espressa in soli 5 minuti!
                    </div>
                    <div class="sub-panel-title">
                      <span>🍽️ Postazione Ritiro / Tavolo (Bistrot Binario 12):</span>
                    </div>
                    <div class="table-chips-row">
                      @for (tbl of ['Al Banco', 'Tavolo 1', 'Tavolo 3', 'Tavolo 5', 'Tavolo 12']; track tbl) {
                        <button
                          type="button"
                          class="table-chip"
                          [class.selected]="isTableNumSelected(tbl)"
                          (click)="onSelectTableNum(tbl, $event)"
                          [disabled]="chatService.isLoading()"
                        >
                          {{ tbl }}
                        </button>
                      }
                    </div>
                    <div class="sub-panel-title mt-2">
                      <span>⏱️ Orario Desiderato (Intervalli di 5 minuti):</span>
                    </div>
                    <div class="slots-chips-grid">
                      @for (slot of tableSlots; track slot.start) {
                        <button
                          type="button"
                          class="slot-chip"
                          [class.selected]="isTableSlotSelected(slot)"
                          (click)="onSelectTableSlot(slot, $event)"
                          [disabled]="chatService.isLoading()"
                        >
                          {{ slot.start }} – {{ slot.end }}
                        </button>
                      }
                    </div>
                    <p class="sub-panel-info">
                      ☕ Finestra di preparazione al desk express o al tavolo: 5 minuti.
                    </p>
                  </div>
                }
              </div>
            }
          </div>
        </div>
      }

      <!-- Totals Breakdown -->
      <div class="totals-section">
        @for (total of getDisplayTotals(); track total.type) {
          <div class="total-row" [class.grand-total]="total.type === 'total'">
            <span>{{ total.display_text }}</span>
            <span>€ {{ formatCurrency(total.amount) }}</span>
          </div>
        }
      </div>

      <!-- Actions -->
      @if (checkout.status !== 'completed') {
        <div class="actions-section">
          @if (checkout.status === 'incomplete') {
            <button
              class="btn btn-primary"
              (click)="onStartPayment()"
              [disabled]="chatService.isLoading()"
            >
              Procedi al Checkout →
            </button>
          } @else if (checkout.status === 'ready_for_complete') {
            <button
              class="btn btn-success"
              (click)="onCompletePayment()"
              [disabled]="chatService.isLoading()"
            >
              🔒 Paga con Mandato AP2 (Google Pay)
            </button>
          }
        </div>
      }
    </div>

    <!-- Local Credential Manager (LCM) Biometric / Passkey Simulation Modal -->
    @if (showLcmModal) {
      <app-lcm-modal
        [checkout]="checkout"
        (confirm)="onLcmConfirmed($event)"
        (cancel)="showLcmModal = false"
      ></app-lcm-modal>
    }
  `,
  styles: [`
    .checkout-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      padding: 18px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.06);
      max-width: 500px;
      width: 100%;
      margin: 8px 0;
    }
    .checkout-card.completed {
      border-color: #86efac;
      background: #f0fdf4;
    }
    .checkout-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #f1f5f9;
      padding-bottom: 12px;
      margin-bottom: 14px;
    }
    .header-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .header-title h3 {
      margin: 0;
      font-size: 1.05rem;
      font-weight: 700;
      color: #0f172a;
    }
    .icon {
      font-size: 1.2rem;
    }
    .status-badge {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .status-incomplete {
      background: #fef3c7;
      color: #92400e;
    }
    .status-ready_for_complete {
      background: #e0f2fe;
      color: #0369a1;
    }
    .status-completed {
      background: #dcfce7;
      color: #15803d;
    }
    .order-id-box {
      background: #ecfdf5;
      border: 1px solid #a7f3d0;
      border-radius: 10px;
      padding: 12px 14px;
      margin-bottom: 14px;
      color: #065f46;
      font-size: 0.85rem;
    }
    .order-id-row {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 8px;
    }
    .order-id-val {
      font-size: 0.95rem;
      color: #047857;
      font-family: monospace;
    }
    .order-summary-meta {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin: 8px 0;
      padding: 8px 0;
      border-top: 1px dashed #a7f3d0;
      border-bottom: 1px dashed #a7f3d0;
      font-size: 0.8rem;
    }
    .meta-row {
      display: flex;
      align-items: flex-start;
      gap: 6px;
    }
    .meta-icon {
      font-size: 0.85rem;
    }
    .order-note {
      margin: 6px 0 0 0;
      font-size: 0.75rem;
      color: #047857;
    }
    .items-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 14px;
    }
    .item-row {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .item-thumb {
      width: 44px;
      height: 44px;
      border-radius: 6px;
      object-fit: cover;
      background: #f1f5f9;
    }
    .item-info {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
    .item-title {
      font-size: 0.85rem;
      font-weight: 600;
      color: #1e293b;
    }
    .item-qty {
      font-size: 0.75rem;
      color: #64748b;
    }
    .item-price {
      font-size: 0.9rem;
      font-weight: 700;
      color: #0f172a;
    }
    .fulfillment-section {
      border-top: 1px solid #f1f5f9;
      padding-top: 12px;
      margin-bottom: 14px;
    }
    .section-title {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      color: #64748b;
      margin: 0 0 8px 0;
    }
    .fulfillment-options {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .fulfillment-option {
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px 12px;
      cursor: pointer;
      background: #ffffff;
      transition: all 0.15s ease;
    }
    .fulfillment-option:hover:not(.disabled) {
      border-color: #d97706;
      background: #fafaf9;
    }
    .fulfillment-option.selected {
      border-color: #d97706;
      background: #fffbeb;
    }
    .fulfillment-option.disabled {
      opacity: 0.55;
      cursor: not-allowed;
      background: #fafaf9;
    }
    .option-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.84rem;
    }
    .option-title-row {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .radio-indicator {
      color: #d97706;
      font-size: 0.9rem;
    }
    .option-cost {
      font-weight: 700;
      color: #0f172a;
    }
    .option-desc {
      font-size: 0.74rem;
      color: #64748b;
      margin: 4px 0 0 20px;
    }
    .warning-tag {
      display: inline-block;
      margin: 4px 0 0 20px;
      font-size: 0.7rem;
      color: #b91c1c;
      font-weight: 600;
    }
    /* Sub panels inside selected options */
    .sub-panel {
      margin-top: 10px;
      padding: 10px 12px;
      background: #ffffff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
    }
    .lead-time-badge {
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.73rem;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
      line-height: 1.3;
    }
    .lead-time-badge.warning-lead {
      background: #fef3c7;
      border: 1px solid #fde68a;
      color: #92400e;
    }
    .lead-time-badge.info-lead {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1e40af;
    }
    .lead-time-badge.success-lead {
      background: #ecfdf5;
      border: 1px solid #a7f3d0;
      color: #065f46;
    }
    .sub-panel-title {
      font-size: 0.76rem;
      font-weight: 700;
      color: #1e3a8a;
      margin-bottom: 6px;
    }
    .mt-2 {
      margin-top: 8px;
    }
    .slots-chips-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 6px;
    }
    .slot-chip {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 4px 8px;
      font-size: 0.75rem;
      font-weight: 600;
      color: #334155;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .slot-chip:hover:not(:disabled) {
      border-color: #2563eb;
      background: #e0f2fe;
    }
    .slot-chip.selected {
      background: #2563eb;
      color: #ffffff;
      border-color: #1d4ed8;
    }
    .table-chips-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 6px;
    }
    .table-chip {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 4px 8px;
      font-size: 0.75rem;
      font-weight: 600;
      color: #334155;
      cursor: pointer;
    }
    .table-chip:hover:not(:disabled) {
      border-color: #2563eb;
      background: #e0f2fe;
    }
    .table-chip.selected {
      background: #1d4ed8;
      color: #ffffff;
      border-color: #1e40af;
    }
    .sub-panel-info {
      font-size: 0.72rem;
      color: #64748b;
      margin: 4px 0 0 0;
    }
    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 8px;
    }
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .form-group.span-2 {
      grid-column: span 2;
    }
    .form-group label {
      font-size: 0.7rem;
      font-weight: 600;
      color: #475569;
    }
    .form-input {
      padding: 5px 8px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      font-size: 0.78rem;
      color: #0f172a;
    }
    .form-input:focus {
      outline: none;
      border-color: #2563eb;
    }
    .precision-badge {
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      padding: 6px 8px;
      font-size: 0.72rem;
      color: #991b1b;
      margin-bottom: 8px;
    }
    .train-time-presets {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 8px;
    }
    .presets-label {
      font-size: 0.68rem;
      font-weight: 700;
      color: #1e40af;
    }
    .presets-buttons {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .preset-chip {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 6px;
      padding: 3px 8px;
      font-size: 0.72rem;
      font-weight: 600;
      color: #1d4ed8;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .preset-chip:hover {
      background: #dbeafe;
      border-color: #93c5fd;
    }
    .train-lead-warning {
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-radius: 8px;
      padding: 8px 10px;
      margin-bottom: 8px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .warning-title {
      font-size: 0.72rem;
      font-weight: 800;
      color: #92400e;
    }
    .warning-desc {
      margin: 0;
      font-size: 0.7rem;
      color: #78350f;
      line-height: 1.35;
    }
    .warning-btn-row {
      display: flex;
      gap: 6px;
      margin-top: 4px;
    }
    .btn-warn-action {
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 0.7rem;
      font-weight: 700;
      cursor: pointer;
      border: 1px solid #d97706;
      background: #fef3c7;
      color: #92400e;
      transition: all 0.15s ease;
    }
    .btn-warn-action:hover {
      background: #fde68a;
    }
    .btn-warn-action.express-highlight {
      background: #dcfce7;
      color: #166534;
      border-color: #86efac;
    }
    .btn-warn-action.express-highlight:hover {
      background: #bbf7d0;
    }
    .btn-apply-details {
      width: 100%;
      background: #2563eb;
      color: #ffffff;
      border: none;
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.15s ease;
    }
    .btn-apply-details:hover:not(:disabled) {
      background: #1d4ed8;
    }
    .totals-section {
      border-top: 1px solid #f1f5f9;
      padding-top: 10px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .total-row {
      display: flex;
      justify-content: space-between;
      font-size: 0.82rem;
      color: #475569;
    }
    .total-row.grand-total {
      font-size: 1.05rem;
      font-weight: 800;
      color: #0f172a;
      border-top: 1px solid #e2e8f0;
      padding-top: 8px;
      margin-top: 4px;
    }
    .actions-section {
      margin-top: 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .btn {
      width: 100%;
      padding: 10px 16px;
      border-radius: 8px;
      font-size: 0.88rem;
      font-weight: 700;
      border: none;
      cursor: pointer;
      transition: background 0.15s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .btn-primary {
      background: linear-gradient(135deg, #d97706, #b45309);
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(180, 83, 9, 0.25);
    }
    .btn-primary:hover:not(:disabled) {
      background: linear-gradient(135deg, #b45309, #92400e);
    }
    .btn-success {
      background: #16a34a;
      color: #ffffff;
    }
    .btn-success:hover:not(:disabled) {
      background: #15803d;
    }
    .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  `]
})
export class CheckoutComponent implements OnInit, OnChanges {
  @Input({ required: true }) checkout!: Checkout;
  chatService = inject(ChatService);

  // Train delivery input fields
  trainNumber: string = 'Frecciarossa 9540';
  carriage: string = 'Carrozza 4';
  seat: string = '12D';
  platform: string = 'Binario 14';
  trainTime: string = '';

  // Table service input fields
  selectedTable: string = 'Al Banco';
  selectedTableSlot: string | null = null;

  // Smart locker selection
  selectedLockerSlot: string | null = null;

  // Slots lists
  lockerSlots: { start: string; end: string }[] = [];
  tableSlots: { start: string; end: string }[] = [];

  ngOnInit(): void {
    this.lockerSlots = this.getLockerSlots();
    this.tableSlots = this.getTableSlots();
    if (this.lockerSlots.length > 0) {
      this.selectedLockerSlot = this.lockerSlots[0].start;
    }
    if (this.tableSlots.length > 0) {
      this.selectedTableSlot = this.tableSlots[0].start;
    }
    this.syncAllFromCheckout();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['checkout']) {
      this.syncAllFromCheckout();
    }
  }

  syncAllFromCheckout(): void {
    this.selectedTable = this.getActiveTable();
    this.syncTrainDetailsFromCheckout();
  }

  getConfirmedTrainTime(): string | null {
    // 1. From opt.description ("Consegna confermata per le 19:45...")
    const opt = this.getFulfillmentOptions().find((o) => o.id === 'in_seat_train');
    if (opt?.description) {
      const match = opt.description.match(/per le\s*(\d{2}:\d{2})/i);
      if (match) return match[1];
    }

    // 2. From destinations extended_address ("... Orario consegna: 19:45 ...")
    const methods = this.getFulfillmentMethods();
    if (methods.length > 0 && methods[0].destinations && methods[0].destinations.length > 0) {
      const rawDest: any = methods[0].destinations[0];
      const dest = rawDest.root || rawDest;
      const ext = dest.extended_address || '';
      const match = ext.match(/Orario consegna:\s*(\d{2}:\d{2})/i);
      if (match) return match[1];
    }

    // 3. From opt.earliest_fulfillment_time
    if (opt?.earliest_fulfillment_time) {
      const t = this.formatIsoTime(opt.earliest_fulfillment_time);
      if (/^\d{2}:\d{2}$/.test(t)) return t;
    }

    return null;
  }

  syncTrainDetailsFromCheckout(): void {
    const confirmedTime = this.getConfirmedTrainTime();
    if (confirmedTime) {
      this.trainTime = confirmedTime;
    } else if (!this.trainTime) {
      this.trainTime = this.getInitialTrainTime();
    }

    const opt = this.getFulfillmentOptions().find((o) => o.id === 'in_seat_train');
    const methods = this.getFulfillmentMethods();
    if (methods.length > 0 && methods[0].destinations && methods[0].destinations.length > 0) {
      const rawDest: any = methods[0].destinations[0];
      const dest = rawDest.root || rawDest;
      const street = dest.street_address || '';
      const ext = dest.extended_address || '';

      // Treno: "Stazione Milano Centrale, Treno Frecciarossa 9540 (Binario 14)"
      const trainMatch = street.match(/Treno\s+(.*?)\s*\(/i) || opt?.description?.match(/Treno\s+(.*?),/i);
      if (trainMatch) {
        this.trainNumber = trainMatch[1].trim();
      }

      // Binario: "(Binario 14)"
      const platMatch = street.match(/\((Binario.*?)\)/i) || opt?.description?.match(/\((Binario.*?)\)/i);
      if (platMatch) {
        this.platform = platMatch[1].trim();
      }

      // Carrozza: "Carrozza 4, Posto 12D"
      const carrMatch = ext.match(/Carrozza\s+([^,]+)/i) || opt?.description?.match(/Carrozza\s+([^,]+)/i);
      if (carrMatch) {
        const rawCarr = carrMatch[1].trim();
        this.carriage = rawCarr.replace(/^Carrozza\s+/i, '').trim() || rawCarr;
      }

      // Posto: "Posto 12D"
      const seatMatch = ext.match(/Posto\s+([^\s,(]+)/i) || opt?.description?.match(/Posto\s+([^\s,(]+)/i);
      if (seatMatch) {
        this.seat = seatMatch[1].trim();
      }
    }
  }

  getInitialTrainTime(): string {
    return this.getTrainTimeOffsetDisplay(35);
  }

  getTrainTimeOffsetDisplay(offsetMins: number): string {
    const d = new Date(Date.now() + offsetMins * 60 * 1000);
    return d.toTimeString().substring(0, 5);
  }

  setTrainTimeOffset(offsetMins: number, event?: Event): void {
    if (event) event.stopPropagation();
    this.trainTime = this.getTrainTimeOffsetDisplay(offsetMins);
  }

  isTrainTimeTooSoon(): boolean {
    if (!this.trainTime) return false;
    try {
      const parts = this.trainTime.split(':').map((p) => parseInt(p, 10));
      if (parts.length >= 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
        const now = new Date();
        const target = new Date();
        target.setHours(parts[0], parts[1], 0, 0);
        // If hour is far in the past today, assume tomorrow
        if (target.getTime() < now.getTime() - 12 * 3600 * 1000) {
          target.setDate(target.getDate() + 1);
        }
        const diffMins = (target.getTime() - now.getTime()) / (60 * 1000);
        return diffMins < 25;
      }
    } catch (_) {}
    return false;
  }

  formatCurrency(cents: number): string {
    return (cents / 100).toFixed(2);
  }

  getItemTotal(item: LineItem): number {
    const total = item.totals.find((t) => t.type === 'total');
    return total ? total.amount : item.item.price * item.quantity;
  }

  getStatusLabel(): string {
    switch (this.checkout.status) {
      case 'incomplete': return 'In Corso';
      case 'ready_for_complete': return 'Pronto per il Pagamento';
      case 'completed': return 'Confermato';
      default: return this.checkout.status;
    }
  }

  hasFulfillmentOptions(): boolean {
    const opts = this.getFulfillmentOptions();
    return opts.length > 0;
  }

  getFulfillmentMethods(): any[] {
    if (!this.checkout?.fulfillment) return [];
    const f: any = this.checkout.fulfillment;
    if (Array.isArray(f.methods)) return f.methods;
    if (f.root && Array.isArray(f.root.methods)) return f.root.methods;
    return [];
  }

  getFulfillmentOptions(): FulfillmentOption[] {
    const methods = this.getFulfillmentMethods();
    for (const m of methods) {
      if (m.groups && m.groups.length > 0 && m.groups[0].options) {
        return m.groups[0].options;
      }
    }
    return [];
  }

  getSelectedOption(): FulfillmentOption | null {
    const selectedId = this.getSelectedOptionId();
    if (!selectedId) return null;
    return this.getFulfillmentOptions().find(o => o.id === selectedId) || null;
  }

  getSelectedOptionId(): string | null {
    const methods = this.getFulfillmentMethods();
    for (const m of methods) {
      if (m.groups && m.groups.length > 0) {
        return m.groups[0].selected_option_id;
      }
    }
    return null;
  }

  getSelectedOptionTitle(): string {
    const opt = this.getSelectedOption();
    return opt ? opt.title : 'Ritiro Stazione Centrale';
  }

  getOptionCost(opt: FulfillmentOption): number {
    const total = opt.totals.find((t) => t.type === 'total');
    return total ? total.amount : 0;
  }

  hasHotItems(): boolean {
    return this.checkout.line_items.some(li => {
      const title = (li.item.title || '').toLowerCase();
      return (
        title.includes('espresso') ||
        title.includes('cappuccino') ||
        title.includes('caldo') ||
        title.includes('calda') ||
        title.includes('toast')
      );
    });
  }

  isOptionDisabled(optionId: string): boolean {
    if (optionId === 'pickup_locker' && this.hasHotItems()) {
      return true;
    }
    return false;
  }

  getDisplayTotals() {
    return this.checkout.totals;
  }

  getWaitOneMin(timeStr: string): string {
    try {
      const parts = timeStr.split(':').map(p => parseInt(p, 10));
      if (parts.length >= 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
        let hour = parts[0];
        let minute = parts[1] + 1;
        if (minute >= 60) {
          minute = 0;
          hour = (hour + 1) % 24;
        }
        return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
      }
    } catch (_) {}
    return '17:16';
  }

  getLockerSlots(): { start: string; end: string }[] {
    const now = new Date();
    // Minimum 30 minutes lead buffer for locker preparation
    const lead = new Date(now.getTime() + 30 * 60 * 1000);
    const minute = lead.getMinutes();
    const remainder = minute % 10;
    const addMins = remainder === 0 ? 0 : 10 - remainder;
    lead.setMinutes(minute + addMins, 0, 0);

    const slots: { start: string; end: string }[] = [];
    for (let i = 0; i < 5; i++) {
      const sStart = new Date(lead.getTime() + i * 10 * 60 * 1000);
      const sEnd = new Date(sStart.getTime() + 10 * 60 * 1000);
      slots.push({
        start: sStart.toTimeString().substring(0, 5),
        end: sEnd.toTimeString().substring(0, 5),
      });
    }
    return slots;
  }

  getTableSlots(): { start: string; end: string }[] {
    const now = new Date();
    const lead = new Date(now.getTime() + 3 * 60 * 1000);
    const minute = lead.getMinutes();
    const remainder = minute % 5;
    const addMins = remainder === 0 ? 0 : 5 - remainder;
    lead.setMinutes(minute + addMins, 0, 0);

    const slots: { start: string; end: string }[] = [];
    for (let i = 0; i < 5; i++) {
      const sStart = new Date(lead.getTime() + i * 5 * 60 * 1000);
      const sEnd = new Date(sStart.getTime() + 5 * 60 * 1000);
      slots.push({
        start: sStart.toTimeString().substring(0, 5),
        end: sEnd.toTimeString().substring(0, 5),
      });
    }
    return slots;
  }

  isLockerSlotSelected(slot: { start: string; end: string }): boolean {
    const opt = this.getSelectedOption();
    if (opt?.earliest_fulfillment_time) {
      return opt.earliest_fulfillment_time.includes(slot.start);
    }
    return this.selectedLockerSlot === slot.start;
  }

  isTableSlotSelected(slot: { start: string; end: string }): boolean {
    const opt = this.getSelectedOption();
    if (opt?.earliest_fulfillment_time) {
      return opt.earliest_fulfillment_time.includes(slot.start);
    }
    return this.selectedTableSlot === slot.start;
  }

  getActiveTable(): string {
    // 1. Try from destination extended_address
    const methods = this.getFulfillmentMethods();
    if (methods.length > 0 && methods[0].destinations && methods[0].destinations.length > 0) {
      const rawDest: any = methods[0].destinations[0];
      const dest = rawDest.root || rawDest;
      const ext = (dest.extended_address || '').toLowerCase();
      if (ext.includes('banco') || ext.includes('bancone')) {
        return 'Al Banco';
      }
      for (const t of ['Tavolo 1', 'Tavolo 3', 'Tavolo 5', 'Tavolo 12']) {
        if (ext.includes(t.toLowerCase())) {
          return t;
        }
      }
    }

    // 2. Try from selected fulfillment option
    const opt = this.getSelectedOption();
    if (opt) {
      const text = `${opt.title || ''} ${opt.description || ''}`.toLowerCase();
      if (text.includes('banco') || text.includes('bancone')) {
        return 'Al Banco';
      }
      for (const t of ['Tavolo 1', 'Tavolo 3', 'Tavolo 5', 'Tavolo 12']) {
        if (text.includes(t.toLowerCase())) {
          return t;
        }
      }
    }

    // 3. Fallback to local user selection or default 'Al Banco'
    return this.selectedTable || 'Al Banco';
  }

  isTableNumSelected(tbl: string): boolean {
    return this.getActiveTable() === tbl;
  }

  getFulfillmentWindowDisplay(): string {
    const opt = this.getSelectedOption();
    if (opt?.earliest_fulfillment_time && opt?.latest_fulfillment_time) {
      const start = this.formatIsoTime(opt.earliest_fulfillment_time);
      const end = this.formatIsoTime(opt.latest_fulfillment_time);
      if (opt.id === 'in_seat_train') {
        return `${start} – ${end} (Finestra attesa max 1 min a bordo treno)`;
      } else if (opt.id === 'pickup_locker') {
        return `${start} – ${end} (Finestra sblocco 10 min, multiplo di 10)`;
      } else {
        return `${start} – ${end} (Finestra preparazione 5 min)`;
      }
    }
    if (opt?.id === 'in_seat_train') {
      return `${this.trainTime} – ${this.getWaitOneMin(this.trainTime)} (Attesa max 1 min)`;
    }
    return 'Entro 10 minuti';
  }

  getDestinationDisplay(): string {
    const methods = this.getFulfillmentMethods();
    if (methods.length > 0 && methods[0].destinations && methods[0].destinations.length > 0) {
      const rawDest: any = methods[0].destinations[0];
      const dest = rawDest.root || rawDest;
      if (dest.extended_address) {
        return `${dest.street_address} • ${dest.extended_address}`;
      }
      return dest.street_address || "Milano Centrale";
    }
    return "Milano Centrale";
  }

  getPlacedDateTimeDisplay(): string {
    const d = new Date();
    return d.toLocaleDateString('it-IT') + ' ' + d.toLocaleTimeString('it-IT');
  }

  formatIsoTime(isoStr: string): string {
    if (!isoStr) return '';
    try {
      if (isoStr.includes('T')) {
        const timePart = isoStr.split('T')[1]?.substring(0, 5);
        if (/^\d{2}:\d{2}$/.test(timePart)) {
          return timePart;
        }
      }
      const dt = new Date(isoStr);
      if (!isNaN(dt.getTime())) {
        return dt.toTimeString().substring(0, 5);
      }
    } catch (_) {}
    return isoStr;
  }

  onSelectOption(optionId: string): void {
    if (this.isOptionDisabled(optionId)) return;
    this.chatService.selectDeliveryOption(optionId);
  }

  onSelectLockerSlot(slot: { start: string; end: string }, event: Event): void {
    event.stopPropagation();
    this.selectedLockerSlot = slot.start;
    this.chatService.setLockerPickup(slot.start);
  }

  onSelectTableSlot(slot: { start: string; end: string }, event: Event): void {
    event.stopPropagation();
    this.selectedTableSlot = slot.start;
    this.chatService.setTableService(this.getActiveTable(), slot.start);
  }

  onSelectTableNum(tableNum: string, event: Event): void {
    event.stopPropagation();
    this.selectedTable = tableNum;
    this.chatService.setTableService(tableNum, this.selectedTableSlot || undefined);
  }

  onApplyTrainDetails(event: Event): void {
    event.stopPropagation();
    this.chatService.setTrainDelivery({
      trainNumber: this.trainNumber,
      carriage: this.carriage,
      seat: this.seat,
      deliveryTime: this.trainTime,
      platform: this.platform,
    });
  }

  showLcmModal: boolean = false;

  onStartPayment(): void {
    this.chatService.startPayment();
  }

  onCompletePayment(): void {
    // Open Local Credential Manager (LCM) biometric/passkey modal
    this.showLcmModal = true;
  }

  onLcmConfirmed(mandates: { mandateId: string; cartMandateJwt: string; paymentMandateJwt: string }): void {
    this.showLcmModal = false;
    this.chatService.completePayment(this.checkout, mandates);
  }
}

