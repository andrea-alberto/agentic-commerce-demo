// Copyright 2026 UCP Authors / GDG DevFest Milano 2026
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TravelerContext, ScenarioPreset, DEFAULT_SCENARIO_PRESETS } from '../models/traveler-context.model';

@Component({
  selector: 'lib-traveler-ticket-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="ticket-wrapper" [class.italo-theme]="context?.ticket?.train_number?.includes('Italo')">
      <!-- HEADER ROW: BRAND, PNR & PRESET CHIPS -->
      <div class="ticket-header">
        <div class="brand-badge">
          <span class="train-icon">🚆</span>
          <div class="train-title-group">
            <strong class="train-name">{{ context?.ticket?.train_number || 'Frecciarossa 9540' }}</strong>
            <span class="train-class">{{ context?.ticket?.class_service || 'Area Silenzio • Prima Classe' }}</span>
          </div>
        </div>

        <div class="ticket-pnr-box">
          <span class="pnr-label">PNR BIGLIETTO</span>
          <strong class="pnr-code">{{ context?.ticket?.pnr || 'FR-9540-MR' }}</strong>
        </div>

        <!-- QUICK SCENARIO PRESETS -->
        <div class="preset-chips">
          <button
            *ngFor="let p of presets"
            type="button"
            class="preset-chip-btn"
            [class.active]="context?.scenario_preset_id === p.id"
            (click)="selectPreset.emit(p)"
            [title]="p.description"
          >
            <span>{{ p.badge }}</span>
            <small>{{ p.short_label }}</small>
          </button>
        </div>

        <button type="button" class="btn-edit-context" (click)="editContext.emit()">
          <span>✏️ Modifica Contesto</span>
        </button>
      </div>

      <!-- MAIN TICKET BODY -->
      <div class="ticket-body">
        <div class="route-block">
          <div class="station-col origin">
            <span class="city-name">{{ context?.ticket?.origin || 'Milano Centrale' }}</span>
            <span class="station-meta">Partenza ore {{ context?.ticket?.departure_time || '13:10' }}</span>
          </div>

          <div class="route-line-col">
            <div class="line-dot"></div>
            <div class="line-track"></div>
            <span class="route-arrow">➔</span>
            <div class="line-track"></div>
            <div class="line-dot end"></div>
          </div>

          <div class="station-col dest">
            <span class="city-name">{{ context?.ticket?.destination || 'Roma Termini' }}</span>
            <span class="station-meta">Alta Velocità AV</span>
          </div>
        </div>

        <!-- TICKET SEAT & PLATFORM METRICS -->
        <div class="metrics-grid">
          <div class="metric-box">
            <span class="m-label">BINARIO</span>
            <strong class="m-val highlight">Bin. {{ context?.ticket?.platform || '14' }}</strong>
          </div>
          <div class="metric-box">
            <span class="m-label">CARROZZA</span>
            <strong class="m-val">{{ context?.ticket?.carriage || '4' }}</strong>
          </div>
          <div class="metric-box">
            <span class="m-label">POSTO</span>
            <strong class="m-val">{{ context?.ticket?.seat || '12D' }}</strong>
          </div>
          <div class="metric-box ap2-box">
            <span class="m-label">MANDATO AP2</span>
            <strong class="m-val ap2">≤ €{{ ((context?.ap2?.max_amount_cents || 3000) / 100).toFixed(2) }}</strong>
          </div>
        </div>
      </div>

      <!-- FOOTER NOTE: ASSISTANT KNOWLEDGE SUMMARY -->
      <div class="ticket-footer">
        <span class="know-badge">🧠 Conoscenza Agente Personale:</span>
        <span class="know-text">
          Dieta: <em>{{ context?.preferences?.dietary || 'Piatti leggeri e bio' }}</em> · 
          Budget: <em>€{{ ((context?.preferences?.max_budget_cents || 2500) / 100).toFixed(2) }}</em> · 
          Preferenza: <em>{{ context?.preferences?.preferred_fulfillment === 'in_seat_train' ? 'Consegna a bordo' : 'Smart Locker' }}</em>
        </span>
      </div>
    </div>
  `,
  styles: [`
    .ticket-wrapper {
      background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
      border: 1px solid #4338ca;
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
      margin-bottom: 1rem;
      transition: all 0.2s ease;
    }

    .ticket-wrapper.italo-theme {
      background: linear-gradient(135deg, #450a0a 0%, #0f172a 100%);
      border-color: #991b1b;
    }

    .ticket-header {
      background: rgba(15, 23, 42, 0.7);
      padding: 0.8rem 1.2rem;
      display: flex;
      align-items: center;
      gap: 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      flex-wrap: wrap;
    }

    .brand-badge {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .train-icon {
      font-size: 1.6rem;
    }

    .train-title-group {
      display: flex;
      flex-direction: column;
    }

    .train-name {
      font-size: 1.05rem;
      color: #ffffff;
      font-weight: 800;
    }

    .train-class {
      font-size: 0.75rem;
      color: #94a3b8;
    }

    .ticket-pnr-box {
      background: rgba(0, 0, 0, 0.3);
      padding: 4px 10px;
      border-radius: 6px;
      border: 1px dashed #6366f1;
      display: flex;
      flex-direction: column;
    }

    .pnr-label {
      font-size: 0.65rem;
      color: #818cf8;
      font-weight: 800;
      letter-spacing: 0.05em;
    }

    .pnr-code {
      font-family: 'JetBrains Mono', monospace;
      color: #e0e7ff;
      font-size: 0.85rem;
    }

    .preset-chips {
      display: flex;
      gap: 8px;
      margin-left: auto;
    }

    .preset-chip-btn {
      background: #1e293b;
      border: 1px solid #334155;
      color: #cbd5e1;
      padding: 5px 10px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: center;
      transition: all 0.2s ease;
      font-size: 0.75rem;
    }

    .preset-chip-btn:hover {
      background: #334155;
      color: #ffffff;
    }

    .preset-chip-btn.active {
      background: #4f46e5;
      border-color: #818cf8;
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
    }

    .btn-edit-context {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #e2e8f0;
      padding: 6px 12px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.8rem;
      font-weight: 700;
      transition: all 0.2s ease;
    }

    .btn-edit-context:hover {
      background: rgba(255, 255, 255, 0.15);
      color: #ffffff;
    }

    .ticket-body {
      padding: 1rem 1.2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 24px;
      flex-wrap: wrap;
    }

    .route-block {
      display: flex;
      align-items: center;
      gap: 16px;
      flex: 1;
    }

    .station-col {
      display: flex;
      flex-direction: column;
    }

    .city-name {
      font-size: 1.15rem;
      font-weight: 800;
      color: #ffffff;
    }

    .station-meta {
      font-size: 0.8rem;
      color: #cbd5e1;
    }

    .route-line-col {
      display: flex;
      align-items: center;
      gap: 6px;
      color: #818cf8;
    }

    .line-track {
      width: 40px;
      height: 2px;
      background: #6366f1;
    }

    .line-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #818cf8;
    }

    .metrics-grid {
      display: flex;
      gap: 12px;
    }

    .metric-box {
      background: rgba(0, 0, 0, 0.3);
      padding: 6px 12px;
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 70px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .m-label {
      font-size: 0.65rem;
      color: #94a3b8;
      font-weight: 800;
    }

    .m-val {
      font-size: 1.05rem;
      font-weight: 800;
      color: #ffffff;
    }

    .m-val.highlight {
      color: #38bdf8;
    }

    .m-val.ap2 {
      color: #c084fc;
    }

    .ticket-footer {
      background: rgba(0, 0, 0, 0.4);
      padding: 0.5rem 1.2rem;
      font-size: 0.78rem;
      color: #cbd5e1;
      display: flex;
      align-items: center;
      gap: 8px;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    .know-badge {
      font-weight: 700;
      color: #818cf8;
    }

    .know-text em {
      color: #e0e7ff;
      font-style: normal;
      font-weight: 600;
    }
  `]
})
export class TravelerTicketCardComponent {
  @Input() context: TravelerContext | null = null;
  @Input() presets: ScenarioPreset[] = DEFAULT_SCENARIO_PRESETS;

  @Output() selectPreset = new EventEmitter<ScenarioPreset>();
  @Output() editContext = new EventEmitter<void>();
}
