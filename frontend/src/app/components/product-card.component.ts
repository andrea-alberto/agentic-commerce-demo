import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Product } from '../models';
import { ChatService } from '../services/chat.service';

@Component({
  selector: 'app-product-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="product-card">
      <div class="product-image-container">
        <img [src]="getImageUrl()" [alt]="product.name" class="product-image" />
        <span class="badge" [ngClass]="getTemperatureClass()">
          {{ getTemperatureLabel() }}
        </span>
      </div>
      <div class="product-details">
        <span class="product-category">{{ product.category || 'Travel Retail' }}</span>
        <h4 class="product-title">{{ product.name }}</h4>
        <p class="product-description">{{ product.description }}</p>
        <div class="product-footer">
          <span class="product-price">€ {{ getFormattedPrice() }}</span>
          <button (click)="onAdd()" class="btn-add" [disabled]="chatService.isLoading()">
            + Aggiungi
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .product-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      box-shadow: 0 2px 6px rgba(0,0,0,0.04);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
      max-width: 270px;
      min-width: 240px;
    }
    .product-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 14px rgba(0,0,0,0.08);
    }
    .product-image-container {
      position: relative;
      height: 140px;
      background: #f8fafc;
      overflow: hidden;
    }
    .product-image {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .badge {
      position: absolute;
      top: 8px;
      right: 8px;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 9999px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    }
    .badge-hot {
      background: #fee2e2;
      color: #b91c1c;
      border: 1px solid #fecaca;
    }
    .badge-cold {
      background: #e0f2fe;
      color: #0369a1;
      border: 1px solid #bae6fd;
    }
    .badge-ambient {
      background: #f1f5f9;
      color: #334155;
      border: 1px solid #e2e8f0;
    }
    .product-details {
      padding: 12px;
      display: flex;
      flex-direction: column;
      flex: 1;
    }
    .product-category {
      font-size: 0.7rem;
      color: #64748b;
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.03em;
    }
    .product-title {
      font-size: 0.92rem;
      font-weight: 600;
      color: #0f172a;
      margin: 4px 0;
      line-height: 1.25;
    }
    .product-description {
      font-size: 0.78rem;
      color: #475569;
      line-height: 1.35;
      margin-bottom: 10px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .product-footer {
      margin-top: auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 6px;
      border-top: 1px solid #f5f5f4;
    }
    .product-price {
      font-size: 1.05rem;
      font-weight: 800;
      color: #92400e;
    }
    .btn-add {
      background: linear-gradient(135deg, #d97706, #b45309);
      color: #ffffff;
      border: none;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 1px 4px rgba(180, 83, 9, 0.25);
      transition: all 0.15s ease;
    }
    .btn-add:hover:not(:disabled) {
      background: linear-gradient(135deg, #b45309, #92400e);
    }
    .btn-add:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  `]
})
export class ProductCardComponent {
  @Input({ required: true }) product!: Product;
  chatService = inject(ChatService);

  getImageUrl(): string {
    if (Array.isArray(this.product.image) && this.product.image.length > 0) {
      return this.product.image[0];
    }
    if (typeof this.product.image === 'string') {
      return this.product.image;
    }
    return 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=400&q=80';
  }

  getFormattedPrice(): string {
    if (this.product.offers?.price) {
      return Number(this.product.offers.price).toFixed(2);
    }
    return '0.00';
  }

  getTemperatureClass(): string {
    const temp = this.getTemperature();
    if (temp === 'hot') return 'badge-hot';
    if (temp === 'cold') return 'badge-cold';
    return 'badge-ambient';
  }

  getTemperatureLabel(): string {
    const temp = this.getTemperature();
    if (temp === 'hot') return '🔥 Caldo';
    if (temp === 'cold') return '❄️ Freddo (Locker OK)';
    return '⚡ Tech / Ambient';
  }

  private getTemperature(): string {
    if (this.product.additionalProperty) {
      const props = Array.isArray(this.product.additionalProperty)
        ? this.product.additionalProperty
        : [this.product.additionalProperty];
      for (const p of props) {
        if (p.name === 'temperature') return p.value;
      }
    }
    const name = this.product.name.toLowerCase();
    if (name.includes('caldo') || name.includes('espresso') || name.includes('toast')) return 'hot';
    return 'cold';
  }

  onAdd(): void {
    this.chatService.addToCheckout(this.product, 1);
  }
}
