// Copyright 2026 UCP Authors / GDG DevFest Milano 2026
import { Component, EventEmitter, Input, Output, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TravelerContext } from '../models/traveler-context.model';

@Component({
  selector: 'lib-traveler-context-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="modal-backdrop" (click)="close.emit()">
      <div class="modal-card" (click)="$event.stopPropagation()">
        <div class="modal-head">
          <div class="head-title-row">
            <span class="modal-icon">🧠</span>
            <div class="head-text">
              <h3>Modifica Contesto Viaggiatore</h3>
              <span class="head-sub">Dati noti al Personal Shopper Agent per la negoziazione</span>
            </div>
          </div>
          <button type="button" class="btn-close" (click)="close.emit()">✕</button>
        </div>

        <div class="modal-body" *ngIf="editModel">
          <!-- SECTION 1: BIGLIETTO DEL TRENO -->
          <div class="form-section">
            <h4 class="sec-title">🚆 Biglietto Treno Attivo (Wallet)</h4>
            <div class="form-grid-2">
              <div class="form-group">
                <label>Numero Treno:</label>
                <input type="text" class="input-ctrl" [(ngModel)]="editModel.ticket.train_number" />
              </div>
              <div class="form-group">
                <label>Codice PNR:</label>
                <input type="text" class="input-ctrl" [(ngModel)]="editModel.ticket.pnr" />
              </div>
              <div class="form-group">
                <label>Orario di Partenza (HH:MM):</label>
                <input type="time" class="input-ctrl" [(ngModel)]="editModel.ticket.departure_time" />
              </div>
              <div class="form-group">
                <label>Binario Stazione:</label>
                <input type="text" class="input-ctrl" [(ngModel)]="editModel.ticket.platform" />
              </div>
              <div class="form-group">
                <label>Carrozza:</label>
                <input type="text" class="input-ctrl" [(ngModel)]="editModel.ticket.carriage" />
              </div>
              <div class="form-group">
                <label>Posto a Sedere:</label>
                <input type="text" class="input-ctrl" [(ngModel)]="editModel.ticket.seat" />
              </div>
            </div>
          </div>

          <!-- SECTION 2: PREFERENZE & SPESA -->
          <div class="form-section">
            <h4 class="sec-title">🍽️ Preferenze Personali & Vincoli Salute / Specialty</h4>
            <div class="form-grid-2">
              <div class="form-group full">
                <label>Preferenze Dietetiche / Ingredienti:</label>
                <input type="text" class="input-ctrl" [(ngModel)]="editModel.preferences.dietary" />
              </div>
              <div class="form-group">
                <label>Modalità di Consegna Preferita:</label>
                <select class="input-ctrl" [(ngModel)]="editModel.preferences.preferred_fulfillment">
                  <option value="in_seat_train">🚆 Consegna al Posto Treno (Binario)</option>
                  <option value="pickup_locker">🥪 Smart Locker (Piano Interrato)</option>
                  <option value="pickup_express">⚡ Ritiro al Banco Bistrot</option>
                  <option value="table_service">☕ Servizio al Tavolo Bistrot</option>
                </select>
              </div>
              <div class="form-group">
                <label>Budget Massimo (€):</label>
                <input type="number" class="input-ctrl" [value]="editModel.preferences.max_budget_cents / 100" (input)="onBudgetChange($event)" />
              </div>
              <div class="form-group">
                <label>Preferenza Caffè & Brewing:</label>
                <select class="input-ctrl" [(ngModel)]="editModel.preferences.coffee_preference">
                  <option value="">Nessuna preferenza</option>
                  <option value="cold_brew_specialty">❄️ Cold Brew 16h (Single Origin Etiopia)</option>
                  <option value="espresso_hot">☕ Espresso Caldo Tradizionale 100% Arabica</option>
                  <option value="specialty_filter">🌟 Qualsiasi Specialty Coffee Grade</option>
                </select>
              </div>
              <div class="form-group checkbox-group">
                <label class="checkbox-label">
                  <input type="checkbox" [(ngModel)]="editModel.preferences.avoid_ultra_processed" />
                  <span>🌱 Evita Alimenti Ultra-Processati (Solo NOVA 1-3)</span>
                </label>
              </div>
            </div>
          </div>

          <!-- SECTION 3: AP2 DELEGAZIONE -->
          <div class="form-section">
            <h4 class="sec-title">🛡️ Mandato Autonomo AP2 (Cart Mandate)</h4>
            <div class="form-grid-2">
              <div class="form-group">
                <label>Massimale Delegato senza tocco (€):</label>
                <input type="number" class="input-ctrl" [value]="editModel.ap2.max_amount_cents / 100" (input)="onAp2MaxChange($event)" />
              </div>
              <div class="form-group">
                <label>Keystore / Credenziale:</label>
                <input type="text" class="input-ctrl" [(ngModel)]="editModel.ap2.credential_manager" readonly />
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn-cancel" (click)="close.emit()">Annulla</button>
          <button type="button" class="btn-save" (click)="saveContext()">💾 Salva Contesto</button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      z-index: 200;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
    }

    .modal-card {
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 14px;
      width: 640px;
      max-width: 95vw;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.7);
      animation: modalFade 0.2s ease-out;
    }

    @keyframes modalFade {
      from { opacity: 0; transform: scale(0.96); }
      to { opacity: 1; transform: scale(1); }
    }

    .modal-head {
      background: #1e293b;
      padding: 1rem 1.5rem;
      border-bottom: 1px solid #334155;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .head-title-row {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .modal-icon {
      font-size: 1.8rem;
    }

    .head-text h3 {
      margin: 0;
      font-size: 1.15rem;
      color: #ffffff;
      font-weight: 800;
    }

    .head-sub {
      font-size: 0.78rem;
      color: #94a3b8;
    }

    .btn-close {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid #475569;
      color: #cbd5e1;
      width: 32px;
      height: 32px;
      border-radius: 8px;
      cursor: pointer;
    }

    .modal-body {
      padding: 1.5rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .form-section {
      background: rgba(30, 41, 59, 0.5);
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 1rem;
    }

    .sec-title {
      margin: 0 0 1rem 0;
      font-size: 0.9rem;
      color: #38bdf8;
      font-weight: 800;
    }

    .form-grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .form-group.full {
      grid-column: span 2;
    }

    .form-group label {
      font-size: 0.75rem;
      color: #94a3b8;
      font-weight: 700;
    }

    .input-ctrl {
      background: #0f172a;
      border: 1px solid #475569;
      color: #ffffff;
      padding: 8px 10px;
      border-radius: 6px;
      font-size: 0.85rem;
    }

    .input-ctrl:focus {
      outline: none;
      border-color: #38bdf8;
    }

    .modal-footer {
      background: #1e293b;
      padding: 1rem 1.5rem;
      border-top: 1px solid #334155;
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }

    .checkbox-group {
      grid-column: 1 / -1;
      margin-top: 4px;
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      color: #e2e8f0;
      font-size: 0.85rem;
    }

    .btn-cancel {
      background: transparent;
      border: 1px solid #475569;
      color: #cbd5e1;
      padding: 8px 16px;
      border-radius: 8px;
      cursor: pointer;
    }

    .btn-save {
      background: linear-gradient(135deg, #0284c7 0%, #0ea5e9 100%);
      border: none;
      color: #ffffff;
      padding: 8px 20px;
      border-radius: 8px;
      font-weight: 800;
      cursor: pointer;
    }
  `]
})
export class TravelerContextModalComponent implements OnInit {
  @Input() context: TravelerContext | null = null;
  @Output() close = new EventEmitter<void>();
  @Output() save = new EventEmitter<TravelerContext>();

  editModel: any = null;

  ngOnInit(): void {
    if (this.context) {
      this.editModel = JSON.parse(JSON.stringify(this.context));
    }
  }

  onBudgetChange(event: any): void {
    const val = parseFloat(event.target.value) || 25;
    this.editModel.preferences.max_budget_cents = Math.round(val * 100);
  }

  onAp2MaxChange(event: any): void {
    const val = parseFloat(event.target.value) || 30;
    this.editModel.ap2.max_amount_cents = Math.round(val * 100);
  }

  saveContext(): void {
    if (this.editModel) {
      this.save.emit(this.editModel);
    }
  }
}
