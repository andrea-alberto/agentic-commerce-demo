// Copyright 2026 UCP Authors / GDG DevFest Milano 2026
import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { McpService, StoreProduct } from './services/mcp.service';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  readonly mcpService = inject(McpService);
  readonly authService = inject(AuthService);

  // --- USER PROFILE & LOGIN STATE ---
  readonly currentUser = this.mcpService.currentUser;

  // --- UI DIALOGS & DRAWERS (SYNCHRONIZED WITH WEBMCP AGENT TOOLS) ---
  readonly isCartOpen = this.mcpService.isCartOpen;
  readonly orderSuccessBanner = this.mcpService.orderSuccessBanner;

  // --- FULFILLMENT STATE (SYNCHRONIZED WITH WEBMCP AGENT TOOLS) ---
  readonly selectedFulfillment = this.mcpService.selectedFulfillment;
  readonly lockerSlotTime = this.mcpService.lockerSlotTime;
  readonly lockerPin = this.mcpService.lockerPin;
  readonly trainNumber = this.mcpService.trainNumber;
  readonly trainPlatform = this.mcpService.trainPlatform;
  readonly trainCarriage = this.mcpService.trainCarriage;
  readonly trainSeat = this.mcpService.trainSeat;
  readonly trainDeliveryTime = this.mcpService.trainDeliveryTime;
  readonly tableNumber = this.mcpService.tableNumber;

  // --- HUMAN-PRESENT PAYMENT SELECTION ---
  readonly selectedPaymentMethod = this.mcpService.selectedPaymentMethod;
  readonly isProcessingPayment = this.mcpService.isProcessingPayment;

  // --- HUMAN ACTIONS ---

  openCart(): void {
    this.isCartOpen.set(true);
  }

  closeCart(): void {
    this.isCartOpen.set(false);
  }

  async loginWithGoogle(): Promise<void> {
    try {
      await this.authService.loginWithGoogle();
    } catch (err) {
      console.warn('Google sign-in error:', err);
    }
  }

  // --- VIEWS & USER ORDERS NAVIGATION ---
  readonly activeView = this.mcpService.activeView;
  readonly userOrders = this.mcpService.userOrders;
  readonly isOrdersLoading = this.mcpService.isOrdersLoading;

  async logout(): Promise<void> {
    await this.authService.logout();
    this.mcpService.activeView.set('catalog');
  }

  setActiveView(view: 'catalog' | 'orders' | 'about'): void {
    this.mcpService.activeView.set(view);
    if (view === 'orders') {
      this.mcpService.fetchUserOrders();
    }
  }

  readonly demo2Prompt = "Trova una spremuta d'arancia fresca e un panino vegano con verdure a Km 0, compatibile con lo Smart Locker, e prepara il carrello.";
  readonly isDemoPromptCopied = signal(false);

  readonly demo2Steps = [
    {
      step: 1,
      badge: 'Step 1 · Filtra Catalogo',
      prompt: "Mostrami i panini vegani nel catalogo",
      action: 'searchCatalog("panini vegani")'
    },
    {
      step: 2,
      badge: 'Step 2 · Aggiungi Carrello',
      prompt: "Aggiungi al carrello il panino vegano",
      action: 'addToCart("VEG-012")'
    },
    {
      step: 3,
      badge: 'Step 3 · Smart Locker',
      prompt: "Imposta il ritiro allo Smart Locker",
      action: 'configureFulfillment("pickup_locker")'
    },
    {
      step: 4,
      badge: 'Step 4 · Apri Checkout',
      prompt: "Procedi al checkout",
      action: 'prepareCheckout()'
    }
  ];
  readonly copiedStepIndex = signal<number | null>(null);

  copyStepPrompt(index: number): void {
    const p = this.demo2Steps[index].prompt;
    navigator.clipboard.writeText(p);
    this.copiedStepIndex.set(index);
    setTimeout(() => {
      this.copiedStepIndex.set(null);
    }, 2500);
  }

  copyDemoPrompt(): void {
    navigator.clipboard.writeText(this.demo2Prompt);
    this.isDemoPromptCopied.set(true);
    setTimeout(() => {
      this.isDemoPromptCopied.set(false);
    }, 2500);
  }

  readonly isContextCopied = signal(false);

  async copyPageContext(): Promise<void> {
    const ok = await this.mcpService.copyPageContextToClipboard();
    if (ok) {
      this.isContextCopied.set(true);
      setTimeout(() => {
        this.isContextCopied.set(false);
      }, 2500);
    }
  }

  refreshOrders(): void {
    this.mcpService.fetchUserOrders();
  }

  viewOrderInHistory(order: any): void {
    this.dismissSuccessBanner();
    this.setActiveView('orders');
  }

  loginDemoUser(): void {
    this.authService.loginDemoUser();
  }

  toggleLogin(): void {
    this.mcpService.toggleLogin();
  }

  selectCategory(cat: string): void {
    this.mcpService.searchQuery.set('');
    this.mcpService.selectedCategory.set(cat);
  }

  resetSearch(): void {
    this.mcpService.searchQuery.set('');
    this.mcpService.selectedCategory.set('all');
  }

  onSearchInput(event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.mcpService.searchQuery.set(val);
  }

  selectPaymentMethod(method: 'gpay' | 'card' | 'ap2'): void {
    this.mcpService.selectedPaymentMethod.set(method);
  }

  // --- PRODUCT SPECS ACCORDION STATE ---
  readonly expandedProducts = signal<Record<string, boolean>>({});

  toggleProductSpecs(productId: string): void {
    const cur = { ...this.expandedProducts() };
    cur[productId] = !cur[productId];
    this.expandedProducts.set(cur);
  }

  isSpecsExpanded(productId: string): boolean {
    return !!this.expandedProducts()[productId];
  }

  getNutriScoreColor(score?: string): string {
    switch (score?.toUpperCase()) {
      case 'A': return '#1b8a3e';
      case 'B': return '#85bb2f';
      case 'C': return '#fecb02';
      case 'D': return '#ee8100';
      case 'E': return '#e63e11';
      default: return '#6b7280';
    }
  }

  getNovaColor(group?: number): string {
    switch (group) {
      case 1: return '#10b981';
      case 2: return '#3b82f6';
      case 3: return '#f59e0b';
      case 4: return '#ef4444';
      default: return '#6b7280';
    }
  }

  async addProductToCart(prod: StoreProduct): Promise<void> {
    await this.mcpService.addItemToCart(prod, 1);
  }

  getProductCartQty(productId: string): number {
    const cart = this.mcpService.currentCart();
    if (!cart) return 0;
    const item = cart.items.find(i => i.product_id === productId);
    return item ? item.quantity : 0;
  }

  async onFulfillmentMethodChange(method: 'pickup_locker' | 'pickup_express' | 'in_seat_train' | 'table_service'): Promise<void> {
    this.selectedFulfillment.set(method);
    await this.applySelectedFulfillment();
  }

  async applySelectedFulfillment(): Promise<boolean> {
    const method = this.selectedFulfillment();
    let details: any = {};

    if (method === 'pickup_locker') {
      details = {
        slot_time: this.lockerSlotTime(),
        pin_code: this.lockerPin(),
        box_number: 'Box #14'
      };
    } else if (method === 'pickup_express') {
      details = {
        table_number: 'Al Banco Express'
      };
    } else if (method === 'in_seat_train') {
      details = {
        train_number: this.trainNumber(),
        platform: this.trainPlatform(),
        carriage: this.trainCarriage(),
        seat: this.trainSeat(),
        delivery_time: this.trainDeliveryTime()
      };
    } else if (method === 'table_service') {
      details = {
        table_number: this.tableNumber()
      };
    }

    return await this.mcpService.applyFulfillment(method, details);
  }

  async authorizePayment(): Promise<void> {
    if (!this.mcpService.currentCart() || this.mcpService.currentCart()!.items.length === 0) return;
    if (!this.currentUser()) return;

    // 1. Ensure fulfillment configuration is valid
    const ok = await this.applySelectedFulfillment();
    if (!ok) return;

    // 2. Perform Human-Present Payment authorization
    try {
      await this.mcpService.authorizeAndPay();
    } catch (e) {
      console.error('Payment authorization error:', e);
    }
  }

  dismissSuccessBanner(): void {
    this.mcpService.orderSuccessBanner.set(null);
  }

  formatDeliveryTime(order: any): string {
    const raw = order.requested_delivery_display || order.requested_delivery || '';
    const details = order.fulfillment_details || order.fulfillment || {};

    let dateStr = '';
    const dateMatch = raw.match(/\b\d{2}\/\d{2}\/\d{4}\b/);
    if (dateMatch) {
      dateStr = dateMatch[0];
    } else if (order.created_at) {
      try {
        dateStr = new Date(order.created_at).toLocaleDateString('it-IT');
      } catch {
        dateStr = new Date().toLocaleDateString('it-IT');
      }
    } else {
      dateStr = new Date().toLocaleDateString('it-IT');
    }

    let timeStr = '';
    const timeMatch = raw.match(/\b\d{1,2}:\d{2}(?:\s*[\-–]\s*\d{1,2}:\d{2})?\b/);
    if (timeMatch) {
      timeStr = timeMatch[0];
    } else if (details.service_time && /\b\d{1,2}:\d{2}\b/.test(details.service_time)) {
      timeStr = details.service_time;
    } else if (details.delivery_time && /\b\d{1,2}:\d{2}\b/.test(details.delivery_time)) {
      timeStr = details.delivery_time;
    } else if (details.slot_start && /\b\d{1,2}:\d{2}\b/.test(details.slot_start)) {
      timeStr = details.slot_end ? `${details.slot_start} – ${details.slot_end}` : details.slot_start;
    } else {
      try {
        const base = order.created_at ? new Date(order.created_at) : new Date();
        const lead = order.lead_time_minutes ?? 5;
        const target = new Date(base.getTime() + lead * 60 * 1000);
        timeStr = target.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
      } catch {
        timeStr = 'In orario';
      }
    }

    return `${dateStr} ${timeStr}`.trim();
  }
}
