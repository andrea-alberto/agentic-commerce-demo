// Copyright 2026 UCP Authors / GDG DevFest Milano 2026
import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ShopperProposal, ProposalFulfillmentOption } from '../models/ucp-bopis.model';

@Component({
  selector: 'lib-proposal-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="proposal-card" [class.confirmed]="disabled">
      <!-- HEADER -->
      <div class="proposal-header">
        <div class="header-title">
          <span class="icon">🛍️</span>
          <div>
            <h3 class="card-title">Proposta Personal Shopper</h3>
            <span class="card-sub">{{ proposal.merchant_name }} • GDG DevFest 2026</span>
          </div>
        </div>
        <span class="status-badge" [class.badge-pending]="!disabled" [class.badge-confirmed]="disabled">
          {{ disabled ? '✅ Confermato' : '⏳ In attesa di scelta' }}
        </span>
      </div>

      <!-- PRODUCT ITEM(S) SECTION -->
      @if (hasMultipleItems()) {
        <div class="multi-items-container">
          <div class="multi-items-header">
            <span class="multi-items-title">🧺 Articoli Inclusi nella Proposta ({{ getItems().length }} articoli)</span>
            <span class="temp-badge" [class.temp-hot]="proposal.item.is_hot" [class.temp-cold]="!proposal.item.is_hot">
              {{ proposal.item.is_hot ? '🔥 Include Caldi' : '❄️ Freddo / Locker OK' }}
            </span>
          </div>

          <div class="multi-items-list">
            @for (subItem of getItems(); track subItem.id || subItem.title) {
              <div class="sub-item-card">
                <img
                  [src]="subItem.image_url || 'https://images.unsplash.com/photo-1509722747041-616f39b57569?w=400&q=80'"
                  [alt]="subItem.title || subItem.name"
                  class="sub-item-thumb"
                />
                <div class="sub-item-info">
                  <div class="sub-item-top">
                    <span class="sub-item-category">{{ subItem.category || 'Travel Retail Bistrot' }}</span>
                    @if (subItem.is_hot !== undefined) {
                      <span class="mini-temp-badge" [class.temp-hot]="subItem.is_hot" [class.temp-cold]="!subItem.is_hot">
                        {{ subItem.is_hot ? '🔥 Caldo' : '❄️ Freddo' }}
                      </span>
                    }
                    @if (subItem.nutri_score) {
                      <span class="micro-badge nutri">Nutri-Score {{ subItem.nutri_score }}</span>
                    }
                    @if (subItem.nova_group) {
                      <span class="micro-badge nova">NOVA {{ subItem.nova_group }}</span>
                    }
                    @if (subItem.coffee_profile) {
                      <span class="micro-badge coffee">☕ Specialty</span>
                    }
                  </div>
                  <h4 class="sub-item-title">{{ subItem.quantity || 1 }}x {{ subItem.title || subItem.name }}</h4>
                  @if (subItem.description) {
                    <p class="sub-item-desc">{{ subItem.description }}</p>
                  }
                  <div class="sub-item-meta-row">
                    @if (subItem.salt_g !== undefined && subItem.salt_g !== null) {
                      <span class="meta-tag">🧂 Sale: {{ subItem.salt_g }}g</span>
                    }
                    @if (subItem.protein_g !== undefined && subItem.protein_g !== null) {
                      <span class="meta-tag">💪 Prot: {{ subItem.protein_g }}g</span>
                    }
                  </div>
                  <div class="sub-item-price-row">
                    <span class="sub-item-price-label">Prezzo:</span>
                    <strong class="sub-item-price">€ {{ formatCents(subItem.price_cents) }}</strong>
                  </div>
                </div>
              </div>
            }
          </div>

          <div class="multi-items-subtotal">
            <span class="subtotal-label">Subtotale Articoli Negoziati:</span>
            <strong class="subtotal-val">€ {{ formatCents(proposal.item.price_cents) }}</strong>
          </div>
        </div>
      } @else {
        <!-- SINGLE PRODUCT ITEM ROW -->
        <div class="product-item-box">
          <img
            [src]="proposal.item.image_url || 'https://images.unsplash.com/photo-1509722747041-616f39b57569?w=400&q=80'"
            [alt]="proposal.item.title"
            class="product-thumb"
          />
          <div class="product-info">
            <div class="product-category-row">
              <span class="product-category">{{ proposal.item.category || 'Travel Retail Bistrot' }}</span>
              <span class="temp-badge" [class.temp-hot]="proposal.item.is_hot" [class.temp-cold]="!proposal.item.is_hot">
                {{ proposal.item.is_hot ? '🔥 Caldo' : '❄️ Freddo / Locker OK' }}
              </span>
              @if (getItemNutriScore(); as ns) {
                <span class="micro-badge nutri">Nutri-Score {{ ns }}</span>
              }
              @if (getItemNovaGroup(); as nv) {
                <span class="micro-badge nova">NOVA {{ nv }}</span>
              }
              @if (hasItemCoffeeProfile()) {
                <span class="micro-badge coffee">☕ Specialty</span>
              }
            </div>
            <h4 class="product-title">{{ proposal.item.title }}</h4>
            <p class="product-desc">{{ proposal.item.description }}</p>
            <div class="sub-item-meta-row">
              @if (getItemSalt(); as salt) {
                <span class="meta-tag">🧂 Sale: {{ salt }}g</span>
              }
              @if (getItemProtein(); as prot) {
                <span class="meta-tag">💪 Prot: {{ prot }}g</span>
              }
            </div>
            <div class="product-price-row">
              <span class="price-label">Prezzo Articolo:</span>
              <strong class="price-val">€ {{ formatCents(proposal.item.price_cents) }}</strong>
            </div>
          </div>
        </div>
      }

      <!-- FULFILLMENT OPTIONS SELECTOR -->
      <div class="fulfillment-section">
        <h5 class="section-heading">Scegli come ricevere il tuo ordine prima di procedere:</h5>
        <div class="options-list">
          @for (opt of proposal.fulfillment_options; track opt.id) {
            <div
              class="option-card"
              [class.selected]="opt.id === selectedOptionId"
              [class.disabled-row]="disabled"
              (click)="selectOption(opt.id)"
            >
              <div class="option-radio-col">
                <span class="radio-indicator">{{ opt.id === selectedOptionId ? '◉' : '○' }}</span>
              </div>
              <div class="option-content-col">
                <div class="option-title-row">
                  <strong class="option-label">{{ opt.label }}</strong>
                  @if (opt.badge) {
                    <span class="option-pill" [class.pill-rec]="opt.is_recommended">
                      {{ opt.badge }}
                    </span>
                  }
                </div>
                <div class="option-details">{{ opt.details }}</div>
                <div class="option-price-row">
                  <span class="fee-text">
                    {{ opt.delivery_fee_cents === 0 ? 'Consegna Gratuita (€0.00)' : 'Supplemento servizio: €' + formatCents(opt.delivery_fee_cents) }}
                  </span>
                  <strong class="total-text">Totale: € {{ formatCents(opt.total_cents) }}</strong>
                </div>
              </div>
            </div>
          }
        </div>
      </div>

      <!-- ACTION BUTTON -->
      @if (!disabled) {
        <div class="proposal-actions">
          <button
            type="button"
            class="btn-confirm-proposal"
            (click)="onConfirm()"
          >
            <span class="btn-lock-icon">🔒</span>
            <span>Conferma e Autorizza (Passkey AP2) • € {{ formatCents(getSelectedTotal()) }}</span>
          </button>
          <span class="action-note">
            🛡️ Verrà emesso un mandato crittografico AP2 tramite Local Credential Manager (LCM).
          </span>
        </div>
      }
    </div>
  `,
  styles: [`
    .proposal-card {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 14px;
      padding: 16px;
      margin: 10px 0;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
      display: flex;
      flex-direction: column;
      gap: 14px;
      max-width: 520px;
      width: 100%;
      transition: all 0.2s ease;
    }
    .proposal-card.confirmed {
      border-color: #86efac;
      background: #f8fafc;
      opacity: 0.95;
    }
    .proposal-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 1px solid #f1f5f9;
      padding-bottom: 10px;
    }
    .header-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .icon {
      font-size: 1.3rem;
    }
    .card-title {
      margin: 0;
      font-size: 0.98rem;
      font-weight: 700;
      color: #0f172a;
    }
    .card-sub {
      font-size: 0.72rem;
      color: #64748b;
    }
    .status-badge {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 9999px;
    }
    .badge-pending {
      background: #e0f2fe;
      color: #0369a1;
      border: 1px solid #bae6fd;
    }
    .badge-confirmed {
      background: #dcfce7;
      color: #15803d;
      border: 1px solid #86efac;
    }
    .product-item-box {
      display: flex;
      gap: 12px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 10px;
    }
    .product-thumb {
      width: 68px;
      height: 68px;
      border-radius: 8px;
      object-fit: cover;
      flex-shrink: 0;
    }
    .product-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .product-category-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .product-category {
      font-size: 0.68rem;
      text-transform: uppercase;
      font-weight: 700;
      color: #64748b;
      letter-spacing: 0.03em;
    }
    .temp-badge {
      font-size: 0.65rem;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 4px;
    }
    .temp-hot {
      background: #fee2e2;
      color: #b91c1c;
    }
    .temp-cold {
      background: #e0f2fe;
      color: #0284c7;
    }
    .micro-badge {
      font-size: 0.62rem;
      font-weight: 800;
      padding: 1px 5px;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .micro-badge.nutri {
      background: #10b981;
      color: #ffffff;
    }
    .micro-badge.nova {
      background: #f59e0b;
      color: #ffffff;
    }
    .micro-badge.coffee {
      background: #d97706;
      color: #ffffff;
    }
    .sub-item-meta-row {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-top: 3px;
    }
    .meta-tag {
      font-size: 0.65rem;
      background: #f1f5f9;
      color: #334155;
      padding: 1px 6px;
      border-radius: 4px;
      border: 1px solid #e2e8f0;
      font-weight: 600;
    }
    .product-title {
      margin: 0;
      font-size: 0.88rem;
      font-weight: 700;
      color: #0f172a;
      line-height: 1.25;
    }
    .product-desc {
      margin: 0;
      font-size: 0.72rem;
      color: #475569;
      line-height: 1.3;
    }
    .product-price-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 4px;
      padding-top: 4px;
      border-top: 1px dashed #cbd5e1;
    }
    .price-label {
      font-size: 0.72rem;
      color: #64748b;
    }
    .price-val {
      font-size: 0.88rem;
      color: #1e40af;
      font-weight: 800;
    }
    /* MULTI-ITEMS STYLES */
    .multi-items-container {
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 12px;
    }
    .multi-items-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 6px;
      border-bottom: 1px solid #e2e8f0;
    }
    .multi-items-title {
      font-size: 0.8rem;
      font-weight: 700;
      color: #1e293b;
    }
    .multi-items-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .sub-item-card {
      display: flex;
      gap: 10px;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 8px 10px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      transition: all 0.15s ease;
    }
    .sub-item-card:hover {
      border-color: #94a3b8;
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.06);
    }
    .sub-item-thumb {
      width: 54px;
      height: 54px;
      border-radius: 6px;
      object-fit: cover;
      flex-shrink: 0;
      border: 1px solid #e2e8f0;
    }
    .sub-item-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }
    .sub-item-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .sub-item-category {
      font-size: 0.63rem;
      text-transform: uppercase;
      font-weight: 700;
      color: #64748b;
    }
    .mini-temp-badge {
      font-size: 0.6rem;
      font-weight: 700;
      padding: 1px 5px;
      border-radius: 4px;
    }
    .sub-item-title {
      margin: 0;
      font-size: 0.82rem;
      font-weight: 700;
      color: #0f172a;
      line-height: 1.25;
    }
    .sub-item-desc {
      margin: 0;
      font-size: 0.68rem;
      color: #64748b;
      line-height: 1.25;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .sub-item-price-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 3px;
      padding-top: 3px;
      border-top: 1px dotted #e2e8f0;
    }
    .sub-item-price-label {
      font-size: 0.68rem;
      color: #64748b;
    }
    .sub-item-price {
      font-size: 0.82rem;
      font-weight: 800;
      color: #1e40af;
    }
    .multi-items-subtotal {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 8px;
      border-top: 1px dashed #cbd5e1;
      margin-top: 4px;
    }
    .subtotal-label {
      font-size: 0.74rem;
      font-weight: 600;
      color: #475569;
    }
    .subtotal-val {
      font-size: 0.95rem;
      font-weight: 800;
      color: #0f172a;
    }
    /* END MULTI-ITEMS STYLES */
    .fulfillment-section {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .section-heading {
      margin: 0;
      font-size: 0.76rem;
      font-weight: 700;
      color: #334155;
    }
    .options-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .option-card {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 9px 12px;
      cursor: pointer;
      background: #ffffff;
      transition: all 0.15s ease;
    }
    .option-card:hover:not(.disabled-row) {
      border-color: #2563eb;
      background: #f0f7ff;
    }
    .option-card.selected {
      border-color: #1d4ed8;
      background: #eff6ff;
      box-shadow: 0 0 0 1px #1d4ed8;
    }
    .option-card.disabled-row {
      cursor: default;
    }
    .option-radio-col {
      font-size: 1rem;
      color: #1d4ed8;
      padding-top: 1px;
    }
    .option-content-col {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .option-title-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .option-label {
      font-size: 0.82rem;
      color: #0f172a;
    }
    .option-pill {
      font-size: 0.65rem;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 9999px;
      background: #f1f5f9;
      color: #475569;
    }
    .option-pill.pill-rec {
      background: #dcfce7;
      color: #15803d;
      border: 1px solid #86efac;
    }
    .option-details {
      font-size: 0.72rem;
      color: #64748b;
    }
    .option-price-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 4px;
      font-size: 0.73rem;
    }
    .fee-text {
      color: #64748b;
    }
    .total-text {
      color: #1e40af;
      font-weight: 700;
    }
    .proposal-actions {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 4px;
    }
    .btn-confirm-proposal {
      width: 100%;
      background: #16a34a;
      color: #ffffff;
      border: none;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 0.86rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: background 0.15s ease, transform 0.1s ease;
      box-shadow: 0 2px 6px rgba(22, 163, 74, 0.25);
    }
    .btn-confirm-proposal:hover {
      background: #15803d;
      transform: translateY(-1px);
    }
    .btn-lock-icon {
      font-size: 0.95rem;
    }
    .action-note {
      font-size: 0.68rem;
      color: #64748b;
      text-align: center;
    }
  `]
})
export class TravelerProposalCardComponent implements OnInit {
  @Input({ required: true }) proposal!: ShopperProposal;
  @Input() disabled: boolean = false;
  @Output() confirm = new EventEmitter<{ optionId: string; proposal: ShopperProposal }>();

  selectedOptionId: string = 'in_seat_train';

  ngOnInit(): void {
    if (this.proposal?.selected_option_id) {
      this.selectedOptionId = this.proposal.selected_option_id;
    } else if (this.proposal?.fulfillment_options?.length > 0) {
      this.selectedOptionId = this.proposal.fulfillment_options[0].id;
    }
  }

  hasMultipleItems(): boolean {
    const items = this.getItems();
    return items.length > 1;
  }

  getItems(): any[] {
    if (this.proposal?.item && (this.proposal.item as any).items?.length > 0) {
      return (this.proposal.item as any).items;
    }
    if ((this.proposal as any)?.items?.length > 0) {
      return (this.proposal as any).items;
    }
    return [];
  }

  selectOption(optId: string): void {
    if (this.disabled) return;
    this.selectedOptionId = optId;
    this.proposal.selected_option_id = optId;
  }

  getSelectedOption(): ProposalFulfillmentOption | undefined {
    return this.proposal?.fulfillment_options?.find(o => o.id === this.selectedOptionId);
  }

  getSelectedTotal(): number {
    const opt = this.getSelectedOption();
    return opt ? opt.total_cents : (this.proposal?.item?.price_cents || 0);
  }

  getItemNutriScore(): string | undefined {
    return this.proposal?.item?.nutri_score || this.proposal?.item?.items?.[0]?.nutri_score;
  }

  getItemNovaGroup(): number | undefined {
    return this.proposal?.item?.nova_group || this.proposal?.item?.items?.[0]?.nova_group;
  }

  hasItemCoffeeProfile(): boolean {
    return !!(this.proposal?.item?.coffee_profile || this.proposal?.item?.items?.[0]?.coffee_profile);
  }

  getItemSalt(): number | undefined {
    return this.proposal?.item?.salt_g ?? this.proposal?.item?.items?.[0]?.salt_g;
  }

  getItemProtein(): number | undefined {
    return this.proposal?.item?.protein_g ?? this.proposal?.item?.items?.[0]?.protein_g;
  }

  formatCents(cents?: number): string {
    return ((cents || 0) / 100).toFixed(2);
  }

  onConfirm(): void {
    if (this.disabled) return;
    this.confirm.emit({
      optionId: this.selectedOptionId,
      proposal: this.proposal,
    });
  }
}
